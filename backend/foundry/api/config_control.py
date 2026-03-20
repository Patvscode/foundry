"""Runtime configuration control. Read/write persistent settings that override config.toml.

Settings are stored in the DB settings_store table and override file-based config at runtime.
This lets the UI control provider, model, swarm, and execution settings without editing TOML.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from foundry.storage.database import Database

router = APIRouter(prefix="/system/config", tags=["config-control"])
logger = logging.getLogger(__name__)

# Keys that can be controlled at runtime
ALLOWED_KEYS = {
    "agent.default_provider",
    "agent.default_model",
    "agent.can_execute",
    "ingestion.swarm.mode",              # "single" | "swarm"
    "ingestion.swarm.coordinator_provider",
    "ingestion.swarm.coordinator_model",
    "ingestion.swarm.worker_provider",
    "ingestion.swarm.worker_model",
    "ingestion.swarm.max_workers",
    "ingestion.swarm.use_critic",
    "ingestion.swarm.max_depth",
    "setup.completed",
}


class ConfigUpdate(BaseModel):
    settings: dict[str, Any]


async def get_setting(db: Database, key: str) -> str | None:
    """Get a single setting from the store."""
    row = await db.fetchone("SELECT value FROM settings_store WHERE key = ?", (key,))
    return row["value"] if row else None


async def get_all_settings(db: Database) -> dict[str, Any]:
    """Get all runtime settings."""
    rows = await db.fetchall("SELECT key, value FROM settings_store")
    result: dict[str, Any] = {}
    for row in rows:
        try:
            result[row["key"]] = json.loads(row["value"])
        except (json.JSONDecodeError, TypeError):
            result[row["key"]] = row["value"]
    return result


async def set_setting(db: Database, key: str, value: Any) -> None:
    """Set a single setting."""
    from foundry.storage.queries import _now
    serialized = json.dumps(value) if not isinstance(value, str) else json.dumps(value)
    await db.execute(
        """
        INSERT INTO settings_store (key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
        """,
        (key, serialized, _now()),
    )
    await db.commit()


@router.get("/runtime")
async def get_runtime_config(request: Request) -> dict[str, Any]:
    """Get all runtime settings that override config.toml."""
    db: Database = request.app.state.db
    settings = await get_all_settings(db)
    return {
        "settings": settings,
        "allowed_keys": sorted(ALLOWED_KEYS),
    }


@router.put("/runtime")
async def update_runtime_config(body: ConfigUpdate, request: Request) -> dict[str, Any]:
    """Update runtime settings. Only allowed keys are accepted."""
    db: Database = request.app.state.db

    applied: dict[str, Any] = {}
    rejected: dict[str, str] = {}

    for key, value in body.settings.items():
        if key not in ALLOWED_KEYS:
            rejected[key] = "not an allowed runtime key"
            continue
        await set_setting(db, key, value)
        applied[key] = value

    # Update the in-memory settings on the app
    _apply_to_runtime(request, applied)

    return {
        "applied": applied,
        "rejected": rejected,
        "all_settings": await get_all_settings(db),
    }


def _apply_to_runtime(request: Request, settings: dict[str, Any]) -> None:
    """Apply settings to the live app.state.settings object."""
    app_settings = request.app.state.settings

    for key, value in settings.items():
        if key == "agent.default_provider":
            app_settings.agent.default_provider = str(value)
        elif key == "agent.default_model":
            app_settings.agent.default_model = str(value)
        elif key == "agent.can_execute":
            app_settings.agent.can_execute = bool(value)


async def load_runtime_settings_into_app(db: Database, settings: Any) -> None:
    """Called at startup to load persisted runtime settings over file config."""
    stored = await get_all_settings(db)
    for key, value in stored.items():
        if key == "agent.default_provider":
            settings.agent.default_provider = str(value)
        elif key == "agent.default_model":
            settings.agent.default_model = str(value)
        elif key == "agent.can_execute":
            settings.agent.can_execute = bool(value)
    if stored:
        logger.info("Loaded %d runtime settings from DB", len(stored))
