"""Tests for project CRUD endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from foundry.main import app


def test_create_project(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        resp = client.post("/api/projects", json={"name": "Test Project"})

    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Project"
    assert data["status"] == "active"
    assert data["id"]

    # Workspace directory should exist
    workspace = Path(data["workspace_path"])
    assert workspace.exists()
    assert (workspace / ".foundry").is_dir()
    assert (workspace / "README.md").exists()


def test_create_project_trims_whitespace(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        resp = client.post("/api/projects", json={"name": "  Padded Name  "})

    assert resp.status_code == 201
    assert resp.json()["name"] == "Padded Name"


def test_create_project_empty_name_rejected(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        resp = client.post("/api/projects", json={"name": ""})

    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert any("required" in str(e).lower() for e in detail)


def test_create_project_whitespace_only_name_rejected(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        resp = client.post("/api/projects", json={"name": "   "})

    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert any("required" in str(e).lower() for e in detail)


def test_create_project_name_too_long_rejected(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        resp = client.post("/api/projects", json={"name": "x" * 201})

    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert any("200" in str(e) for e in detail)


def test_list_projects(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        client.post("/api/projects", json={"name": "Project A"})
        client.post("/api/projects", json={"name": "Project B"})
        resp = client.get("/api/projects")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    names = {p["name"] for p in data}
    assert names == {"Project A", "Project B"}


def test_get_project_by_id(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        create_resp = client.post(
            "/api/projects", json={"name": "My Project", "description": "A test"}
        )
        project_id = create_resp.json()["id"]

        resp = client.get(f"/api/projects/{project_id}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "My Project"
    assert data["description"] == "A test"


def test_get_nonexistent_project(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        resp = client.get("/api/projects/nonexistent-id")

    assert resp.status_code == 404
