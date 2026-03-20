"""Tests for the provider discovery API."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from foundry.main import app


def test_providers_endpoint(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        resp = client.get("/api/system/providers")
        assert resp.status_code == 200
        data = resp.json()

        assert "providers" in data
        assert "active_provider" in data
        assert "recommended" in data
        assert "mode" in data
        assert "setup_hint" in data

        # Should always have at least the fallback provider
        provider_ids = [p["id"] for p in data["providers"]]
        assert "fallback" in provider_ids
        assert "ollama" in provider_ids


def test_providers_has_fallback_always_available(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        resp = client.get("/api/system/providers")
        data = resp.json()

        fallback = next(p for p in data["providers"] if p["id"] == "fallback")
        assert fallback["status"] == "always_available"
        assert fallback["configured"] is True
