"""Subproject API endpoints. Accept/reject proposals, list subprojects."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from foundry.storage.database import Database
from foundry.storage.queries import (
    get_extraction_result,
    get_project,
    get_resource,
    insert_provenance_link,
    insert_subproject,
    list_subprojects_for_project,
    new_id,
    update_proposal_decision,
)
from foundry.workspace.manager import create_subproject_workspace

router = APIRouter(tags=["subprojects"])


class ProposalDecisionRequest(BaseModel):
    """Optionally include edited fields when accepting."""
    suggested_name: str | None = None
    description: str | None = None
    type: str | None = None


@router.post("/resources/{resource_id}/proposals/{proposal_index}/accept", status_code=201)
async def accept_proposal(
    resource_id: str,
    proposal_index: int,
    body: ProposalDecisionRequest,
    request: Request,
) -> dict[str, Any]:
    db: Database = request.app.state.db

    # Get resource and extraction result
    resource = await get_resource(db, resource_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")

    extraction = await get_extraction_result(db, resource_id)
    if extraction is None:
        raise HTTPException(status_code=404, detail="No extraction result for this resource")

    proposals = extraction.get("discovered_projects", [])
    if not isinstance(proposals, list) or proposal_index >= len(proposals):
        raise HTTPException(status_code=404, detail=f"Proposal index {proposal_index} not found")

    proposal = proposals[proposal_index]
    if proposal.get("decision") == "accepted":
        raise HTTPException(status_code=409, detail="Proposal already accepted")

    # Get the project for workspace path
    project = await get_project(db, resource["project_id"])
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    # Apply edits if provided
    name = body.suggested_name or proposal.get("suggested_name", "Unnamed")
    description = body.description or proposal.get("description", "")
    subproject_type = body.type or proposal.get("type", "research")

    # Build edited fields dict for persisting edits to the proposal
    edited_fields: dict[str, Any] = {}
    if body.suggested_name:
        edited_fields["suggested_name"] = body.suggested_name
    if body.description:
        edited_fields["description"] = body.description
    if body.type:
        edited_fields["type"] = body.type

    # Create subproject
    subproject_id = new_id()

    # Create workspace directory
    workspace_path = create_subproject_workspace(
        project_path=project["workspace_path"],
        subproject_id=subproject_id,
        name=name,
        description=description,
        dependencies=proposal.get("dependencies", []),
        setup_steps=proposal.get("setup_steps", []),
    )

    # Insert subproject into DB
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
        sort_order=proposal_index,
    )

    # Create provenance link
    await insert_provenance_link(
        db,
        resource_id=resource_id,
        target_type="subproject",
        target_id=subproject_id,
        context=proposal.get("source_context", ""),
        confidence=proposal.get("confidence", 1.0),
    )

    # Mark proposal as accepted in the extraction result
    await update_proposal_decision(db, resource_id, proposal_index, "accepted", edited_fields)

    return subproject


@router.post("/resources/{resource_id}/proposals/{proposal_index}/reject")
async def reject_proposal(
    resource_id: str,
    proposal_index: int,
    request: Request,
) -> dict[str, str]:
    db: Database = request.app.state.db

    success = await update_proposal_decision(db, resource_id, proposal_index, "rejected")
    if not success:
        raise HTTPException(status_code=404, detail="Proposal not found")

    return {"status": "rejected", "proposal_index": str(proposal_index)}


@router.get("/projects/{project_id}/subprojects")
async def list_subprojects(project_id: str, request: Request) -> list[dict[str, Any]]:
    db: Database = request.app.state.db

    project = await get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    return await list_subprojects_for_project(db, project_id)
