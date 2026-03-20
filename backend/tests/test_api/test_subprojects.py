"""Tests for proposal accept/reject/edit and subproject creation using stable proposal_id."""

from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from foundry.main import app


def _seed_discovered_resource(client: TestClient, temp_data_dir: Path) -> tuple[str, str, list[str]]:
    """Create project + resource + extraction result with two proposals.

    Returns (project_id, resource_id, [proposal_id_1, proposal_id_2]).
    """
    proj = client.post("/api/projects", json={"name": "Test Project"}).json()
    project_id = proj["id"]

    res = client.post(
        f"/api/projects/{project_id}/resources",
        json={"url": "https://example.com/article"},
    ).json()
    resource_id = res["id"]

    pid1 = str(uuid.uuid4())
    pid2 = str(uuid.uuid4())

    db_path = temp_data_dir / "foundry.db"
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            "UPDATE resources SET status = 'completed', pipeline_status = 'discovered' WHERE id = ?",
            (resource_id,),
        )
        result_id = str(uuid.uuid4())
        proposals = [
            {
                "proposal_id": pid1,
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
                "decision": None,
                "decision_at": None,
                "subproject_id": None,
                "edited_name": None,
                "edited_description": None,
                "edited_type": None,
            },
            {
                "proposal_id": pid2,
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
                "decision": None,
                "decision_at": None,
                "subproject_id": None,
                "edited_name": None,
                "edited_description": None,
                "edited_type": None,
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
                result_id, resource_id,
                "Test summary", json.dumps([]), json.dumps({}),
                json.dumps(proposals), "fallback",
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return project_id, resource_id, [pid1, pid2]


def test_accept_creates_subproject(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        project_id, resource_id, pids = _seed_discovered_resource(client, temp_data_dir)

        resp = client.post(f"/api/resources/{resource_id}/proposals/{pids[0]}/accept")

    assert resp.status_code == 201
    sub = resp.json()
    assert sub["status"] == "approved"
    assert sub["name"] == "TestML Framework"
    assert sub["project_id"] == project_id
    assert Path(sub["workspace_path"]).exists()
    assert (Path(sub["workspace_path"]) / "README.md").exists()


def test_reject_proposal(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        _pid, resource_id, pids = _seed_discovered_resource(client, temp_data_dir)

        resp = client.post(f"/api/resources/{resource_id}/proposals/{pids[0]}/reject")
        assert resp.status_code == 200

        res = client.get(f"/api/resources/{resource_id}").json()
        p = res["extraction"]["discovered_projects"][0]
        assert p["decision"] == "rejected"
        assert p["decision_at"] is not None


def test_edit_persists_before_accept(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        _pid, resource_id, pids = _seed_discovered_resource(client, temp_data_dir)

        # Edit
        resp = client.put(
            f"/api/resources/{resource_id}/proposals/{pids[0]}",
            json={"edited_name": "Custom Name", "edited_type": "tool"},
        )
        assert resp.status_code == 200
        assert resp.json()["edited_name"] == "Custom Name"

        # Re-fetch — edits persisted
        res = client.get(f"/api/resources/{resource_id}").json()
        p = res["extraction"]["discovered_projects"][0]
        assert p["edited_name"] == "Custom Name"
        assert p["edited_type"] == "tool"

        # Accept — uses edited fields
        resp = client.post(f"/api/resources/{resource_id}/proposals/{pids[0]}/accept")
        assert resp.status_code == 201
        assert resp.json()["name"] == "Custom Name"
        assert resp.json()["type"] == "tool"


def test_double_accept_idempotent(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        _pid, resource_id, pids = _seed_discovered_resource(client, temp_data_dir)

        resp1 = client.post(f"/api/resources/{resource_id}/proposals/{pids[0]}/accept")
        assert resp1.status_code == 201
        sub_id = resp1.json()["id"]

        resp2 = client.post(f"/api/resources/{resource_id}/proposals/{pids[0]}/accept")
        assert resp2.status_code == 200
        assert resp2.json()["id"] == sub_id  # Same subproject, not a duplicate


def test_reject_then_accept(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        _pid, resource_id, pids = _seed_discovered_resource(client, temp_data_dir)

        client.post(f"/api/resources/{resource_id}/proposals/{pids[0]}/reject")
        resp = client.post(f"/api/resources/{resource_id}/proposals/{pids[0]}/accept")

    assert resp.status_code == 201
    assert resp.json()["name"] == "TestML Framework"


def test_reject_after_accept_blocked(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        _pid, resource_id, pids = _seed_discovered_resource(client, temp_data_dir)

        client.post(f"/api/resources/{resource_id}/proposals/{pids[0]}/accept")
        resp = client.post(f"/api/resources/{resource_id}/proposals/{pids[0]}/reject")

    assert resp.status_code == 409


def test_edit_after_accept_blocked(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        _pid, resource_id, pids = _seed_discovered_resource(client, temp_data_dir)

        client.post(f"/api/resources/{resource_id}/proposals/{pids[0]}/accept")
        resp = client.put(
            f"/api/resources/{resource_id}/proposals/{pids[0]}",
            json={"edited_name": "Nope"},
        )

    assert resp.status_code == 409


def test_list_subprojects(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        project_id, resource_id, pids = _seed_discovered_resource(client, temp_data_dir)
        client.post(f"/api/resources/{resource_id}/proposals/{pids[0]}/accept")

        resp = client.get(f"/api/projects/{project_id}/subprojects")

    assert len(resp.json()) == 1
    assert resp.json()[0]["name"] == "TestML Framework"


def test_invalid_proposal_id(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        _pid, resource_id, _pids = _seed_discovered_resource(client, temp_data_dir)
        resp = client.post(f"/api/resources/{resource_id}/proposals/nonexistent-id/accept")

    assert resp.status_code == 404


def test_exactly_one_provenance_per_accept(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        _pid, resource_id, pids = _seed_discovered_resource(client, temp_data_dir)
        resp = client.post(f"/api/resources/{resource_id}/proposals/{pids[0]}/accept")
        subproject_id = resp.json()["id"]

    # Query provenance links directly
    db_path = temp_data_dir / "foundry.db"
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.execute(
            "SELECT * FROM provenance_links WHERE target_type = 'subproject' AND target_id = ?",
            (subproject_id,),
        )
        rows = cursor.fetchall()
    finally:
        conn.close()

    assert len(rows) == 1


def test_decision_survives_refresh(temp_data_dir: Path) -> None:
    with TestClient(app) as client:
        _pid, resource_id, pids = _seed_discovered_resource(client, temp_data_dir)
        client.post(f"/api/resources/{resource_id}/proposals/{pids[0]}/accept")
        client.post(f"/api/resources/{resource_id}/proposals/{pids[1]}/reject")

        res = client.get(f"/api/resources/{resource_id}").json()
        proposals = res["extraction"]["discovered_projects"]
        assert proposals[0]["decision"] == "accepted"
        assert proposals[0]["subproject_id"] is not None
        assert proposals[1]["decision"] == "rejected"


def test_backfill_legacy_proposals(temp_data_dir: Path) -> None:
    """Proposals missing proposal_id get one assigned on first access."""
    with TestClient(app) as client:
        proj = client.post("/api/projects", json={"name": "Legacy"}).json()
        res = client.post(
            f"/api/projects/{proj['id']}/resources",
            json={"url": "https://example.com/old"},
        ).json()

    # Insert a legacy proposal without proposal_id or decision fields
    db_path = temp_data_dir / "foundry.db"
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            "UPDATE resources SET status = 'completed', pipeline_status = 'discovered' WHERE id = ?",
            (res["id"],),
        )
        legacy_proposals = [{"suggested_name": "OldProject", "description": "No ID", "type": "tool",
                             "confidence": 0.5, "is_synthetic": True, "complexity": "low",
                             "repos": [], "dependencies": [], "setup_steps": [], "source_context": ""}]
        conn.execute(
            """INSERT INTO extraction_results (id, resource_id, summary, discovered_projects, model_used, created_at)
               VALUES (?, ?, 'test', ?, 'fallback', datetime('now'))""",
            (str(uuid.uuid4()), res["id"], json.dumps(legacy_proposals)),
        )
        conn.commit()
    finally:
        conn.close()

    # Access via API — should get backfilled proposal_id
    with TestClient(app) as client:
        r = client.get(f"/api/resources/{res['id']}").json()
        p = r["extraction"]["discovered_projects"][0]
        assert "proposal_id" in p
        assert p["proposal_id"]  # Not empty
        assert p["decision"] is None  # Backfilled default

        # Accept using the backfilled proposal_id
        resp = client.post(f"/api/resources/{res['id']}/proposals/{p['proposal_id']}/accept")
        assert resp.status_code == 201
