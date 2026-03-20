"""Execution log table for workspace-scoped shell commands."""


async def upgrade(conn) -> None:
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS execution_log (
            id TEXT PRIMARY KEY,
            subproject_id TEXT NOT NULL,
            command TEXT NOT NULL,
            action_type TEXT NOT NULL DEFAULT 'shell',
            working_dir TEXT NOT NULL,
            exit_code INTEGER,
            stdout TEXT DEFAULT '',
            stderr TEXT DEFAULT '',
            duration_ms INTEGER,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            FOREIGN KEY (subproject_id) REFERENCES subprojects(id)
        )
    """)
    await conn.commit()
