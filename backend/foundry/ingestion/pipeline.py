"""Ingestion pipeline orchestrator. Runs a resource through staged processing."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from foundry.agents.provider_factory import get_llm_provider
from foundry.config import FoundrySettings
from foundry.ingestion.analysis import AnalysisResult, run_analysis
from foundry.ingestion.extraction import SubprojectProposal, run_discovery
from foundry.ingestion.handlers.base import ExtractedContent, ExtractionError
from foundry.ingestion.handlers.webpage import WebpageHandler
from foundry.storage.database import Database
from foundry.storage.queries import get_resource, update_resource_status

logger = logging.getLogger(__name__)

# Handler registry — extend this list as new handlers are added
HANDLERS = [WebpageHandler()]


async def dispatch(input_str: str) -> tuple[str, object]:
    """Determine which handler should process this input."""
    for handler in HANDLERS:
        if await handler.can_handle(input_str):
            return handler.name, handler
    raise ExtractionError(f"No handler found for: {input_str}", recoverable=False)


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
    try:
        provider = await get_llm_provider(settings)
        analysis: AnalysisResult = await run_analysis(extracted, provider)
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
    logger.info("Pipeline complete for resource %s (%s)", resource_id, url)
