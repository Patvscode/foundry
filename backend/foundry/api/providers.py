"""Provider discovery, status, and selection API."""

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
    """Scan for available LLM providers and report status + models."""
    settings: FoundrySettings = request.app.state.settings

    providers: list[dict[str, Any]] = []

    # ── Ollama ────────────────────────────────────────────────────
    ollama = await _probe_ollama(settings.agent.providers.ollama.base_url)
    providers.append(ollama)

    # ── llama.cpp (OpenAI-compatible) ─────────────────────────────
    llama_cpp = await _probe_openai_compatible(
        "http://localhost:18080", "llama-cpp", "llama.cpp (local)",
    )
    providers.append(llama_cpp)

    # ── OpenClaw gateway ──────────────────────────────────────────
    openclaw = await _probe_openai_compatible(
        settings.agent.providers.openclaw.gateway_url,
        "openclaw", "OpenClaw Gateway",
    )
    providers.append(openclaw)

    # ── OpenAI API ────────────────────────────────────────────────
    openai_key = settings.agent.providers.openai.api_key
    providers.append({
        "id": "openai",
        "name": "OpenAI API",
        "status": "configured" if openai_key else "not_configured",
        "models": [{"name": "gpt-4o"}, {"name": "gpt-4o-mini"}] if openai_key else [],
        "requires": "API key in config (agent.providers.openai.api_key)",
        "configured": bool(openai_key),
    })

    # ── Anthropic API ─────────────────────────────────────────────
    anthropic_key = settings.agent.providers.anthropic.api_key
    providers.append({
        "id": "anthropic",
        "name": "Anthropic API",
        "status": "configured" if anthropic_key else "not_configured",
        "models": [{"name": "claude-sonnet-4-20250514"}] if anthropic_key else [],
        "requires": "API key in config (agent.providers.anthropic.api_key)",
        "configured": bool(anthropic_key),
    })

    # ── Fallback ──────────────────────────────────────────────────
    providers.append({
        "id": "fallback",
        "name": "Fallback (synthetic placeholders)",
        "status": "always_available",
        "models": [{"name": "placeholder"}],
        "requires": "Nothing — always works",
        "configured": True,
    })

    # ── Determine current state ───────────────────────────────────
    active = settings.agent.default_provider
    active_model = settings.agent.default_model
    recommended = _recommend(providers)
    mode = _classify_mode(active, providers)

    # ── Swarm config from runtime settings ────────────────────────
    db = request.app.state.db
    from foundry.api.config_control import get_all_settings
    runtime = await get_all_settings(db)

    swarm_config = {
        "mode": runtime.get("ingestion.swarm.mode", "single"),
        "coordinator_provider": runtime.get("ingestion.swarm.coordinator_provider", ""),
        "coordinator_model": runtime.get("ingestion.swarm.coordinator_model", ""),
        "worker_provider": runtime.get("ingestion.swarm.worker_provider", ""),
        "worker_model": runtime.get("ingestion.swarm.worker_model", ""),
        "max_workers": runtime.get("ingestion.swarm.max_workers", 4),
        "use_critic": runtime.get("ingestion.swarm.use_critic", False),
        "max_depth": runtime.get("ingestion.swarm.max_depth", 1),
    }

    return {
        "providers": providers,
        "active_provider": active,
        "active_model": active_model,
        "recommended": recommended,
        "mode": mode,
        "swarm": swarm_config,
        "setup_completed": runtime.get("setup.completed", False),
        "setup_hint": _setup_hint(providers, mode),
    }


async def _probe_ollama(base_url: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": "ollama", "name": "Ollama (local)", "status": "not_reachable",
        "base_url": base_url, "models": [],
        "requires": f"Ollama running at {base_url}", "configured": True,
    }
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{base_url}/api/tags")
            if resp.status_code < 400:
                models = resp.json().get("models", [])
                result["status"] = "connected"
                result["models"] = [
                    {"name": m["name"], "size_gb": round(m.get("size", 0) / 1e9, 1),
                     "parameter_size": m.get("details", {}).get("parameter_size", "")}
                    for m in models
                ]
    except Exception:
        pass
    return result


async def _probe_openai_compatible(base_url: str, pid: str, pname: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": pid, "name": pname, "status": "not_reachable",
        "base_url": base_url, "models": [],
        "requires": f"Server running at {base_url}", "configured": True,
    }
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{base_url}/v1/models")
            if resp.status_code < 400:
                data = resp.json()
                models = data.get("data", [])
                result["status"] = "connected"
                result["models"] = [{"name": m.get("id", "unknown")} for m in models]
    except Exception:
        pass
    return result


def _recommend(providers: list[dict[str, Any]]) -> str:
    for pid in ("ollama", "llama-cpp", "openclaw", "openai", "anthropic"):
        for p in providers:
            if p["id"] == pid and p["status"] in ("connected", "configured") and p.get("models"):
                return pid
    return "fallback"


def _classify_mode(active: str, providers: list[dict[str, Any]]) -> str:
    if active in ("openai", "anthropic"):
        return "api"
    if active in ("none", "fallback"):
        return "fallback"
    for p in providers:
        if p["id"] == active and p["status"] == "connected":
            return "local"
    return "fallback"


def _setup_hint(providers: list[dict[str, Any]], mode: str) -> str:
    if mode == "local":
        return "Local model connected and active. Ready for real ingestion."
    if mode == "api":
        return "API provider configured. Ingestion will use cloud models."
    connected = [p for p in providers if p["status"] == "connected"]
    if connected:
        names = ", ".join(p["name"] for p in connected)
        return f"Providers available: {names}. Select one as default in Settings."
    return (
        "No providers connected. To get started:\n"
        "• Ollama: ollama serve && ollama pull qwen3.5:4b\n"
        "• llama.cpp: start server on port 18080\n"
        "• API: add openai or anthropic key in config"
    )
