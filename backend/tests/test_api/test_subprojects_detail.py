"""Tests for subproject detail view, file tree, and file content."""

from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from foundry.main import app


def _create_subproject(client: TestClient, temp_data_dir: Path) -> tuple[str, str, str]:
    """Create project → resource → extraction → accept proposal. Returns (project_id, resource_id, subproject_id)."""
    proj = client.post("/api/projects", json={"name": "Test"}).json()
    project_id = proj["id"]

    res = client.post(f"/api/projects/{project_id}/resources", json={"url": "https://example.com/page"}).json()
    resource_id = res["id"]

    pid = str(uuid.uuid4())
    db_path = temp_data_dir / "foundry.db"
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("UPDATE resources SET status='completed', pipeline_status='discovered' WHERE id=?", (resource_id,))
        proposals = [{
            "proposal_id": pid,
            "suggested_name": "TestProject",
            "description": "A test project with deps",
            "type": "library",
            "repos": ["https://github.com/test/repo"],
            "dependencies": ["pytorch", "numpy"],
            "setup_steps": ["pip install test-project", "python setup.py"],
            "complexity": "medium",
            "confidence": 0.85,
            "source_context": "Described in section 2",
            "is_synthetic": True,
            "decision": None, "decision_at": None, "subproject_id": None,
            "edited_name": None, "edited_description": None, "edited_type": None,
        }]
        conn.execute(
            "INSERT INTO extraction_results (id, resource_id, summary, discovered_projects, model_used, created_at) VALUES (?,?,?,?,?,datetime('now'))",
            (str(uuid.uuid4()), resource_id, "test", json.dumps(proposals), "fallback"),
        )
        conn.commit()
    finally:
        conn.close()

    resp = client.post(f"/api/resources/{resource_id}/proposals/{pid}/accept")
    assert resp.status_code == 201
    subproject_id = resp.json()["id"]
    return project_id, resource_id, subproject_id


def test_get_subproject_detail(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        _pid, resource_id, sub_id = _create_subproject(client, temp_data_dir)

        resp = client.get(f"/api/subprojects/{sub_id}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "TestProject"
    assert data["workspace_exists"] is True
    assert len(data["provenance"]) == 1
    assert data["provenance"][0]["resource_id"] == resource_id
    assert data["provenance"][0]["confidence"] == 0.85
    assert data["provenance"][0]["context"] == "Described in section 2"


def test_subproject_file_tree(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        _pid, _rid, sub_id = _create_subproject(client, temp_data_dir)

        resp = client.get(f"/api/subprojects/{sub_id}/files")

    assert resp.status_code == 200
    data = resp.json()
    assert data["workspace_exists"] is True
    names = {e["name"] for e in data["entries"]}
    assert "README.md" in names
    assert ".foundry" in names


def test_subproject_file_content(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        _pid, _rid, sub_id = _create_subproject(client, temp_data_dir)

        resp = client.get(f"/api/subprojects/{sub_id}/files/README.md")

    assert resp.status_code == 200
    data = resp.json()
    assert "TestProject" in data["content"]
    assert data["size"] > 0


def test_file_content_path_traversal_blocked(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        _pid, _rid, sub_id = _create_subproject(client, temp_data_dir)

        # Use a traversal that stays within the URL path structure
        resp = client.get(f"/api/subprojects/{sub_id}/files/.foundry/../../../../../../etc/passwd")

    assert resp.status_code in (403, 404)  # 403 if path check catches it, 404 if file doesn't exist after resolve


def test_nonexistent_subproject(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        resp = client.get("/api/subprojects/fake-id")
    assert resp.status_code == 404


def test_nonexistent_file(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        _pid, _rid, sub_id = _create_subproject(client, temp_data_dir)
        resp = client.get(f"/api/subprojects/{sub_id}/files/nope.txt")
    assert resp.status_code == 404


def test_provenance_has_resource_info(temp_data_dir: Path) -> None:
    """Provenance links include the source resource URL and title."""
    with TestClient(app) as client:
        _pid, resource_id, sub_id = _create_subproject(client, temp_data_dir)
        resp = client.get(f"/api/subprojects/{sub_id}")

    prov = resp.json()["provenance"][0]
    assert prov["resource_url"] == "https://example.com/page"
