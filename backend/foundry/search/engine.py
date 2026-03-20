"""FTS5-backed search engine. Indexes and queries across all entity types."""

from __future__ import annotations

import logging
from typing import Any

from foundry.storage.database import Database

logger = logging.getLogger(__name__)


async def index_entity(
    db: Database,
    entity_type: str,
    entity_id: str,
    title: str,
    body: str = "",
    parent_id: str = "",
) -> None:
    """Insert or replace an entity in the search index."""
    # Delete existing entry first (FTS5 doesn't support REPLACE)
    await db.execute(
        "DELETE FROM search_index WHERE entity_id = ? AND entity_type = ?",
        (entity_id, entity_type),
    )
    await db.execute(
        "INSERT INTO search_index (entity_type, entity_id, title, body, parent_id) VALUES (?, ?, ?, ?, ?)",
        (entity_type, entity_id, title, body, parent_id),
    )
    await db.commit()


async def remove_entity(db: Database, entity_type: str, entity_id: str) -> None:
    """Remove an entity from the search index."""
    await db.execute(
        "DELETE FROM search_index WHERE entity_id = ? AND entity_type = ?",
        (entity_id, entity_type),
    )
    await db.commit()


async def search(
    db: Database,
    query: str,
    entity_types: list[str] | None = None,
    limit: int = 25,
) -> list[dict[str, Any]]:
    """Search across indexed entities. Returns ranked results."""
    if not query or not query.strip():
        return []

    # Sanitize query for FTS5
    clean = _sanitize_fts_query(query.strip())
    if not clean:
        return []

    type_filter = ""
    params: list[Any] = [clean]

    if entity_types:
        placeholders = ", ".join("?" for _ in entity_types)
        type_filter = f"AND entity_type IN ({placeholders})"
        params.extend(entity_types)

    params.append(limit)

    rows = await db.fetchall(
        f"""
        SELECT entity_type, entity_id, title, snippet(search_index, 3, '<mark>', '</mark>', '…', 40) AS snippet,
               parent_id, rank
        FROM search_index
        WHERE search_index MATCH ? {type_filter}
        ORDER BY rank
        LIMIT ?
        """,
        tuple(params),
    )
    return [dict(row) for row in rows]


async def rebuild_index(db: Database) -> int:
    """Rebuild the entire search index from source tables. Returns count indexed."""
    await db.execute("DELETE FROM search_index")
    count = 0

    # Projects
    rows = await db.fetchall("SELECT id, name, description FROM projects WHERE status != 'deleted'")
    for row in rows:
        await db.execute(
            "INSERT INTO search_index (entity_type, entity_id, title, body, parent_id) VALUES (?, ?, ?, ?, ?)",
            ("project", row["id"], row["name"], row["description"] or "", ""),
        )
        count += 1

    # Resources
    rows = await db.fetchall("SELECT id, project_id, url, title FROM resources")
    for row in rows:
        await db.execute(
            "INSERT INTO search_index (entity_type, entity_id, title, body, parent_id) VALUES (?, ?, ?, ?, ?)",
            ("resource", row["id"], row["title"] or row["url"], row["url"], row["project_id"]),
        )
        count += 1

    # Subprojects
    rows = await db.fetchall("SELECT id, project_id, name, description FROM subprojects")
    for row in rows:
        await db.execute(
            "INSERT INTO search_index (entity_type, entity_id, title, body, parent_id) VALUES (?, ?, ?, ?, ?)",
            ("subproject", row["id"], row["name"], row["description"] or "", row["project_id"]),
        )
        count += 1

    # Tasks
    rows = await db.fetchall("SELECT id, subproject_id, title, description FROM tasks")
    for row in rows:
        await db.execute(
            "INSERT INTO search_index (entity_type, entity_id, title, body, parent_id) VALUES (?, ?, ?, ?, ?)",
            ("task", row["id"], row["title"], row["description"] or "", row["subproject_id"]),
        )
        count += 1

    # Notes
    rows = await db.fetchall("SELECT id, subproject_id, title, content FROM notes")
    for row in rows:
        await db.execute(
            "INSERT INTO search_index (entity_type, entity_id, title, body, parent_id) VALUES (?, ?, ?, ?, ?)",
            ("note", row["id"], row["title"], row["content"] or "", row["subproject_id"]),
        )
        count += 1

    await db.commit()
    logger.info("Rebuilt search index: %d entities", count)
    return count


def _sanitize_fts_query(query: str) -> str:
    """Make a user query safe for FTS5 MATCH. Wraps each term in quotes."""
    # Strip FTS5 operators that could cause syntax errors
    terms = []
    for word in query.split():
        clean = word.strip('"\'(){}[]<>*')
        if clean and len(clean) >= 1:
            # Escape internal quotes
            clean = clean.replace('"', '')
            if clean:
                terms.append(f'"{clean}"')
    return " ".join(terms)
