"""Project CRUD API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from foundry.storage.database import Database
from foundry.storage.queries import get_project, insert_project, list_projects
from foundry.workspace.manager import create_project_workspace

router = APIRouter(prefix="/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    name: str
    description: str = ""


@router.post("", status_code=201)
async def create(body: CreateProjectRequest, request: Request) -> dict[str, Any]:
    db: Database = request.app.state.db
    settings = request.app.state.settings

    # Create workspace on disk
    workspace_path = create_project_workspace(
        project_id="pending",  # Will be replaced
        name=body.name,
        data_dir=settings.storage.data_dir,
    )

    # Insert into DB
    project = await insert_project(
        db,
        name=body.name,
        description=body.description,
        workspace_path=str(workspace_path),
    )

    # Rename workspace dir to use the real project ID
    real_path = workspace_path.parent / project["id"]
    if workspace_path != real_path:
        workspace_path.rename(real_path)
        project["workspace_path"] = str(real_path)
        from foundry.storage.queries import update_project

        await update_project(db, project["id"], workspace_path=str(real_path))

    return project


@router.get("")
async def list_all(request: Request) -> list[dict[str, Any]]:
    db: Database = request.app.state.db
    return await list_projects(db)


@router.get("/{project_id}")
async def get_one(project_id: str, request: Request) -> dict[str, Any]:
    db: Database = request.app.state.db
    project = await get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    return project
