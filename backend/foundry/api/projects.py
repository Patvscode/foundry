"""Project CRUD API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator

from foundry.storage.database import Database
from foundry.storage.queries import get_project, insert_project, list_projects
from foundry.workspace.manager import create_project_workspace

router = APIRouter(prefix="/projects", tags=["projects"])

MAX_NAME_LENGTH = 200


class CreateProjectRequest(BaseModel):
    name: str
    description: str = ""

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Project name is required")
        if len(v) > MAX_NAME_LENGTH:
            raise ValueError(f"Project name must be {MAX_NAME_LENGTH} characters or less")
        return v


@router.post("", status_code=201)
async def create(body: CreateProjectRequest, request: Request) -> dict[str, Any]:
    db: Database = request.app.state.db
    settings = request.app.state.settings

    # Insert first to get the real project ID
    project = await insert_project(
        db,
        name=body.name,
        description=body.description,
    )

    # Create workspace using the real project ID
    workspace_path = create_project_workspace(
        project_id=project["id"],
        name=body.name,
        data_dir=settings.storage.data_dir,
    )

    # Update the workspace path in DB
    now_str = project["updated_at"]  # Same timestamp is fine for atomic create
    await db.execute(
        "UPDATE projects SET workspace_path = ?, updated_at = ? WHERE id = ?",
        (str(workspace_path), now_str, project["id"]),
    )
    await db.commit()
    project["workspace_path"] = str(workspace_path)

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
