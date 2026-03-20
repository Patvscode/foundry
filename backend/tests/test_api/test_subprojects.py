"""Tests for proposal accept/reject and subproject creation."""

from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from foundry.main import app


def _seed_discovered_resource(client: TestClient, temp_data_dir: Path) -> tuple[str, str]:
    """Create project + resource, then seed extraction result with proposals via raw SQL.

    We use synchronous sqlite3 to seed test data because the TestClient runs
    sync tests against an async app — we can't easily run async DB ops here.
    The aiosqlite connection uses WAL mode so concurrent reads work fine.
    """
    proj = client.post("/api/projects", json={"name": "Test Project"}).json()
    project_id = proj["id"]

    res = client.post(
        f"/api/projects/{project_id}/resources",
        json={"url": "https://example.com/article"},
    ).json()
    resource_id = res["id"]

    # Seed extraction result directly via synchronous sqlite3
    db_path = temp_data_dir / "foundry.db"
    conn = sqlite3.connect(str(db_path))
    try:
        # Update resource to discovered status
        conn.execute(
            "UPDATE resources SET status = 'completed', pipeline_status = 'discovered' WHERE id = ?",
            (resource_id,),
        )

        # Insert extraction result with two proposals
        result_id = str(uuid.uuid4())
        proposals = [
            {
                "suggested_name": "TestML Framework",
                "description": "A machine learning framework",
                "type": "library",
                "repos": ["https://github.com/example/testml"],
                "dependencies": ["pytorch", "numpy"],
                "setup_steps": ["pip install testml"],
                "complexity": "medium",
                "confidence": 0.85,
                "source_context": "Described in first section",
                "is_synthetic": True,
            },
            {
                "suggested_name": "VizPro Dashboard",
                "description": "A data visualization tool",
                "type": "tool",
                "repos": [],
                "dependencies": ["plotly"],
                "setup_steps": [],
                "complexity": "low",
                "confidence": 0.6,
                "source_context": "Mentioned briefly",
                "is_synthetic": True,
            },
        ]
        conn.execute(
            """
            INSERT INTO extraction_results
                (id, resource_id, summary, key_concepts, entities,
                 discovered_projects, model_used, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            (
                result_id,
                resource_id,
                "Test summary about TestML and VizPro",
                json.dumps(["machine learning", "visualization"]),
                json.dumps({"repos": [], "tools": []}),
                json.dumps(proposals),
                "fallback",
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return project_id, resource_id


def test_accept_proposal_creates_subproject(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        project_id, resource_id = _seed_discovered_resource(client, temp_data_dir)

        # Verify proposals exist
        res = client.get(f"/api/resources/{resource_id}").json()
        assert len(res["extraction"]["discovered_projects"]) == 2

        # Accept first proposal
        resp = client.post(f"/api/resources/{resource_id}/proposals/0/accept", json={})

    assert resp.status_code == 201
    subproject = resp.json()
    assert subproject["status"] == "approved"
    assert subproject["project_id"] == project_id
    assert subproject["name"] == "TestML Framework"

    # Workspace directory exists
    workspace = Path(subproject["workspace_path"])
    assert workspace.exists()
    assert (workspace / "README.md").exists()
    assert (workspace / ".foundry").is_dir()


def test_reject_proposal(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        _project_id, resource_id = _seed_discovered_resource(client, temp_data_dir)

        resp = client.post(f"/api/resources/{resource_id}/proposals/0/reject")
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"

        # Verify decision persisted
        res = client.get(f"/api/resources/{resource_id}").json()
        assert res["extraction"]["discovered_projects"][0]["decision"] == "rejected"


def test_accept_with_edits(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        _project_id, resource_id = _seed_discovered_resource(client, temp_data_dir)

        resp = client.post(
            f"/api/resources/{resource_id}/proposals/0/accept",
            json={"suggested_name": "Custom Name", "type": "tool"},
        )

    assert resp.status_code == 201
    subproject = resp.json()
    assert subproject["name"] == "Custom Name"
    assert subproject["type"] == "tool"


def test_double_accept_rejected(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        _project_id, resource_id = _seed_discovered_resource(client, temp_data_dir)
        client.post(f"/api/resources/{resource_id}/proposals/0/accept", json={})
        resp = client.post(f"/api/resources/{resource_id}/proposals/0/accept", json={})

    assert resp.status_code == 409


def test_list_subprojects(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        project_id, resource_id = _seed_discovered_resource(client, temp_data_dir)
        client.post(f"/api/resources/{resource_id}/proposals/0/accept", json={})

        resp = client.get(f"/api/projects/{project_id}/subprojects")

    assert resp.status_code == 200
    subprojects = resp.json()
    assert len(subprojects) == 1
    assert subprojects[0]["name"] == "TestML Framework"
    assert subprojects[0]["status"] == "approved"


def test_accept_both_proposals(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        project_id, resource_id = _seed_discovered_resource(client, temp_data_dir)
        client.post(f"/api/resources/{resource_id}/proposals/0/accept", json={})
        client.post(f"/api/resources/{resource_id}/proposals/1/accept", json={})

        resp = client.get(f"/api/projects/{project_id}/subprojects")

    assert len(resp.json()) == 2


def test_decision_survives_refresh(temp_data_dir: Path) -> None:
    """Decisions are persisted — re-fetching shows the same state."""
    with TestClient(app) as client:
        _project_id, resource_id = _seed_discovered_resource(client, temp_data_dir)
        client.post(f"/api/resources/{resource_id}/proposals/0/accept", json={})
        client.post(f"/api/resources/{resource_id}/proposals/1/reject")

        # Re-fetch — simulates page refresh
        res = client.get(f"/api/resources/{resource_id}").json()
        proposals = res["extraction"]["discovered_projects"]
        assert proposals[0]["decision"] == "accepted"
        assert proposals[1]["decision"] == "rejected"


def test_invalid_proposal_index(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        _project_id, resource_id = _seed_discovered_resource(client, temp_data_dir)
        resp = client.post(f"/api/resources/{resource_id}/proposals/99/accept", json={})

    assert resp.status_code == 404
