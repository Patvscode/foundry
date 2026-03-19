"""Abstract base for LLM providers used by the ingestion pipeline."""

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Interface for LLM providers. Used for analysis and discovery stages."""

    name: str

    @abstractmethod
    async def analyze(self, content: str, prompt: str) -> str:
        """Send content + prompt to the LLM. Returns raw text response."""

    async def health(self) -> bool:
        """Check if this provider is reachable. Default: True."""
        return True
