"""Ingestion pipeline orchestrator. Runs a resource through staged processing.

Supports two modes:
1. Sequential (default): single provider handles analysis + discovery
2. Coordinated: optional bounded multi-worker mode for richer extraction
   (see coordinator.py and INGESTION_ARCHITECTURE.md)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from foundry.agents.provider_factory import get_llm_provider
from foundry.config import FoundrySettings
from foundry.ingestion.analysis import AnalysisResult, run_analysis
from foundry.ingestion.coordinator import (
    CoordinatedResult,
    CoordinatorConfig,
    run_coordinated_analysis,
)
from foundry.ingestion.extraction import SubprojectProposal, run_discovery
from foundry.ingestion.handlers.base import ExtractedContent, ExtractionError
from foundry.ingestion.handlers.pdf import PDFHandler
from foundry.ingestion.handlers.webpage import WebpageHandler
from foundry.ingestion.handlers.youtube import YouTubeHandler
from foundry.storage.database import Database
from foundry.storage.queries import get_resource, update_resource_status

logger = logging.getLogger(__name__)

# Handler registry — order matters: more specific handlers first
HANDLERS = [YouTubeHandler(), PDFHandler(), WebpageHandler()]


async def dispatch(input_str: str) -> tuple[str, object]:
    """Determine which handler should process this input."""
    for handler in HANDLERS:
        if await handler.can_handle(input_str):
            return handler.name, handler
    raise ExtractionError(f"No handler found for: {input_str}", recoverable=False)


def _coordinated_to_analysis(result: CoordinatedResult) -> AnalysisResult:
    """Convert coordinated analysis output to AnalysisResult for downstream compatibility."""
    # Try to parse the synthesis as our standard JSON format
    try:
        parsed = json.loads(result.synthesis)
    except (json.JSONDecodeError, TypeError):
        parsed = {}

    return AnalysisResult(
        summary=parsed.get("summary", result.synthesis[:2000] if result.synthesis else ""),
        key_concepts=parsed.get("key_concepts", []),
        entities=parsed.get("entities", {}),
        content_sections=parsed.get("content_sections", []),
        open_questions=parsed.get("open_questions", []),
        follow_up_suggestions=parsed.get("follow_up_suggestions", result.follow_up_results),
        model_used="coordinated",
        is_synthetic=False,
        raw_response=result.synthesis,
    )


async def run_pipeline(
    resource_id: str,
    db: Database,
    settings: FoundrySettings,
) -> None:
    """Run the full ingestion pipeline for a resource. Updates DB status at each stage."""
    resource = await get_resource(db, resource_id)
    if resource is None:
        logger.error("Resource %s not found", resource_id)
        return

    url = resource.get("url", "")
    cache_dir = Path(settings.ingestion.cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    # ── Stage 1-2: Dispatch + Extract ────────────────────────────────────
    await update_resource_status(db, resource_id, "extracting")
    try:
        handler_name, handler = await dispatch(url)
        extracted: ExtractedContent = await handler.extract(url, cache_dir)
    except ExtractionError as e:
        logger.error("Extraction failed for %s: %s", url, e)
        await update_resource_status(db, resource_id, "extract_failed", error=str(e))
        return
    except Exception as e:
        logger.exception("Unexpected error during extraction for %s", url)
        await update_resource_status(db, resource_id, "extract_failed", error=str(e))
        return

    # Update resource with extracted metadata
    await update_resource_status(
        db, resource_id, "extracted",
        content_hash=extracted.content_hash,
        raw_content_path=str(extracted.raw_content_path) if extracted.raw_content_path else None,
        title=extracted.metadata.get("title"),
    )

    # ── Stage 3: Analyze ─────────────────────────────────────────────────
    await update_resource_status(db, resource_id, "analyzing")

    provider = await get_llm_provider(settings)
    analysis: AnalysisResult | None = None

    # Try coordinated mode if configured and provider is healthy
    coord_config = await _build_coordinator_config(settings, db)
    if coord_config.enabled:
        try:
            coord_result = await run_coordinated_analysis(extracted, coord_config)
            if coord_result.mode == "coordinated" and coord_result.synthesis:
                analysis = _coordinated_to_analysis(coord_result)
                logger.info("Used coordinated analysis mode")
        except Exception as e:
            logger.warning("Coordinated analysis failed, falling back to sequential: %s", e)

    # Fallback: sequential single-model analysis
    if analysis is None:
        try:
            analysis = await run_analysis(extracted, provider)
        except Exception as e:
            logger.exception("Analysis failed for %s", url)
            await update_resource_status(db, resource_id, "analyze_failed", error=str(e))
            return

    await update_resource_status(db, resource_id, "analyzed")

    # Store extraction result
    from foundry.storage.queries import insert_extraction_result
    await insert_extraction_result(db, resource_id, analysis)

    # ── Stage 4: Discover ────────────────────────────────────────────────
    await update_resource_status(db, resource_id, "discovering")
    try:
        proposals: list[SubprojectProposal] = await run_discovery(analysis, provider)
    except Exception as e:
        logger.exception("Discovery failed for %s", url)
        await update_resource_status(db, resource_id, "discover_failed", error=str(e))
        return

    # Store proposals in extraction result
    from foundry.storage.queries import update_extraction_proposals
    await update_extraction_proposals(db, resource_id, proposals)

    # Store pipeline metadata alongside the status
    analysis_mode = "coordinated" if (coord_config.enabled and analysis and analysis.model_used == "coordinated") else "sequential"
    await update_resource_status(db, resource_id, "discovered")

    # Update extraction result with pipeline metadata
    from foundry.storage.queries import update_extraction_metadata
    await update_extraction_metadata(db, resource_id, {
        "handler": handler_name,
        "provider": provider.name,
        "model": getattr(provider, "model", ""),
        "analysis_mode": analysis_mode,
    })

    logger.info(
        "Pipeline complete for resource %s (%s) handler=%s provider=%s mode=%s",
        resource_id, url, handler_name, provider.name, analysis_mode,
    )


async def _build_coordinator_config(
    settings: FoundrySettings,
    db: Database,
) -> CoordinatorConfig:
    """Build coordinator config from persistent runtime settings."""
    from foundry.api.config_control import get_all_settings
    from foundry.agents.provider_factory import get_provider_for_role

    runtime = await get_all_settings(db)
    swarm_mode = runtime.get("ingestion.swarm.mode", "single")

    if swarm_mode != "swarm":
        return CoordinatorConfig(enabled=False)

    # Build swarm settings dict for provider_factory
    swarm_settings = {
        "coordinator_provider": runtime.get("ingestion.swarm.coordinator_provider", ""),
        "coordinator_model": runtime.get("ingestion.swarm.coordinator_model", ""),
        "worker_provider": runtime.get("ingestion.swarm.worker_provider", ""),
        "worker_model": runtime.get("ingestion.swarm.worker_model", ""),
    }

    coordinator_provider = await get_provider_for_role(settings, "coordinator", swarm_settings)
    worker_provider = await get_provider_for_role(settings, "worker", swarm_settings)

    return CoordinatorConfig(
        enabled=True,
        max_parallel_workers=int(runtime.get("ingestion.swarm.max_workers", 4)),
        coordinator_provider=coordinator_provider,
        worker_provider=worker_provider,
        use_critic=bool(runtime.get("ingestion.swarm.use_critic", False)),
    )
