"""Provider discovery and status API. Shows what's available locally."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from fastapi import APIRouter, Request

from foundry.config import FoundrySettings

router = APIRouter(prefix="/system/providers", tags=["providers"])
logger = logging.getLogger(__name__)


@router.get("")
async def list_providers(request: Request) -> dict[str, Any]:
    """Scan for available LLM providers and report status."""
    settings: FoundrySettings = request.app.state.settings

    providers: list[dict[str, Any]] = []
    recommended: str | None = None

    # ── Ollama ────────────────────────────────────────────────────
    ollama = await _probe_ollama(settings.agent.providers.ollama.base_url)
    providers.append(ollama)

    # ── llama.cpp (OpenAI-compatible) ─────────────────────────────
    llama_cpp = await _probe_openai_compatible(
        "http://localhost:18080",
        "llama-cpp",
        "llama.cpp server (local)",
    )
    providers.append(llama_cpp)

    # ── OpenAI API ────────────────────────────────────────────────
    openai_key = settings.agent.providers.openai.api_key
    providers.append({
        "id": "openai",
        "name": "OpenAI API",
        "status": "configured" if openai_key else "not_configured",
        "models": [],
        "requires": "API key in config (agent.providers.openai.api_key)",
        "configured": bool(openai_key),
    })

    # ── Anthropic API ─────────────────────────────────────────────
    anthropic_key = settings.agent.providers.anthropic.api_key
    providers.append({
        "id": "anthropic",
        "name": "Anthropic API",
        "status": "configured" if anthropic_key else "not_configured",
        "models": [],
        "requires": "API key in config (agent.providers.anthropic.api_key)",
        "configured": bool(anthropic_key),
    })

    # ── Fallback ──────────────────────────────────────────────────
    providers.append({
        "id": "fallback",
        "name": "Fallback (synthetic placeholders)",
        "status": "always_available",
        "models": ["placeholder"],
        "requires": "Nothing — always works",
        "configured": True,
    })

    # ── Determine recommendation ──────────────────────────────────
    active = settings.agent.default_provider
    active_model = settings.agent.default_model

    if ollama["status"] == "connected" and ollama["models"]:
        recommended = "ollama"
    elif llama_cpp["status"] == "connected":
        recommended = "llama-cpp"
    elif openai_key:
        recommended = "openai"
    elif anthropic_key:
        recommended = "anthropic"
    else:
        recommended = "fallback"

    return {
        "providers": providers,
        "active_provider": active,
        "active_model": active_model,
        "recommended": recommended,
        "mode": _classify_mode(active, providers),
        "setup_hint": _setup_hint(providers),
    }


async def _probe_ollama(base_url: str) -> dict[str, Any]:
    """Probe Ollama API for models."""
    result: dict[str, Any] = {
        "id": "ollama",
        "name": "Ollama (local)",
        "status": "not_reachable",
        "base_url": base_url,
        "models": [],
        "requires": f"Ollama running at {base_url}",
        "configured": True,
    }
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{base_url}/api/tags")
            if resp.status_code < 400:
                data = resp.json()
                models = data.get("models", [])
                result["status"] = "connected"
                result["models"] = [
                    {
                        "name": m["name"],
                        "size_gb": round(m.get("size", 0) / 1e9, 1),
                        "parameter_size": m.get("details", {}).get("parameter_size", ""),
                    }
                    for m in models
                ]
    except Exception as e:
        logger.debug("Ollama probe failed: %s", e)
    return result


async def _probe_openai_compatible(
    base_url: str, provider_id: str, provider_name: str
) -> dict[str, Any]:
    """Probe an OpenAI-compatible API for models."""
    result: dict[str, Any] = {
        "id": provider_id,
        "name": provider_name,
        "status": "not_reachable",
        "base_url": base_url,
        "models": [],
        "requires": f"Server running at {base_url}",
        "configured": True,
    }
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{base_url}/v1/models")
            if resp.status_code < 400:
                data = resp.json()
                models = data.get("data", [])
                result["status"] = "connected"
                result["models"] = [{"name": m.get("id", "unknown")} for m in models]
    except Exception as e:
        logger.debug("%s probe failed: %s", provider_id, e)
    return result


def _classify_mode(active_provider: str, providers: list[dict[str, Any]]) -> str:
    """Classify the current operating mode."""
    if active_provider in ("openai", "anthropic"):
        return "api"
    if active_provider == "none" or active_provider == "fallback":
        return "fallback"
    # Check if the local provider is actually reachable
    for p in providers:
        if p["id"] == active_provider and p["status"] == "connected":
            return "local"
    return "fallback"


def _setup_hint(providers: list[dict[str, Any]]) -> str:
    """Provide a human-readable setup hint."""
    connected = [p for p in providers if p["status"] == "connected"]
    if connected:
        names = ", ".join(p["name"] for p in connected)
        return f"Connected to: {names}. Set agent.default_provider and agent.default_model in ~/.foundry/config.toml."
    return (
        "No local providers detected. Options:\n"
        "1. Start Ollama: ollama serve, then ollama pull qwen3.5:4b\n"
        "2. Add an API key: set agent.providers.openai.api_key in ~/.foundry/config.toml\n"
        "3. Use fallback mode: set agent.default_provider = 'none' (synthetic placeholders)"
    )
