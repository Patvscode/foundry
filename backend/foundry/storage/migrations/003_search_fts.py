"""FTS5 virtual tables for full-text search across projects, resources, subprojects, tasks, notes."""


async def upgrade(conn) -> None:
    # Drop existing table if schema changed
    await conn.execute("DROP TABLE IF EXISTS search_index")
    await conn.execute("""
        CREATE VIRTUAL TABLE search_index USING fts5(
            entity_type,
            entity_id,
            title,
            body,
            parent_id,
            tokenize='porter unicode61'
        )
    """)
    await conn.commit()
