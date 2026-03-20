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
    coord_config = _build_coordinator_config(settings, provider)
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

    await update_resource_status(db, resource_id, "discovered")
    logger.info(
        "Pipeline complete for resource %s (%s) via handler=%s",
        resource_id, url, handler_name,
    )


def _build_coordinator_config(
    settings: FoundrySettings,
    default_provider: LLMProvider,
) -> CoordinatorConfig:
    """Build coordinator config from settings. Coordinated mode requires explicit opt-in."""
    # Coordinated mode is opt-in via environment or future config field
    # For now, it's disabled by default — single-model always works
    import os
    if not os.environ.get("FOUNDRY_INGESTION_COORDINATED"):
        return CoordinatorConfig(enabled=False)

    return CoordinatorConfig(
        enabled=True,
        max_parallel_workers=settings.ingestion.max_concurrent,
        coordinator_provider=default_provider,
        worker_provider=default_provider,
        use_critic=bool(os.environ.get("FOUNDRY_INGESTION_CRITIC")),
    )
