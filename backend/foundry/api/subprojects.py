"""Subproject API endpoints. Accept/reject proposals by proposal_id, edit proposals, list subprojects."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from foundry.storage.database import Database
from foundry.storage.queries import (
    get_project,
    get_proposal,
    get_resource,
    get_subproject,
    insert_provenance_link,
    insert_subproject,
    list_subprojects_for_project,
    new_id,
    update_proposal_decision,
    update_proposal_edits,
)
from foundry.workspace.manager import create_subproject_workspace

router = APIRouter(tags=["subprojects"])


class EditProposalRequest(BaseModel):
    edited_name: str | None = None
    edited_description: str | None = None
    edited_type: str | None = None


@router.post("/resources/{resource_id}/proposals/{proposal_id}/accept")
async def accept_proposal(
    resource_id: str,
    proposal_id: str,
    request: Request,
) -> JSONResponse:
    db: Database = request.app.state.db

    resource = await get_resource(db, resource_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")

    proposal = await get_proposal(db, resource_id, proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found")

    # Idempotent: if already accepted, return existing subproject with 200
    if proposal.get("decision") == "accepted" and proposal.get("subproject_id"):
        existing = await get_subproject(db, proposal["subproject_id"])
        if existing is not None:
            return JSONResponse(content=existing, status_code=200)

    project = await get_project(db, resource["project_id"])
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    # Use edited fields if they exist, otherwise use original proposal fields
    name = proposal.get("edited_name") or proposal.get("suggested_name", "Unnamed")
    description = proposal.get("edited_description") or proposal.get("description", "")
    subproject_type = proposal.get("edited_type") or proposal.get("type", "research")

    subproject_id = new_id()

    workspace_path = create_subproject_workspace(
        project_path=project["workspace_path"],
        subproject_id=subproject_id,
        name=name,
        description=description,
        dependencies=proposal.get("dependencies", []),
        setup_steps=proposal.get("setup_steps", []),
    )

    subproject = await insert_subproject(
        db,
        subproject_id=subproject_id,
        project_id=resource["project_id"],
        name=name,
        description=description,
        subproject_type=subproject_type,
        workspace_path=str(workspace_path),
        dependencies=proposal.get("dependencies"),
        setup_steps=proposal.get("setup_steps"),
        complexity=proposal.get("complexity", "medium"),
        sort_order=0,
    )

    await insert_provenance_link(
        db,
        resource_id=resource_id,
        target_type="subproject",
        target_id=subproject_id,
        context=proposal.get("source_context", ""),
        confidence=proposal.get("confidence", 1.0),
    )

    await update_proposal_decision(
        db, resource_id, proposal_id, "accepted", subproject_id=subproject_id
    )

    return JSONResponse(content=subproject, status_code=201)


@router.post("/resources/{resource_id}/proposals/{proposal_id}/reject")
async def reject_proposal(
    resource_id: str,
    proposal_id: str,
    request: Request,
) -> dict[str, Any]:
    db: Database = request.app.state.db

    proposal = await get_proposal(db, resource_id, proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found")

    # Cannot reject an accepted proposal
    if proposal.get("decision") == "accepted":
        raise HTTPException(
            status_code=409,
            detail="Cannot reject an accepted proposal — delete the subproject first.",
        )

    # Idempotent: rejecting an already rejected proposal is a no-op
    if proposal.get("decision") == "rejected":
        return {"status": "rejected", "proposal_id": proposal_id}

    updated = await update_proposal_decision(db, resource_id, proposal_id, "rejected")
    if updated is None:
        raise HTTPException(status_code=404, detail="Proposal not found")

    return {"status": "rejected", "proposal_id": proposal_id}


@router.put("/resources/{resource_id}/proposals/{proposal_id}")
async def edit_proposal(
    resource_id: str,
    proposal_id: str,
    body: EditProposalRequest,
    request: Request,
) -> dict[str, Any]:
    db: Database = request.app.state.db

    proposal = await get_proposal(db, resource_id, proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found")

    if proposal.get("decision") == "accepted":
        raise HTTPException(status_code=409, detail="Cannot edit an accepted proposal.")

    updated = await update_proposal_edits(
        db,
        resource_id,
        proposal_id,
        edited_name=body.edited_name,
        edited_description=body.edited_description,
        edited_type=body.edited_type,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Proposal not found")

    return updated


@router.get("/projects/{project_id}/subprojects")
async def list_subprojects(project_id: str, request: Request) -> list[dict[str, Any]]:
    db: Database = request.app.state.db

    project = await get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    return await list_subprojects_for_project(db, project_id)
