from __future__ import annotations

from fastapi.testclient import TestClient

from foundry.main import app


def test_health_endpoint_returns_expected_shape(temp_data_dir) -> None:
    with TestClient(app) as client:
        response = client.get("/api/system/health")

    assert response.status_code == 200
    payload = response.json()

    expected_keys = {
        "status",
        "version",
        "uptime_seconds",
        "db",
        "workspace",
        "disk_free_gb",
        "agent_provider",
        "active_projects",
        "active_ingestions",
        "pending_reconcile_issues",
    }
    assert expected_keys.issubset(payload.keys())
    assert payload["db"] == "ok"
    assert payload["workspace"] == "ok"
