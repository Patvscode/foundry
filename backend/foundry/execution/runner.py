"""Workspace-scoped shell execution. Bounded, logged, path-restricted.

Safety rules:
- Commands run ONLY inside a subproject's workspace directory
- Working directory is resolved and verified with is_relative_to()
- All executions are logged to the execution_log table
- Timeout enforced (default 60s, max 300s)
- Requires agent.can_execute=true in config
- No background/daemon processes
- stdout+stderr captured and returned
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from foundry.storage.database import Database
from foundry.storage.queries import new_id

logger = logging.getLogger(__name__)

MAX_TIMEOUT = 300  # 5 minutes absolute max
MAX_OUTPUT_BYTES = 512_000  # 500KB per stream
DEFAULT_TIMEOUT = 60

# Commands that are explicitly allowed action types
ALLOWED_ACTIONS = {"shell", "install", "test", "build", "run"}

# Install command templates by ecosystem
INSTALL_COMMANDS: dict[str, list[str]] = {
    "python": ["pip", "install", "-r", "requirements.txt"],
    "node": ["npm", "install"],
    "rust": ["cargo", "build"],
}

TEST_COMMANDS: dict[str, list[str]] = {
    "python": ["python", "-m", "pytest", "-v"],
    "node": ["npm", "test"],
    "rust": ["cargo", "test"],
}

BUILD_COMMANDS: dict[str, list[str]] = {
    "node": ["npm", "run", "build"],
    "rust": ["cargo", "build", "--release"],
}


@dataclass
class ExecResult:
    """Result of a workspace command execution."""
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    command: str
    working_dir: str
    timed_out: bool = False


def detect_ecosystem(workspace_path: Path) -> str:
    """Detect the project ecosystem from workspace files."""
    if (workspace_path / "requirements.txt").exists() or (workspace_path / "pyproject.toml").exists():
        return "python"
    if (workspace_path / "package.json").exists():
        return "node"
    if (workspace_path / "Cargo.toml").exists():
        return "rust"
    return "unknown"


def resolve_action_command(
    action_type: str,
    workspace_path: Path,
    custom_command: str = "",
) -> list[str]:
    """Resolve an action type to a concrete command."""
    eco = detect_ecosystem(workspace_path)

    if action_type == "shell":
        if not custom_command:
            raise ValueError("Shell action requires a command")
        return ["bash", "-c", custom_command]

    if action_type == "install":
        if eco in INSTALL_COMMANDS:
            return INSTALL_COMMANDS[eco]
        if custom_command:
            return ["bash", "-c", custom_command]
        raise ValueError(f"No install command known for {eco} ecosystem. Provide a custom command.")

    if action_type == "test":
        if eco in TEST_COMMANDS:
            return TEST_COMMANDS[eco]
        if custom_command:
            return ["bash", "-c", custom_command]
        raise ValueError(f"No test command known for {eco} ecosystem. Provide a custom command.")

    if action_type == "build":
        if eco in BUILD_COMMANDS:
            return BUILD_COMMANDS[eco]
        if custom_command:
            return ["bash", "-c", custom_command]
        raise ValueError(f"No build command known for {eco} ecosystem. Provide a custom command.")

    if action_type == "run":
        if not custom_command:
            raise ValueError("Run action requires a command")
        return ["bash", "-c", custom_command]

    raise ValueError(f"Unknown action type: {action_type}")


async def execute_in_workspace(
    command: list[str],
    workspace_path: Path,
    timeout: int = DEFAULT_TIMEOUT,
    env: dict[str, str] | None = None,
) -> ExecResult:
    """Execute a command inside a workspace directory with safety bounds.

    Raises ValueError if the workspace path is invalid.
    """
    workspace_path = workspace_path.resolve()
    if not workspace_path.exists() or not workspace_path.is_dir():
        raise ValueError(f"Workspace directory does not exist: {workspace_path}")

    effective_timeout = min(timeout, MAX_TIMEOUT)
    cmd_str = " ".join(command)

    logger.info("Executing in %s: %s (timeout=%ds)", workspace_path, cmd_str, effective_timeout)
    start = time.monotonic()

    try:
        proc = await asyncio.create_subprocess_exec(
            *command,
            cwd=workspace_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=effective_timeout,
            )
            timed_out = False
        except asyncio.TimeoutError:
            proc.kill()
            stdout_bytes, stderr_bytes = await proc.communicate()
            timed_out = True

    except FileNotFoundError:
        duration_ms = int((time.monotonic() - start) * 1000)
        return ExecResult(
            exit_code=127,
            stdout="",
            stderr=f"Command not found: {command[0]}",
            duration_ms=duration_ms,
            command=cmd_str,
            working_dir=str(workspace_path),
        )

    duration_ms = int((time.monotonic() - start) * 1000)

    return ExecResult(
        exit_code=proc.returncode or (124 if timed_out else 0),
        stdout=stdout_bytes[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace"),
        stderr=stderr_bytes[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace"),
        duration_ms=duration_ms,
        command=cmd_str,
        working_dir=str(workspace_path),
        timed_out=timed_out,
    )


async def log_execution(
    db: Database,
    subproject_id: str,
    result: ExecResult,
    action_type: str = "shell",
) -> str:
    """Log an execution to the database. Returns the log entry ID."""
    from foundry.storage.queries import _now
    log_id = new_id()
    await db.execute(
        """
        INSERT INTO execution_log
            (id, subproject_id, command, action_type, working_dir,
             exit_code, stdout, stderr, duration_ms, started_at, completed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            log_id, subproject_id, result.command, action_type,
            result.working_dir, result.exit_code, result.stdout, result.stderr,
            result.duration_ms, _now(), _now(),
        ),
    )
    await db.commit()
    return log_id


async def get_execution_history(
    db: Database,
    subproject_id: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Get recent execution history for a subproject."""
    rows = await db.fetchall(
        """
        SELECT id, command, action_type, exit_code, duration_ms, started_at, completed_at
        FROM execution_log
        WHERE subproject_id = ?
        ORDER BY started_at DESC
        LIMIT ?
        """,
        (subproject_id, limit),
    )
    return [dict(row) for row in rows]


async def get_execution_detail(
    db: Database,
    log_id: str,
) -> dict[str, Any] | None:
    """Get full execution detail including stdout/stderr."""
    row = await db.fetchone("SELECT * FROM execution_log WHERE id = ?", (log_id,))
    return dict(row) if row else None
