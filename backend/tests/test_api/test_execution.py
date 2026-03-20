"""Tests for workspace-scoped execution API."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from foundry.main import app


def _create_subproject_with_workspace(client, tmp_path: Path) -> tuple[str, str, Path]:
    """Helper to create a project + subproject with a real workspace."""
    proj = client.post("/api/projects", json={"name": "Exec Test"}).json()
    pid = proj["id"]

    # Add resource + mock the pipeline to create extraction with proposals
    res = client.post(f"/api/projects/{pid}/resources", json={"url": "https://example.com/test"}).json()
    rid = res["id"]

    # Create a subproject directly via the accept flow is complex,
    # so we'll test the execution runner directly
    return pid, rid, tmp_path


class TestExecutionRunner:
    """Tests for the execution runner module."""

    @pytest.mark.asyncio
    async def test_execute_echo(self, tmp_path: Path) -> None:
        from foundry.execution.runner import execute_in_workspace
        result = await execute_in_workspace(
            ["echo", "hello world"],
            tmp_path,
            timeout=10,
        )
        assert result.exit_code == 0
        assert "hello world" in result.stdout
        assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_execute_timeout(self, tmp_path: Path) -> None:
        from foundry.execution.runner import execute_in_workspace
        result = await execute_in_workspace(
            ["sleep", "10"],
            tmp_path,
            timeout=1,
        )
        assert result.timed_out is True

    @pytest.mark.asyncio
    async def test_execute_nonexistent_command(self, tmp_path: Path) -> None:
        from foundry.execution.runner import execute_in_workspace
        result = await execute_in_workspace(
            ["nonexistent_command_12345"],
            tmp_path,
            timeout=5,
        )
        assert result.exit_code == 127

    @pytest.mark.asyncio
    async def test_execute_invalid_workspace(self) -> None:
        from foundry.execution.runner import execute_in_workspace
        with pytest.raises(ValueError, match="does not exist"):
            await execute_in_workspace(["echo", "hi"], Path("/nonexistent/path"))

    def test_detect_ecosystem_python(self, tmp_path: Path) -> None:
        from foundry.execution.runner import detect_ecosystem
        (tmp_path / "requirements.txt").write_text("flask\n")
        assert detect_ecosystem(tmp_path) == "python"

    def test_detect_ecosystem_node(self, tmp_path: Path) -> None:
        from foundry.execution.runner import detect_ecosystem
        (tmp_path / "package.json").write_text("{}\n")
        assert detect_ecosystem(tmp_path) == "node"

    def test_detect_ecosystem_unknown(self, tmp_path: Path) -> None:
        from foundry.execution.runner import detect_ecosystem
        assert detect_ecosystem(tmp_path) == "unknown"

    def test_resolve_shell_command(self, tmp_path: Path) -> None:
        from foundry.execution.runner import resolve_action_command
        cmd = resolve_action_command("shell", tmp_path, "ls -la")
        assert cmd == ["bash", "-c", "ls -la"]

    def test_resolve_install_python(self, tmp_path: Path) -> None:
        from foundry.execution.runner import resolve_action_command
        (tmp_path / "requirements.txt").write_text("flask\n")
        cmd = resolve_action_command("install", tmp_path)
        assert "pip" in cmd[0]

    def test_resolve_test_python(self, tmp_path: Path) -> None:
        from foundry.execution.runner import resolve_action_command
        (tmp_path / "pyproject.toml").write_text("[tool.pytest]\n")
        cmd = resolve_action_command("test", tmp_path)
        assert "pytest" in cmd


class TestExecutionAPI:
    """Tests for the execution HTTP endpoints."""

    def test_exec_disabled_by_default(self, temp_data_dir: Path) -> None:
        with TestClient(app) as client:
            resp = client.post(
                "/api/subprojects/fake-id/exec",
                json={"action": "shell", "command": "echo hi"},
            )
            # Should be 403 since can_execute defaults to false
            assert resp.status_code == 403
            assert "disabled" in resp.json()["detail"].lower()

    def test_ecosystem_endpoint(self, temp_data_dir: Path) -> None:
        with TestClient(app) as client:
            resp = client.get("/api/subprojects/fake-id/ecosystem")
            assert resp.status_code == 404
