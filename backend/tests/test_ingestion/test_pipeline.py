"""Tests for the ingestion pipeline with the fallback provider."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from fastapi.testclient import TestClient
from foundry.main import app


def test_add_resource_to_project(temp_data_dir: Path) -> None:
    """POST resource creates resource record and queued job."""
    with TestClient(app) as client:
        # Create a project first
        proj = client.post("/api/projects", json={"name": "Test"}).json()
        project_id = proj["id"]

        # Add a resource
        resp = client.post(
            f"/api/projects/{project_id}/resources",
            json={"url": "https://example.com/article"},
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["project_id"] == project_id
    assert data["url"] == "https://example.com/article"
    assert data["pipeline_status"] == "pending"


def test_add_resource_invalid_url(temp_data_dir: Path) -> None:
    """Rejects non-HTTP URLs."""
    with TestClient(app) as client:
        proj = client.post("/api/projects", json={"name": "Test"}).json()
        resp = client.post(
            f"/api/projects/{proj['id']}/resources",
            json={"url": "not-a-url"},
        )
    assert resp.status_code == 422


def test_add_resource_to_nonexistent_project(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        resp = client.post(
            "/api/projects/fake-id/resources",
            json={"url": "https://example.com"},
        )
    assert resp.status_code == 404


def test_list_resources(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        proj = client.post("/api/projects", json={"name": "Test"}).json()
        pid = proj["id"]
        client.post(f"/api/projects/{pid}/resources", json={"url": "https://example.com/a"})
        client.post(f"/api/projects/{pid}/resources", json={"url": "https://example.com/b"})

        resp = client.get(f"/api/projects/{pid}/resources")

    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_get_resource_by_id(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        proj = client.post("/api/projects", json={"name": "Test"}).json()
        res = client.post(
            f"/api/projects/{proj['id']}/resources",
            json={"url": "https://example.com/page"},
        ).json()

        resp = client.get(f"/api/resources/{res['id']}")

    assert resp.status_code == 200
    assert resp.json()["url"] == "https://example.com/page"


@pytest.mark.asyncio
async def test_pipeline_runs_with_fallback_provider(temp_data_dir: Path) -> None:
    """Pipeline runs end-to-end with mock extraction and fallback LLM."""
    from foundry.config import get_settings
    from foundry.ingestion.pipeline import run_pipeline
    from foundry.storage.database import init_database
    from foundry.storage.queries import (
        get_extraction_result,
        get_resource,
        insert_project,
        insert_resource,
        new_id,
    )

    settings = get_settings()
    db = await init_database(temp_data_dir / "test.db")

    # Create project and resource
    project_id = new_id()
    await insert_project(db, project_id, "Test", str(temp_data_dir))
    resource_id = new_id()
    await insert_resource(db, resource_id, project_id, "webpage", "https://example.com/test")

    # Mock the webpage handler to avoid real HTTP
    from foundry.ingestion.handlers.base import ExtractedContent

    mock_content = ExtractedContent(
        text="This article describes a new machine learning framework called TestML. "
             "It includes a training pipeline, a dataset loader, and a web dashboard.",
        metadata={"url": "https://example.com/test", "title": "TestML Framework"},
        content_hash="abc123",
        raw_content_path=temp_data_dir / "cached.txt",
    )
    (temp_data_dir / "cached.txt").write_text(mock_content.text)

    with patch("foundry.ingestion.pipeline.dispatch", new_callable=AsyncMock) as mock_dispatch:
        mock_handler = AsyncMock()
        mock_handler.extract = AsyncMock(return_value=mock_content)
        mock_dispatch.return_value = ("webpage", mock_handler)

        await run_pipeline(resource_id, db, settings)

    # Check final state
    resource = await get_resource(db, resource_id)
    assert resource is not None
    assert resource["pipeline_status"] == "discovered"
    assert resource["pipeline_error"] is None
    assert resource["content_hash"] == "abc123"

    # Check extraction result exists with proposals
    extraction = await get_extraction_result(db, resource_id)
    assert extraction is not None
    assert extraction["summary"]  # Should have some content
    assert extraction["discovered_projects"] is not None
    proposals = extraction["discovered_projects"]
    assert len(proposals) >= 1
    # Fallback provider labels output as synthetic
    assert proposals[0]["is_synthetic"] is True

    await db.close()
