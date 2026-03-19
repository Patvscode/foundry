"""Thin async query layer over SQLite. Keeps SQL out of API handlers."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from foundry.storage.database import Database


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    """Generate a new UUID. Public so callers can pre-generate IDs."""
    return str(uuid.uuid4())


# ── Projects ──────────────────────────────────────────────────────────────


async def insert_project(
    db: Database,
    project_id: str,
    name: str,
    workspace_path: str,
    description: str = "",
    settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Insert a new project with all final values. No partial inserts."""
    now = _now()
    await db.execute(
        """
        INSERT INTO projects (id, name, description, status, workspace_path, settings, created_at, updated_at)
        VALUES (?, ?, ?, 'active', ?, ?, ?, ?)
        """,
        (project_id, name, description, workspace_path, json.dumps(settings or {}), now, now),
    )
    await db.commit()
    return {
        "id": project_id,
        "name": name,
        "description": description,
        "status": "active",
        "workspace_path": workspace_path,
        "settings": settings or {},
        "created_at": now,
        "updated_at": now,
    }


async def list_projects(db: Database) -> list[dict[str, Any]]:
    """List all non-deleted projects, most recent first, with subproject counts."""
    rows = await db.fetchall(
        """
        SELECT p.*, COUNT(s.id) AS subproject_count
        FROM projects p
        LEFT JOIN subprojects s ON s.project_id = p.id
        WHERE p.status != 'deleted'
        GROUP BY p.id
        ORDER BY p.created_at DESC
        """
    )
    results = []
    for row in rows:
        d = dict(row)
        if d.get("settings"):
            try:
                d["settings"] = json.loads(d["settings"])
            except (json.JSONDecodeError, TypeError):
                pass
        results.append(d)
    return results


async def get_project(db: Database, project_id: str) -> dict[str, Any] | None:
    """Fetch a single non-deleted project by ID, with subproject count."""
    row = await db.fetchone(
        """
        SELECT p.*, COUNT(s.id) AS subproject_count
        FROM projects p
        LEFT JOIN subprojects s ON s.project_id = p.id
        WHERE p.id = ? AND p.status != 'deleted'
        GROUP BY p.id
        """,
        (project_id,),
    )
    if row is None:
        return None
    d = dict(row)
    if d.get("settings"):
        try:
            d["settings"] = json.loads(d["settings"])
        except (json.JSONDecodeError, TypeError):
            pass
    return d
