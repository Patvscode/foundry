"""Fallback LLM provider. Returns synthetic placeholder results when no real provider is available.

All output from this provider is clearly labeled as synthetic/placeholder so users
and downstream code can distinguish it from real model output.
"""

from __future__ import annotations

import json

from foundry.agents.providers.base import LLMProvider


class FallbackProvider(LLMProvider):
    name = "fallback"

    async def analyze(self, content: str, prompt: str) -> str:
        """Return a structured placeholder analysis. Clearly labeled as synthetic."""
        # Take first 500 chars as a crude summary
        snippet = content[:500].strip()
        if len(content) > 500:
            snippet += "..."

        result = {
            "_synthetic": True,
            "_notice": "This is a placeholder result. No LLM provider was available.",
            "summary": f"[Placeholder] Content begins: {snippet}",
            "key_concepts": [],
            "entities": {"repos": [], "models": [], "datasets": [], "tools": [], "papers": [], "people": []},
            "content_sections": [],
            "open_questions": ["LLM analysis was not available — review this content manually."],
            "follow_up_suggestions": [],
        }
        return json.dumps(result)

    async def health(self) -> bool:
        return True
