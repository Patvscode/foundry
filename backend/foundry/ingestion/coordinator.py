"""Ingestion coordinator — optional bounded orchestration for intake/discovery.

This implements the Perception Engine pattern for Foundry's ingestion pipeline ONLY.
It provides a coordinator that can decompose intake work across specialist workers
when multiple LLM providers are available.

Design rules (from INGESTION_ARCHITECTURE.md):
- Provider-agnostic, role-based, configurable
- Graceful fallback to single-model sequential mode
- Bounded to ingestion/discovery — NOT used by workspace/UI/CRUD
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from foundry.agents.providers.base import LLMProvider
from foundry.ingestion.handlers.base import ExtractedContent

logger = logging.getLogger(__name__)


class WorkerRole(str, Enum):
    """Roles a worker can fill during coordinated ingestion."""
    SECTION_ANALYST = "section_analyst"
    ENTITY_EXTRACTOR = "entity_extractor"
    FOLLOW_UP_FINDER = "follow_up_finder"
    SYNTHESIS = "synthesis"
    CRITIC = "critic"


@dataclass
class WorkerTask:
    """A single unit of work dispatched by the coordinator."""
    role: WorkerRole
    input_text: str
    prompt: str
    result: str = ""
    error: str = ""
    done: bool = False


@dataclass
class CoordinatorConfig:
    """Configuration for coordinated ingestion mode."""
    enabled: bool = False
    max_parallel_workers: int = 4
    section_chunk_chars: int = 8000
    use_critic: bool = False
    coordinator_provider: LLMProvider | None = None
    worker_provider: LLMProvider | None = None


@dataclass
class CoordinatedResult:
    """Combined output from coordinated analysis."""
    section_analyses: list[dict[str, Any]] = field(default_factory=list)
    entity_results: list[dict[str, Any]] = field(default_factory=list)
    follow_up_results: list[str] = field(default_factory=list)
    synthesis: str = ""
    critic_notes: str = ""
    mode: str = "coordinated"  # or "sequential"


# ── Prompts ─────────────────────────────────────────────────────────

SECTION_ANALYSIS_PROMPT = """\
Analyze this section of a research document. Extract:
1. Key concepts and topics
2. Any mentioned tools, repos, models, datasets, papers, people
3. Buildable components or projects described
4. Open questions or unclear points

Respond as JSON:
{"concepts": [...], "entities": {...}, "components": [...], "questions": [...]}

Section:"""

ENTITY_EXTRACTION_PROMPT = """\
Extract all named entities from this text. Include:
- Repositories (with URLs if present)
- ML models
- Datasets
- Tools and frameworks
- Papers and publications
- People and organizations

Respond as JSON:
{"repos": [...], "models": [...], "datasets": [...], "tools": [...], "papers": [...], "people": [...]}

Text:"""

FOLLOW_UP_PROMPT = """\
Based on this content, suggest follow-up resources that would complement it.
Include specific search terms, paper titles, or repo names when possible.

Respond as JSON:
{"suggestions": [{"title": "...", "type": "...", "search_terms": [...]}]}

Content:"""

SYNTHESIS_PROMPT = """\
You are synthesizing results from multiple parallel analyses of a document.
Combine these partial analyses into a single coherent summary.

Merge entities (deduplicate), combine concepts, and produce:
1. A unified 2-3 paragraph summary
2. Merged entity list
3. Combined list of buildable components
4. Open questions
5. Follow-up suggestions

Respond as JSON with the standard analysis structure:
{
  "summary": "...",
  "key_concepts": [...],
  "entities": {"repos": [], "models": [], "datasets": [], "tools": [], "papers": [], "people": []},
  "content_sections": [{"title": "...", "summary": "..."}],
  "open_questions": [...],
  "follow_up_suggestions": [...]
}

Partial analyses:"""

CRITIC_PROMPT = """\
Review this combined analysis for quality. Check for:
1. Missed entities or concepts
2. Incorrect classifications
3. Low-confidence or vague proposals
4. Missing follow-up suggestions

Respond as JSON:
{"issues": [...], "suggestions": [...], "quality_score": 0.0-1.0}

Analysis:"""


def _chunk_text(text: str, chunk_size: int) -> list[str]:
    """Split text into chunks at paragraph boundaries."""
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    paragraphs = text.split("\n\n")
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 > chunk_size and current:
            chunks.append(current.strip())
            current = para
        else:
            current = current + "\n\n" + para if current else para

    if current.strip():
        chunks.append(current.strip())

    return chunks if chunks else [text]


async def _run_worker(
    provider: LLMProvider,
    task: WorkerTask,
    semaphore: asyncio.Semaphore,
) -> WorkerTask:
    """Execute a single worker task with concurrency control."""
    async with semaphore:
        try:
            task.result = await provider.analyze(task.input_text, task.prompt)
            task.done = True
        except Exception as e:
            logger.warning("Worker %s failed: %s", task.role, e)
            task.error = str(e)
            task.done = True
    return task


async def run_coordinated_analysis(
    extracted: ExtractedContent,
    config: CoordinatorConfig,
) -> CoordinatedResult:
    """Run coordinated multi-worker analysis on extracted content.

    Falls back to empty result if providers are missing — caller should
    check and use sequential mode instead.
    """
    if not config.coordinator_provider or not config.worker_provider:
        logger.warning("Coordinator or worker provider not set, returning empty result")
        return CoordinatedResult(mode="sequential")

    text = extracted.text
    if len(text) > 60000:
        text = text[:60000] + "\n\n[Content truncated at 60,000 characters]"

    semaphore = asyncio.Semaphore(config.max_parallel_workers)
    tasks: list[WorkerTask] = []

    # ── Phase 1: Parallel section analysis + entity extraction ───────
    chunks = _chunk_text(text, config.section_chunk_chars)
    for i, chunk in enumerate(chunks):
        tasks.append(WorkerTask(
            role=WorkerRole.SECTION_ANALYST,
            input_text=chunk,
            prompt=SECTION_ANALYSIS_PROMPT,
        ))

    tasks.append(WorkerTask(
        role=WorkerRole.ENTITY_EXTRACTOR,
        input_text=text[:30000],  # Entity extraction on first 30K
        prompt=ENTITY_EXTRACTION_PROMPT,
    ))

    tasks.append(WorkerTask(
        role=WorkerRole.FOLLOW_UP_FINDER,
        input_text=text[:15000],
        prompt=FOLLOW_UP_PROMPT,
    ))

    logger.info(
        "Coordinated analysis: %d section chunks + entity + follow-up = %d workers",
        len(chunks), len(tasks),
    )

    # Run all phase 1 tasks in parallel
    completed = await asyncio.gather(
        *[_run_worker(config.worker_provider, t, semaphore) for t in tasks],
        return_exceptions=True,
    )

    result = CoordinatedResult()

    # Collect results
    for item in completed:
        if isinstance(item, Exception):
            logger.warning("Worker raised: %s", item)
            continue
        task = item
        if task.error:
            continue
        try:
            parsed = json.loads(task.result)
        except (json.JSONDecodeError, TypeError):
            parsed = {"raw": task.result[:1000]}

        if task.role == WorkerRole.SECTION_ANALYST:
            result.section_analyses.append(parsed)
        elif task.role == WorkerRole.ENTITY_EXTRACTOR:
            result.entity_results.append(parsed)
        elif task.role == WorkerRole.FOLLOW_UP_FINDER:
            suggestions = parsed.get("suggestions", [])
            result.follow_up_results.extend(
                s.get("title", str(s)) if isinstance(s, dict) else str(s)
                for s in suggestions
            )

    # ── Phase 2: Synthesis (coordinator model) ───────────────────────
    partial_json = json.dumps({
        "sections": result.section_analyses,
        "entities": result.entity_results,
        "follow_ups": result.follow_up_results,
    }, indent=2)

    if len(partial_json) > 40000:
        partial_json = partial_json[:40000] + "\n..."

    try:
        synthesis_raw = await config.coordinator_provider.analyze(
            partial_json, SYNTHESIS_PROMPT
        )
        result.synthesis = synthesis_raw
    except Exception as e:
        logger.warning("Synthesis failed: %s", e)
        result.synthesis = json.dumps({
            "summary": "Synthesis failed — partial results available.",
            "key_concepts": [],
            "entities": {},
            "content_sections": [],
            "open_questions": ["Synthesis step failed."],
            "follow_up_suggestions": result.follow_up_results,
        })

    # ── Phase 3 (optional): Critic pass ──────────────────────────────
    if config.use_critic:
        try:
            critic_raw = await config.coordinator_provider.analyze(
                result.synthesis, CRITIC_PROMPT
            )
            result.critic_notes = critic_raw
        except Exception as e:
            logger.warning("Critic pass failed: %s", e)

    result.mode = "coordinated"
    return result
