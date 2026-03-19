"""Stage 3: LLM-powered analysis of extracted content."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from foundry.agents.providers.base import LLMProvider
from foundry.ingestion.handlers.base import ExtractedContent

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT = """\
You are analyzing content for Foundry, a research-to-projects workspace.
Extract structured, actionable information from the following content.

Instructions:
1. Provide a 2-3 paragraph summary of the overall content.
2. List the key concepts and topics covered.
3. Extract all mentioned entities: repositories, models, datasets, tools, papers, people.
   For each, include name, URL if available, and context where it appears.
4. Identify logical sections of the content and summarize each.
5. List open questions — things unclear, missing, or needing further research.
6. Suggest follow-up resources that would complement this content.

Respond as JSON with this structure:
{
  "summary": "...",
  "key_concepts": ["..."],
  "entities": {"repos": [], "models": [], "datasets": [], "tools": [], "papers": [], "people": []},
  "content_sections": [{"title": "...", "summary": "..."}],
  "open_questions": ["..."],
  "follow_up_suggestions": ["..."]
}

Content:"""


@dataclass
class AnalysisResult:
    summary: str = ""
    key_concepts: list[str] = field(default_factory=list)
    entities: dict[str, list[Any]] = field(default_factory=dict)
    content_sections: list[dict[str, str]] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    follow_up_suggestions: list[str] = field(default_factory=list)
    model_used: str = ""
    is_synthetic: bool = False
    raw_response: str = ""


async def run_analysis(
    extracted: ExtractedContent,
    provider: LLMProvider,
) -> AnalysisResult:
    """Run LLM analysis on extracted content. Returns structured AnalysisResult."""
    # Truncate very long content to avoid token limits
    text = extracted.text
    if len(text) > 30000:
        text = text[:30000] + "\n\n[Content truncated at 30,000 characters]"

    logger.info("Running analysis with provider=%s on %d chars", provider.name, len(text))
    raw_response = await provider.analyze(text, ANALYSIS_PROMPT)

    # Parse the response
    result = AnalysisResult(
        model_used=provider.name,
        is_synthetic=provider.name == "fallback",
        raw_response=raw_response,
    )

    try:
        parsed = json.loads(raw_response)
    except (json.JSONDecodeError, TypeError):
        # LLM didn't return valid JSON — extract what we can
        logger.warning("Analysis response was not valid JSON, using raw text as summary")
        result.summary = raw_response[:2000] if raw_response else "Analysis produced no output."
        return result

    result.summary = parsed.get("summary", "")
    result.key_concepts = parsed.get("key_concepts", [])
    result.entities = parsed.get("entities", {})
    result.content_sections = parsed.get("content_sections", [])
    result.open_questions = parsed.get("open_questions", [])
    result.follow_up_suggestions = parsed.get("follow_up_suggestions", [])

    if parsed.get("_synthetic"):
        result.is_synthetic = True

    return result
