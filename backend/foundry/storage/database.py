from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import aiosqlite


class Database:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> aiosqlite.Connection:
        if self._conn is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = await aiosqlite.connect(self.db_path)
            self._conn.row_factory = aiosqlite.Row
            await self._conn.execute("PRAGMA journal_mode=WAL;")
            await self._conn.execute("PRAGMA foreign_keys=ON;")
            await self._conn.execute("PRAGMA synchronous=NORMAL;")
            await self._conn.commit()
        return self._conn

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def execute(self, sql: str, params: tuple | None = None) -> aiosqlite.Cursor:
        conn = await self.connect()
        return await conn.execute(sql, params or ())

    async def fetchone(self, sql: str, params: tuple | None = None) -> aiosqlite.Row | None:
        cursor = await self.execute(sql, params)
        return await cursor.fetchone()

    async def fetchall(self, sql: str, params: tuple | None = None) -> list[aiosqlite.Row]:
        cursor = await self.execute(sql, params)
        return await cursor.fetchall()

    async def commit(self) -> None:
        conn = await self.connect()
        await conn.commit()


_db_instance: Database | None = None


def configure_database(db_path: Path) -> Database:
    global _db_instance
    _db_instance = Database(db_path)
    return _db_instance


def get_database() -> Database:
    if _db_instance is None:
        raise RuntimeError("Database is not configured. Call configure_database first.")
    return _db_instance


async def init_database(db_path: Path) -> Database:
    db = configure_database(db_path)
    await db.connect()
    await run_migrations(db)
    return db


async def run_migrations(db: Database) -> None:
    conn = await db.connect()
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    await conn.commit()

    migration_dir = Path(__file__).resolve().parent / "migrations"
    migration_files = sorted(
        path
        for path in migration_dir.glob("*.py")
        if path.name != "__init__.py" and path.stem[0:3].isdigit()
    )

    for migration_file in migration_files:
        version = migration_file.stem
        existing = await db.fetchone(
            "SELECT version FROM schema_migrations WHERE version = ?", (version,)
        )
        if existing is not None:
            continue

        module = _load_migration_module(migration_file)
        upgrade_fn = getattr(module, "upgrade", None)
        if upgrade_fn is None:
            raise RuntimeError(f"Migration {migration_file.name} is missing async upgrade(conn) function")

        await upgrade_fn(conn)
        await conn.execute("INSERT INTO schema_migrations (version) VALUES (?)", (version,))
        await conn.commit()


def _load_migration_module(path: Path) -> ModuleType:
    module_name = f"foundry.storage.migrations.{path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load migration module from {path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
