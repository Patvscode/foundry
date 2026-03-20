"""End-to-end test covering the complete Foundry product loop.

Creates a project → adds a resource → seeds pipeline results (fallback LLM)
→ accepts a proposal → opens subproject → generates starter tasks → adds a note.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
from foundry.main import app


def test_complete_product_loop(temp_data_dir: Path) -> None:
    """Full vertical slice through Foundry's MVP product loop."""

    # ── Step 1: Create project ────────────────────────────────────────
    with TestClient(app) as client:
        resp = client.post("/api/projects", json={"name": "E2E Test Project"})
        assert resp.status_code == 201
        project = resp.json()
        project_id = project["id"]
        assert project["name"] == "E2E Test Project"
        assert Path(project["workspace_path"]).exists()

    # ── Step 2: Add resource ──────────────────────────────────────────
    with TestClient(app) as client:
        resp = client.post(
            f"/api/projects/{project_id}/resources",
            json={"url": "https://example.com/ml-article"},
        )
        assert resp.status_code == 201
        resource = resp.json()
        resource_id = resource["id"]
        assert resource["status"] == "pending"
        assert resource["pipeline_status"] == "pending"

    # ── Step 3: Run pipeline (mocked extraction, fallback LLM) ────────
    # Seed pipeline completion via synchronous sqlite3 (same pattern as subproject tests)
    # since we can't easily call async pipeline from sync TestClient context
    import sqlite3 as _sqlite3
    import uuid as _uuid

    mock_text = (
        "This article introduces NeuroForge, a neural architecture search framework. "
        "It also describes DataPipe, a streaming data pipeline library for ML training."
    )
    db_path = temp_data_dir / "foundry.db"
    conn = _sqlite3.connect(str(db_path))
    try:
        conn.execute(
            "UPDATE resources SET status='completed', pipeline_status='discovered', "
            "content_hash='e2e-hash', title='NeuroForge & DataPipe' WHERE id=?",
            (resource_id,),
        )
        proposal_id_val = str(_uuid.uuid4())
        proposals = [
            {
                "proposal_id": proposal_id_val,
                "suggested_name": "NeuroForge",
                "description": "A neural architecture search framework requiring PyTorch 2.1+",
                "type": "library",
                "repos": ["https://github.com/example/neuroforge"],
                "dependencies": ["pytorch>=2.1", "numpy"],
                "setup_steps": ["pip install neuroforge", "python -m neuroforge init"],
                "complexity": "high",
                "confidence": 0.9,
                "source_context": "Primary subject of the article",
                "is_synthetic": True,
                "decision": None, "decision_at": None, "subproject_id": None,
                "edited_name": None, "edited_description": None, "edited_type": None,
            },
        ]
        result_id = str(_uuid.uuid4())
        conn.execute(
            """INSERT INTO extraction_results
               (id, resource_id, summary, key_concepts, entities,
                discovered_projects, model_used, created_at)
               VALUES (?,?,?,?,?,?,?,datetime('now'))""",
            (
                result_id, resource_id,
                f"[Placeholder] Content begins: {mock_text[:200]}",
                json.dumps(["neural architecture search", "data pipelines"]),
                json.dumps({"repos": ["https://github.com/example/neuroforge"], "tools": ["PyTorch"]}),
                json.dumps(proposals),
                "fallback",
            ),
        )
        conn.commit()
    finally:
        conn.close()

    # ── Step 4: Verify pipeline completed ─────────────────────────────
    with TestClient(app) as client:
        resp = client.get(f"/api/resources/{resource_id}")
        assert resp.status_code == 200
        resource = resp.json()
        assert resource["status"] == "completed"
        assert resource["pipeline_status"] == "discovered"
        assert resource["extraction"] is not None
        assert resource["extraction"]["summary"]

        proposals = resource["extraction"]["discovered_projects"]
        assert len(proposals) >= 1
        assert proposals[0]["is_synthetic"] is True
        proposal_id = proposals[0]["proposal_id"]

    # ── Step 5: Accept proposal → creates subproject ──────────────────
    with TestClient(app) as client:
        resp = client.post(f"/api/resources/{resource_id}/proposals/{proposal_id}/accept")
        assert resp.status_code == 201
        subproject = resp.json()
        subproject_id = subproject["id"]
        assert subproject["status"] == "approved"
        assert Path(subproject["workspace_path"]).exists()

    # ── Step 6: Open subproject detail ────────────────────────────────
    with TestClient(app) as client:
        resp = client.get(f"/api/subprojects/{subproject_id}")
        assert resp.status_code == 200
        detail = resp.json()
        assert detail["workspace_exists"] is True
        assert len(detail["provenance"]) == 1
        assert detail["provenance"][0]["resource_id"] == resource_id

    # ── Step 7: Browse files ──────────────────────────────────────────
    with TestClient(app) as client:
        resp = client.get(f"/api/subprojects/{subproject_id}/files")
        assert resp.status_code == 200
        files = resp.json()
        assert files["workspace_exists"] is True
        assert any(e["name"] == "README.md" for e in files["entries"])

        # Read README
        resp = client.get(f"/api/subprojects/{subproject_id}/files/README.md")
        assert resp.status_code == 200
        assert len(resp.json()["content"]) > 0  # README has content

    # ── Step 8: Generate starter tasks ────────────────────────────────
    with TestClient(app) as client:
        resp = client.post(f"/api/subprojects/{subproject_id}/tasks/generate")
        assert resp.status_code == 201
        tasks = resp.json()
        assert len(tasks) >= 1
        assert all(t["source"] == "extracted" for t in tasks)

    # ── Step 9: Add a manual task ─────────────────────────────────────
    with TestClient(app) as client:
        resp = client.post(
            f"/api/subprojects/{subproject_id}/tasks",
            json={"title": "Review architecture docs"},
        )
        assert resp.status_code == 201
        assert resp.json()["source"] == "user"

    # ── Step 10: Add a note ───────────────────────────────────────────
    with TestClient(app) as client:
        resp = client.post(
            f"/api/subprojects/{subproject_id}/notes",
            json={"title": "First impressions", "content": "Looks promising, needs GPU testing."},
        )
        assert resp.status_code == 201

        # Verify note persisted
        resp = client.get(f"/api/subprojects/{subproject_id}/notes")
        assert len(resp.json()) == 1
        assert resp.json()[0]["title"] == "First impressions"

    # ── Step 11: Verify project shows subproject count ────────────────
    with TestClient(app) as client:
        resp = client.get(f"/api/projects/{project_id}")
        assert resp.json()["subproject_count"] >= 1

    # ── Step 12: Health check still healthy ───────────────────────────
    with TestClient(app) as client:
        resp = client.get("/api/system/health")
        assert resp.json()["status"] == "healthy"
