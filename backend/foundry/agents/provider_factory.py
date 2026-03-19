"""Factory for creating LLM providers based on configuration."""

from __future__ import annotations

import logging

from foundry.agents.providers.base import LLMProvider
from foundry.agents.providers.fallback import FallbackProvider
from foundry.agents.providers.ollama import OllamaProvider
from foundry.config import FoundrySettings

logger = logging.getLogger(__name__)


async def get_llm_provider(settings: FoundrySettings) -> LLMProvider:
    """Return the best available LLM provider. Falls back to FallbackProvider."""
    provider_name = settings.agent.default_provider

    if provider_name == "ollama":
        provider = OllamaProvider(
            base_url=settings.agent.providers.ollama.base_url,
            model=settings.agent.default_model,
        )
        if await provider.health():
            logger.info("Using Ollama provider at %s", settings.agent.providers.ollama.base_url)
            return provider
        logger.warning("Ollama not reachable, falling back to placeholder provider")

    if provider_name == "none":
        logger.info("No LLM provider configured, using placeholder provider")

    return FallbackProvider()
