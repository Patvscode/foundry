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


# ── Resources ─────────────────────────────────────────────────────────────


def _coarse_status(pipeline_status: str) -> str:
    """Derive coarse lifecycle status from detailed pipeline_status."""
    if pipeline_status == "pending":
        return "pending"
    if pipeline_status.endswith("_failed"):
        return "failed"
    if pipeline_status == "discovered":
        return "completed"
    return "processing"


async def insert_resource(
    db: Database,
    resource_id: str,
    project_id: str,
    resource_type: str,
    url: str,
    title: str = "",
) -> dict[str, Any]:
    """Insert a new resource with pending status."""
    now = _now()
    await db.execute(
        """
        INSERT INTO resources (id, project_id, type, url, title, status, pipeline_status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, 'pending', 'pending', ?, ?)
        """,
        (resource_id, project_id, resource_type, url, title, now, now),
    )
    await db.commit()
    return {
        "id": resource_id,
        "project_id": project_id,
        "type": resource_type,
        "url": url,
        "title": title or url,
        "status": "pending",
        "pipeline_status": "pending",
        "pipeline_error": None,
        "created_at": now,
        "updated_at": now,
    }


async def list_resources_for_project(db: Database, project_id: str) -> list[dict[str, Any]]:
    """List all resources for a project, most recent first."""
    rows = await db.fetchall(
        "SELECT * FROM resources WHERE project_id = ? ORDER BY created_at DESC",
        (project_id,),
    )
    return [dict(row) for row in rows]


async def get_resource(db: Database, resource_id: str) -> dict[str, Any] | None:
    """Fetch a single resource by ID."""
    row = await db.fetchone("SELECT * FROM resources WHERE id = ?", (resource_id,))
    if row is None:
        return None
    return dict(row)


async def update_resource_status(
    db: Database,
    resource_id: str,
    pipeline_status: str,
    error: str | None = None,
    content_hash: str | None = None,
    raw_content_path: str | None = None,
    title: str | None = None,
) -> None:
    """Update resource pipeline_status and derive coarse status automatically."""
    fields: dict[str, Any] = {
        "pipeline_status": pipeline_status,
        "status": _coarse_status(pipeline_status),
        "pipeline_error": error,
        "updated_at": _now(),
    }
    if content_hash is not None:
        fields["content_hash"] = content_hash
    if raw_content_path is not None:
        fields["raw_content_path"] = raw_content_path
    if title is not None:
        fields["title"] = title

    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [resource_id]
    await db.execute(f"UPDATE resources SET {set_clause} WHERE id = ?", tuple(values))
    await db.commit()


# ── Extraction Results ────────────────────────────────────────────────────


async def insert_extraction_result(
    db: Database,
    resource_id: str,
    analysis: Any,  # AnalysisResult
) -> str:
    """Store analysis results for a resource."""
    result_id = new_id()
    await db.execute(
        """
        INSERT INTO extraction_results
            (id, resource_id, summary, key_concepts, entities, content_sections,
             open_questions, follow_up_suggestions, model_used, raw_response, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            result_id,
            resource_id,
            analysis.summary,
            json.dumps(analysis.key_concepts),
            json.dumps(analysis.entities),
            json.dumps(analysis.content_sections),
            json.dumps(analysis.open_questions),
            json.dumps(analysis.follow_up_suggestions),
            analysis.model_used,
            analysis.raw_response,
            _now(),
        ),
    )
    await db.commit()
    return result_id


async def update_extraction_proposals(
    db: Database,
    resource_id: str,
    proposals: list[Any],  # list[SubprojectProposal]
) -> None:
    """Update the discovered_projects field on the extraction result."""
    proposals_json = json.dumps([
        {
            "suggested_name": p.suggested_name,
            "description": p.description,
            "type": p.type,
            "repos": p.repos,
            "dependencies": p.dependencies,
            "setup_steps": p.setup_steps,
            "complexity": p.complexity,
            "confidence": p.confidence,
            "source_context": p.source_context,
            "is_synthetic": p.is_synthetic,
        }
        for p in proposals
    ])
    await db.execute(
        "UPDATE extraction_results SET discovered_projects = ? WHERE resource_id = ?",
        (proposals_json, resource_id),
    )
    await db.commit()


async def get_extraction_result(db: Database, resource_id: str) -> dict[str, Any] | None:
    """Fetch extraction result for a resource."""
    row = await db.fetchone(
        "SELECT * FROM extraction_results WHERE resource_id = ? ORDER BY created_at DESC LIMIT 1",
        (resource_id,),
    )
    if row is None:
        return None
    d = dict(row)
    for field in ("key_concepts", "entities", "content_sections", "discovered_projects",
                  "open_questions", "follow_up_suggestions", "token_usage"):
        if d.get(field):
            try:
                d[field] = json.loads(d[field])
            except (json.JSONDecodeError, TypeError):
                pass
    return d


# ── Jobs ──────────────────────────────────────────────────────────────────


async def insert_job(
    db: Database,
    job_id: str,
    job_type: str,
    project_id: str | None = None,
    result: str | None = None,
) -> dict[str, Any]:
    """Insert a queued job. For ingestion jobs, result stores the resource_id."""
    now = _now()
    await db.execute(
        """
        INSERT INTO jobs (id, type, project_id, status, result, created_at)
        VALUES (?, ?, ?, 'queued', ?, ?)
        """,
        (job_id, job_type, project_id, result, now),
    )
    await db.commit()
    return {"id": job_id, "type": job_type, "status": "queued", "created_at": now}


async def get_queued_jobs(db: Database, limit: int = 1) -> list[dict[str, Any]]:
    """Fetch queued jobs, oldest first."""
    rows = await db.fetchall(
        "SELECT * FROM jobs WHERE status = 'queued' ORDER BY created_at ASC LIMIT ?",
        (limit,),
    )
    return [dict(row) for row in rows]


async def update_job(
    db: Database,
    job_id: str,
    status: str | None = None,
    pid: int | None = None,
    error: str | None = None,
    progress_pct: int | None = None,
) -> None:
    """Update job fields."""
    fields: dict[str, Any] = {}
    if status is not None:
        fields["status"] = status
    if pid is not None:
        fields["pid"] = pid
    if error is not None:
        fields["error"] = error
    if progress_pct is not None:
        fields["progress_pct"] = progress_pct
    if status in ("completed", "failed", "stale"):
        fields["completed_at"] = _now()
    if status == "running":
        fields["started_at"] = _now()
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [job_id]
    await db.execute(f"UPDATE jobs SET {set_clause} WHERE id = ?", tuple(values))
    await db.commit()


async def mark_stale_jobs(db: Database) -> int:
    """Mark any 'running' jobs as 'stale' on startup."""
    now = _now()
    cursor = await db.execute(
        "UPDATE jobs SET status = 'stale', error = 'Process did not survive restart', completed_at = ? WHERE status = 'running'",
        (now,),
    )
    await db.commit()
    return cursor.rowcount


# ── Subprojects ───────────────────────────────────────────────────────────


async def insert_subproject(
    db: Database,
    subproject_id: str,
    project_id: str,
    name: str,
    description: str = "",
    subproject_type: str = "research",
    workspace_path: str = "",
    dependencies: list[str] | None = None,
    setup_steps: list[str] | None = None,
    complexity: str = "medium",
    sort_order: int = 0,
) -> dict[str, Any]:
    """Insert an accepted subproject."""
    now = _now()
    await db.execute(
        """
        INSERT INTO subprojects
            (id, project_id, name, description, type, status, workspace_path,
             dependencies, setup_steps, complexity, sort_order, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, 'approved', ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            subproject_id, project_id, name, description, subproject_type,
            workspace_path, json.dumps(dependencies or []),
            json.dumps(setup_steps or []), complexity, sort_order, now, now,
        ),
    )
    await db.commit()
    return {
        "id": subproject_id,
        "project_id": project_id,
        "name": name,
        "description": description,
        "type": subproject_type,
        "status": "approved",
        "workspace_path": workspace_path,
        "dependencies": dependencies or [],
        "setup_steps": setup_steps or [],
        "complexity": complexity,
        "sort_order": sort_order,
        "created_at": now,
        "updated_at": now,
    }


async def list_subprojects_for_project(db: Database, project_id: str) -> list[dict[str, Any]]:
    """List subprojects for a project, ordered by sort_order."""
    rows = await db.fetchall(
        "SELECT * FROM subprojects WHERE project_id = ? ORDER BY sort_order ASC, created_at ASC",
        (project_id,),
    )
    results = []
    for row in rows:
        d = dict(row)
        for field in ("dependencies", "setup_steps"):
            if d.get(field):
                try:
                    d[field] = json.loads(d[field])
                except (json.JSONDecodeError, TypeError):
                    pass
        results.append(d)
    return results


# ── Provenance ────────────────────────────────────────────────────────────


async def insert_provenance_link(
    db: Database,
    resource_id: str,
    target_type: str,
    target_id: str,
    context: str = "",
    quote: str = "",
    confidence: float = 1.0,
) -> str:
    """Create a provenance link from a resource to a target entity."""
    link_id = new_id()
    await db.execute(
        """
        INSERT INTO provenance_links (id, resource_id, target_type, target_id, context, quote, confidence, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (link_id, resource_id, target_type, target_id, context, quote, confidence, _now()),
    )
    await db.commit()
    return link_id


# ── Proposal Decisions ────────────────────────────────────────────────────


async def update_proposal_decision(
    db: Database,
    resource_id: str,
    proposal_index: int,
    decision: str,
    edited_fields: dict[str, Any] | None = None,
) -> bool:
    """Update the decision on a specific proposal within discovered_projects JSON.

    Also merges any edited fields (name, description, type) into the proposal.
    """
    result = await get_extraction_result(db, resource_id)
    if result is None:
        return False

    proposals = result.get("discovered_projects")
    if not isinstance(proposals, list) or proposal_index >= len(proposals):
        return False

    proposals[proposal_index]["decision"] = decision
    if edited_fields:
        for key, value in edited_fields.items():
            if key in ("suggested_name", "description", "type"):
                proposals[proposal_index][key] = value

    await db.execute(
        "UPDATE extraction_results SET discovered_projects = ? WHERE resource_id = ?",
        (json.dumps(proposals), resource_id),
    )
    await db.commit()
    return True
