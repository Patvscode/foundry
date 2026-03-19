"""Stage 4: LLM-powered project/subproject discovery from analysis results."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from foundry.agents.providers.base import LLMProvider
from foundry.ingestion.analysis import AnalysisResult

logger = logging.getLogger(__name__)

DISCOVERY_PROMPT = """\
Based on this analysis, identify the distinct buildable projects, components,
or systems described. Each should be a separate thing someone could build or work on.

For each discovered project, provide:
- name: descriptive name
- description: what it is and what it does
- type: one of "library", "tool", "model", "dataset", "service", "research"
- repos: any repository URLs mentioned
- dependencies: known dependencies
- setup_steps: ordered setup instructions
- complexity: "low", "medium", or "high"
- confidence: 0.0 to 1.0 (how confident you are this is a real, distinct project)
- source_context: where in the content this was described

Do NOT create subprojects for generic infrastructure or things mentioned in passing.

Respond as JSON: {"proposals": [{ ... }]}

Analysis:"""


@dataclass
class SubprojectProposal:
    suggested_name: str = ""
    description: str = ""
    type: str = "research"
    repos: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    setup_steps: list[str] = field(default_factory=list)
    complexity: str = "medium"
    confidence: float = 0.5
    source_context: str = ""
    is_synthetic: bool = False


async def run_discovery(
    analysis: AnalysisResult,
    provider: LLMProvider,
) -> list[SubprojectProposal]:
    """Run LLM discovery to extract subproject proposals from analysis results."""
    # Build a compact analysis summary for the prompt
    analysis_json = json.dumps({
        "summary": analysis.summary,
        "key_concepts": analysis.key_concepts,
        "entities": analysis.entities,
        "content_sections": analysis.content_sections,
    }, indent=2)

    logger.info("Running discovery with provider=%s", provider.name)
    raw_response = await provider.analyze(analysis_json, DISCOVERY_PROMPT)

    proposals: list[SubprojectProposal] = []

    # If this is the fallback provider, generate a single placeholder proposal
    try:
        parsed = json.loads(raw_response)
    except (json.JSONDecodeError, TypeError):
        logger.warning("Discovery response was not valid JSON")
        return [SubprojectProposal(
            suggested_name="Review this resource",
            description="LLM discovery did not produce valid output. Review the resource manually.",
            confidence=0.1,
            is_synthetic=True,
        )]

    if parsed.get("_synthetic"):
        # Fallback provider — generate one placeholder proposal
        return [SubprojectProposal(
            suggested_name="Review this resource",
            description="No LLM provider was available. Review the extracted content to identify projects manually.",
            confidence=0.1,
            is_synthetic=True,
        )]

    raw_proposals = parsed.get("proposals", [])
    if isinstance(raw_proposals, list):
        for p in raw_proposals:
            if not isinstance(p, dict):
                continue
            proposals.append(SubprojectProposal(
                suggested_name=p.get("name", "Unnamed"),
                description=p.get("description", ""),
                type=p.get("type", "research"),
                repos=p.get("repos", []),
                dependencies=p.get("dependencies", []),
                setup_steps=p.get("setup_steps", []),
                complexity=p.get("complexity", "medium"),
                confidence=float(p.get("confidence", 0.5)),
                source_context=p.get("source_context", ""),
                is_synthetic=False,
            ))

    if not proposals:
        proposals.append(SubprojectProposal(
            suggested_name="Review this resource",
            description="No distinct projects were identified. Review manually.",
            confidence=0.1,
            is_synthetic=True,
        ))

    return proposals
