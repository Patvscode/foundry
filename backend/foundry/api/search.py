"""Unified search API across all entity types."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Request

from foundry.search.engine import rebuild_index, search
from foundry.storage.database import Database

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
async def search_all(
    request: Request,
    q: str = Query(..., min_length=1, max_length=200),
    types: str | None = Query(None, description="Comma-separated entity types to filter"),
    limit: int = Query(25, ge=1, le=100),
) -> dict[str, Any]:
    """Search across projects, resources, subprojects, tasks, and notes."""
    db: Database = request.app.state.db

    entity_types = None
    if types:
        entity_types = [t.strip() for t in types.split(",") if t.strip()]

    results = await search(db, q, entity_types=entity_types, limit=limit)

    # Group by entity type
    grouped: dict[str, list[dict[str, Any]]] = {}
    for r in results:
        et = r["entity_type"]
        grouped.setdefault(et, []).append(r)

    return {
        "query": q,
        "total": len(results),
        "results": results,
        "grouped": grouped,
    }


@router.post("/rebuild")
async def rebuild(request: Request) -> dict[str, Any]:
    """Rebuild the full-text search index from all source tables."""
    db: Database = request.app.state.db
    count = await rebuild_index(db)
    return {"status": "ok", "indexed": count}
