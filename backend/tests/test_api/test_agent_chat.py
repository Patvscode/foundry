"""Tests for agent chat API."""

from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from foundry.main import app


def _setup_subproject(client: TestClient, temp_data_dir: Path) -> tuple[str, str, str]:
    """Create project → resource → seed extraction → accept → return (project_id, resource_id, subproject_id)."""
    proj = client.post("/api/projects", json={"name": "Chat Test"}).json()
    pid = proj["id"]

    res = client.post(f"/api/projects/{pid}/resources", json={"url": "https://example.com/test"}).json()
    rid = res["id"]

    proposal_id = str(uuid.uuid4())
    db_path = temp_data_dir / "foundry.db"
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("UPDATE resources SET status='completed', pipeline_status='discovered' WHERE id=?", (rid,))
        proposals = [{
            "proposal_id": proposal_id,
            "suggested_name": "TestLib",
            "description": "A test library",
            "type": "library",
            "repos": ["https://github.com/test/repo"],
            "dependencies": ["numpy"],
            "setup_steps": ["pip install testlib"],
            "complexity": "low",
            "confidence": 0.8,
            "source_context": "Main topic",
            "is_synthetic": True,
            "decision": None, "decision_at": None, "subproject_id": None,
            "edited_name": None, "edited_description": None, "edited_type": None,
        }]
        conn.execute(
            "INSERT INTO extraction_results (id, resource_id, summary, discovered_projects, model_used, created_at) VALUES (?,?,?,?,?,datetime('now'))",
            (str(uuid.uuid4()), rid, "Test summary about TestLib", json.dumps(proposals), "fallback"),
        )
        conn.commit()
    finally:
        conn.close()

    sub = client.post(f"/api/resources/{rid}/proposals/{proposal_id}/accept").json()
    return pid, rid, sub["id"]


def test_agent_chat_with_project_context(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        proj = client.post("/api/projects", json={"name": "Chat Test"}).json()

        resp = client.post("/api/agent/chat", json={
            "message": "What is this project?",
            "project_id": proj["id"],
        })

    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"]
    assert data["message"]
    assert data["provider"] in ("ollama", "fallback")
    # Fallback should be labeled
    if data["is_synthetic"]:
        assert "⚠" in data["message"] or "No LLM" in data["message"]


def test_agent_chat_with_subproject_context(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        pid, rid, sid = _setup_subproject(client, temp_data_dir)

        resp = client.post("/api/agent/chat", json={
            "message": "What should I do next?",
            "project_id": pid,
            "subproject_id": sid,
        })

    assert resp.status_code == 200
    data = resp.json()
    assert data["message"]
    assert data["session_id"]


def test_agent_session_persistence(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        proj = client.post("/api/projects", json={"name": "Session Test"}).json()

        # First message creates session
        resp1 = client.post("/api/agent/chat", json={
            "message": "Hello",
            "project_id": proj["id"],
        })
        session_id = resp1.json()["session_id"]

        # Second message uses same session
        resp2 = client.post("/api/agent/chat", json={
            "message": "Tell me more",
            "session_id": session_id,
            "project_id": proj["id"],
        })
        assert resp2.json()["session_id"] == session_id

        # Session has history
        resp3 = client.get(f"/api/agent/sessions/{session_id}")
        assert resp3.status_code == 200
        messages = resp3.json()["messages"]
        assert len(messages) == 4  # user, assistant, user, assistant


def test_agent_action_creates_task(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        pid, rid, sid = _setup_subproject(client, temp_data_dir)

        resp = client.post("/api/agent/action", json={
            "subproject_id": sid,
            "action_type": "task",
            "title": "Agent-suggested task",
        })

    assert resp.status_code == 200
    assert resp.json()["title"] == "Agent-suggested task"
    assert resp.json()["source"] == "agent"


def test_agent_action_creates_note(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        pid, rid, sid = _setup_subproject(client, temp_data_dir)

        resp = client.post("/api/agent/action", json={
            "subproject_id": sid,
            "action_type": "note",
            "title": "Agent observation",
            "content": "This library looks promising.",
        })

    assert resp.status_code == 200
    assert resp.json()["title"] == "Agent observation"


def test_agent_chat_empty_message_rejected(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        resp = client.post("/api/agent/chat", json={"message": ""})
    assert resp.status_code == 422


def test_agent_session_not_found(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        resp = client.get("/api/agent/sessions/nonexistent")
    assert resp.status_code == 404
