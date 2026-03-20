"""File browsing API. Read file trees and content from subproject workspaces."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from foundry.storage.database import Database
from foundry.storage.queries import get_subproject

router = APIRouter(tags=["files"])

EXCLUDED_DIRS = {".git", "__pycache__", "node_modules", ".venv", ".env"}
MAX_ENTRIES = 200
MAX_DEPTH = 3
MAX_FILE_SIZE = 100 * 1024  # 100KB


def _scan_tree(root: Path, rel: Path, depth: int, entries: list[dict[str, Any]]) -> None:
    """Recursively scan a directory tree up to MAX_DEPTH / MAX_ENTRIES."""
    if depth > MAX_DEPTH or len(entries) >= MAX_ENTRIES:
        return

    try:
        items = sorted(root.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except PermissionError:
        return

    for item in items:
        if len(entries) >= MAX_ENTRIES:
            break
        if item.name in EXCLUDED_DIRS:
            continue

        relative = rel / item.name
        entry: dict[str, Any] = {
            "name": item.name,
            "path": str(relative),
            "is_dir": item.is_dir(),
        }

        if item.is_file():
            try:
                entry["size"] = item.stat().st_size
            except OSError:
                entry["size"] = 0

        entries.append(entry)

        if item.is_dir():
            _scan_tree(item, relative, depth + 1, entries)


@router.get("/subprojects/{subproject_id}/files")
async def list_files(subproject_id: str, request: Request) -> dict[str, Any]:
    db: Database = request.app.state.db

    subproject = await get_subproject(db, subproject_id)
    if subproject is None:
        raise HTTPException(status_code=404, detail="Subproject not found")

    workspace = Path(subproject.get("workspace_path", ""))
    if not workspace.exists():
        return {"workspace_exists": False, "entries": []}

    entries: list[dict[str, Any]] = []
    _scan_tree(workspace, Path(""), 0, entries)
    return {"workspace_exists": True, "entries": entries}


@router.get("/subprojects/{subproject_id}/files/{file_path:path}")
async def get_file_content(subproject_id: str, file_path: str, request: Request) -> dict[str, Any]:
    db: Database = request.app.state.db

    subproject = await get_subproject(db, subproject_id)
    if subproject is None:
        raise HTTPException(status_code=404, detail="Subproject not found")

    workspace = Path(subproject.get("workspace_path", ""))
    target = (workspace / file_path).resolve()

    # Path traversal check — must come before existence check for deterministic 403
    if not target.is_relative_to(workspace.resolve()):
        raise HTTPException(status_code=403, detail="Path outside workspace")

    if not target.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    if target.is_dir():
        raise HTTPException(status_code=400, detail="Path is a directory, not a file")

    size = target.stat().st_size
    if size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"File too large ({size} bytes, max {MAX_FILE_SIZE})")

    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=415, detail="File is not a text file")

    return {
        "path": file_path,
        "size": size,
        "content": content,
    }
