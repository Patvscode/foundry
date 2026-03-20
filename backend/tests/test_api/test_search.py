"""Tests for the search API."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from foundry.main import app


def test_search_returns_results(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        # Create a project to search for
        client.post("/api/projects", json={"name": "Machine Learning Pipeline"})
        client.post("/api/projects", json={"name": "Data Visualization Tool"})

        # Rebuild index
        resp = client.post("/api/search/rebuild")
        assert resp.status_code == 200
        assert resp.json()["indexed"] >= 2

        # Search
        resp = client.get("/api/search", params={"q": "machine"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert any("Machine" in r["title"] for r in data["results"])


def test_search_empty_query_rejected(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        resp = client.get("/api/search", params={"q": ""})
        assert resp.status_code == 422


def test_search_type_filter(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        client.post("/api/projects", json={"name": "Filter Test Project"})
        client.post("/api/search/rebuild")

        # Filter to projects only
        resp = client.get("/api/search", params={"q": "Filter", "types": "project"})
        assert resp.status_code == 200
        data = resp.json()
        for r in data["results"]:
            assert r["entity_type"] == "project"


def test_search_grouped_results(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        client.post("/api/projects", json={"name": "Grouped Test"})
        client.post("/api/search/rebuild")

        resp = client.get("/api/search", params={"q": "Grouped"})
        data = resp.json()
        assert "grouped" in data
