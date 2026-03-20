"""Persistent key-value settings store for runtime configuration."""


async def upgrade(conn) -> None:
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS settings_store (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    await conn.commit()
