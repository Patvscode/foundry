from __future__ import annotations

import importlib.metadata
import shutil
import time
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, Request

from foundry.config import FoundrySettings, mask_secrets
from foundry.storage.database import Database

router = APIRouter(prefix="/system", tags=["system"])


def _get_version() -> str:
    try:
        return importlib.metadata.version("foundry")
    except importlib.metadata.PackageNotFoundError:
        return "0.1.0"


async def _check_agent_provider(settings: FoundrySettings) -> str:
    if settings.agent.default_provider == "none":
        return "none"

    if settings.agent.default_provider == "ollama":
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                response = await client.get(f"{settings.agent.providers.ollama.base_url}/api/tags")
            if response.status_code < 400:
                return "ollama (connected)"
            return "ollama (error)"
        except (httpx.HTTPError, ValueError):
            return "ollama (error)"

    return settings.agent.default_provider


async def _count_active_projects(db: Database) -> int:
    row = await db.fetchone("SELECT COUNT(*) AS count FROM projects WHERE status = 'active'")
    return int(row["count"]) if row is not None else 0


async def _count_active_ingestions(db: Database) -> int:
    row = await db.fetchone(
        """
        SELECT COUNT(*) AS count
        FROM jobs
        WHERE type = 'ingestion' AND status IN ('queued', 'running')
        """
    )
    return int(row["count"]) if row is not None else 0


@router.get("/health")
async def health(request: Request) -> dict[str, Any]:
    settings: FoundrySettings = request.app.state.settings
    db: Database = request.app.state.db

    db_status = "ok"
    try:
        await db.fetchone("SELECT 1")
    except Exception:
        db_status = "error"

    workspace_path = Path(settings.storage.data_dir)
    workspace_status = "ok" if workspace_path.exists() and workspace_path.is_dir() else "error"

    disk_free = shutil.disk_usage(workspace_path).free / (1024**3)

    now = time.monotonic()
    started = request.app.state.started_at

    agent_provider = await _check_agent_provider(settings)

    response = {
        "status": "healthy" if db_status == "ok" and workspace_status == "ok" else "degraded",
        "version": _get_version(),
        "uptime_seconds": int(now - started),
        "db": db_status,
        "workspace": workspace_status,
        "disk_free_gb": round(disk_free, 2),
        "agent_provider": agent_provider,
        "agent_model": settings.agent.default_model or "(auto-detect)",
        "execution_enabled": settings.agent.can_execute,
        "active_projects": await _count_active_projects(db),
        "active_ingestions": await _count_active_ingestions(db),
        "pending_reconcile_issues": 0,
    }
    return response


@router.get("/config")
async def config(request: Request) -> dict[str, Any]:
    settings: FoundrySettings = request.app.state.settings
    return mask_secrets(settings.model_dump())


@router.get("/version")
async def version() -> dict[str, str]:
    return {
        "name": "foundry",
        "version": _get_version(),
    }
