from __future__ import annotations

from pathlib import Path

import pytest

from foundry.storage.database import init_database


@pytest.mark.asyncio
async def test_migrations_create_all_required_tables(temp_data_dir: Path) -> None:
    db_path = temp_data_dir / "test.db"
    db = await init_database(db_path)

    rows = await db.fetchall("SELECT name FROM sqlite_master WHERE type IN ('table', 'virtual table')")
    names = {row["name"] for row in rows}

    expected_tables = {
        "schema_migrations",
        "projects",
        "subprojects",
        "resources",
        "extraction_results",
        "tasks",
        "notes",
        "file_assets",
        "environments",
        "agent_sessions",
        "agent_messages",
        "provenance_links",
        "git_configs",
        "jobs",
        "search_index",
    }
    assert expected_tables.issubset(names)

    await db.close()
