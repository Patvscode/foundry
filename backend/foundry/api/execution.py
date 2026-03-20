"""Workspace-scoped execution API. Bounded, logged, path-restricted."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from foundry.config import FoundrySettings
from foundry.execution.runner import (
    ALLOWED_ACTIONS,
    ExecResult,
    detect_ecosystem,
    execute_in_workspace,
    get_execution_detail,
    get_execution_history,
    log_execution,
    resolve_action_command,
)
from foundry.storage.database import Database
from foundry.storage.queries import get_subproject

router = APIRouter(tags=["execution"])


class ExecRequest(BaseModel):
    action: str = Field(..., description="Action type: shell, install, test, build, run")
    command: str = Field("", description="Custom command (required for shell/run)")
    timeout: int = Field(60, ge=1, le=300, description="Timeout in seconds")


@router.post("/subprojects/{subproject_id}/exec")
async def execute_command(
    subproject_id: str,
    body: ExecRequest,
    request: Request,
) -> dict[str, Any]:
    """Execute a command in a subproject's workspace directory.

    Requires agent.can_execute=true in config.
    All executions are logged.
    """
    settings: FoundrySettings = request.app.state.settings
    db: Database = request.app.state.db

    # Permission check
    if not settings.agent.can_execute:
        raise HTTPException(
            status_code=403,
            detail="Execution is disabled. Set agent.can_execute=true in ~/.foundry/config.toml",
        )

    if body.action not in ALLOWED_ACTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown action: {body.action}. Allowed: {', '.join(sorted(ALLOWED_ACTIONS))}",
        )

    # Get subproject and validate workspace
    subproject = await get_subproject(db, subproject_id)
    if subproject is None:
        raise HTTPException(status_code=404, detail=f"Subproject {subproject_id} not found")

    workspace_path = Path(subproject["workspace_path"])
    if not workspace_path.exists() or not workspace_path.is_dir():
        raise HTTPException(
            status_code=400,
            detail=f"Workspace directory does not exist: {workspace_path}",
        )

    # Resolve command
    try:
        cmd = resolve_action_command(body.action, workspace_path, body.command)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Execute
    result: ExecResult = await execute_in_workspace(
        cmd, workspace_path, timeout=body.timeout,
    )

    # Log
    log_id = await log_execution(db, subproject_id, result, body.action)

    return {
        "id": log_id,
        "action": body.action,
        "command": result.command,
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "duration_ms": result.duration_ms,
        "timed_out": result.timed_out,
        "working_dir": result.working_dir,
        "ecosystem": detect_ecosystem(workspace_path),
    }


@router.get("/subprojects/{subproject_id}/exec/history")
async def exec_history(
    subproject_id: str,
    request: Request,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Get execution history for a subproject."""
    db: Database = request.app.state.db

    subproject = await get_subproject(db, subproject_id)
    if subproject is None:
        raise HTTPException(status_code=404, detail=f"Subproject {subproject_id} not found")

    return await get_execution_history(db, subproject_id, limit=limit)


@router.get("/subprojects/{subproject_id}/exec/{log_id}")
async def exec_detail(
    subproject_id: str,
    log_id: str,
    request: Request,
) -> dict[str, Any]:
    """Get full execution detail including stdout/stderr."""
    db: Database = request.app.state.db

    detail = await get_execution_detail(db, log_id)
    if detail is None or detail.get("subproject_id") != subproject_id:
        raise HTTPException(status_code=404, detail="Execution log not found")

    return detail


@router.get("/subprojects/{subproject_id}/ecosystem")
async def get_ecosystem(
    subproject_id: str,
    request: Request,
) -> dict[str, Any]:
    """Detect the ecosystem for a subproject workspace."""
    db: Database = request.app.state.db

    subproject = await get_subproject(db, subproject_id)
    if subproject is None:
        raise HTTPException(status_code=404, detail=f"Subproject {subproject_id} not found")

    workspace_path = Path(subproject["workspace_path"])
    if not workspace_path.exists():
        return {"ecosystem": "unknown", "workspace_exists": False}

    eco = detect_ecosystem(workspace_path)
    files = [f.name for f in workspace_path.iterdir() if not f.name.startswith(".")]

    return {
        "ecosystem": eco,
        "workspace_exists": True,
        "workspace_path": str(workspace_path),
        "files": sorted(files)[:50],
    }
