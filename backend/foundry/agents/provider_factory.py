"""Factory for creating LLM providers based on configuration and runtime settings."""

from __future__ import annotations

import logging

from foundry.agents.providers.base import LLMProvider
from foundry.agents.providers.fallback import FallbackProvider
from foundry.agents.providers.llamacpp import LlamaCppProvider
from foundry.agents.providers.ollama import OllamaProvider
from foundry.agents.providers.openclaw import OpenClawProvider
from foundry.config import FoundrySettings

logger = logging.getLogger(__name__)


async def get_llm_provider(
    settings: FoundrySettings,
    provider_override: str | None = None,
    model_override: str | None = None,
) -> LLMProvider:
    """Return the best available LLM provider.

    Tries the requested provider first, then falls back gracefully.
    Provider/model can be overridden per-call (used by swarm coordinator vs worker).
    """
    provider_name = provider_override or settings.agent.default_provider
    model = model_override or settings.agent.default_model

    # Try the requested provider
    provider = await _create_provider(provider_name, model, settings)
    if provider and await provider.health():
        logger.info("Using provider: %s (model=%s)", provider.name, model or "auto")
        return provider

    # If requested provider failed, try auto-fallback chain
    if provider_name != "ollama":
        ollama = await _create_provider("ollama", "", settings)
        if ollama and await ollama.health():
            logger.info("Auto-fallback to Ollama")
            return ollama

    if provider_name != "llama-cpp":
        llama = await _create_provider("llama-cpp", "", settings)
        if llama and await llama.health():
            logger.info("Auto-fallback to llama-cpp")
            return llama

    if provider_name != "openclaw":
        oc = await _create_provider("openclaw", "", settings)
        if oc and await oc.health():
            logger.info("Auto-fallback to OpenClaw")
            return oc

    logger.warning("No provider reachable, using fallback (synthetic)")
    return FallbackProvider()


async def _create_provider(
    name: str,
    model: str,
    settings: FoundrySettings,
) -> LLMProvider | None:
    """Instantiate a provider by name. Returns None for unknown providers."""
    if name == "ollama":
        return OllamaProvider(
            base_url=settings.agent.providers.ollama.base_url,
            model=model,
        )
    if name == "llama-cpp":
        return LlamaCppProvider(
            base_url="http://localhost:18080",
            model=model,
        )
    if name == "openclaw":
        return OpenClawProvider(
            gateway_url=settings.agent.providers.openclaw.gateway_url,
            model=model,
        )
    if name in ("none", "fallback"):
        return FallbackProvider()
    return None


async def get_provider_for_role(
    settings: FoundrySettings,
    role: str,
    swarm_settings: dict | None = None,
) -> LLMProvider:
    """Get a provider for a specific swarm role.

    Roles: coordinator, worker, critic
    Falls back to the default provider if no role-specific config exists.
    """
    if not swarm_settings:
        return await get_llm_provider(settings)

    if role == "coordinator":
        provider = swarm_settings.get("coordinator_provider", "")
        model = swarm_settings.get("coordinator_model", "")
    elif role == "worker":
        provider = swarm_settings.get("worker_provider", "")
        model = swarm_settings.get("worker_model", "")
    elif role == "critic":
        # Critic uses coordinator provider by default
        provider = swarm_settings.get("coordinator_provider", "")
        model = swarm_settings.get("coordinator_model", "")
    else:
        provider = ""
        model = ""

    if provider:
        return await get_llm_provider(settings, provider_override=provider, model_override=model)
    return await get_llm_provider(settings)
