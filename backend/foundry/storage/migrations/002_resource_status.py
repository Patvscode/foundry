"""Add coarse resource.status column separate from pipeline_status.

status = lifecycle state: pending | processing | completed | failed
pipeline_status = detailed stage: extracting | extracted | analyzing | etc.
"""

from __future__ import annotations

import aiosqlite


async def upgrade(conn: aiosqlite.Connection) -> None:
    # Add the status column with default 'pending'
    await conn.execute(
        "ALTER TABLE resources ADD COLUMN status TEXT DEFAULT 'pending'"
    )
    # Backfill existing rows based on pipeline_status
    await conn.execute("""
        UPDATE resources SET status = CASE
            WHEN pipeline_status IN ('pending') THEN 'pending'
            WHEN pipeline_status IN ('extracting', 'extracted', 'analyzing', 'analyzed', 'discovering') THEN 'processing'
            WHEN pipeline_status IN ('discovered') THEN 'completed'
            WHEN pipeline_status LIKE '%_failed' THEN 'failed'
            ELSE 'pending'
        END
    """)
    await conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_resources_status ON resources(status)"
    )
