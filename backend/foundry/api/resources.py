"""Resource API endpoints. Add resources to projects, check pipeline status."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator

from foundry.storage.database import Database
from foundry.storage.queries import (
    get_extraction_result,
    get_project,
    get_resource,
    insert_job,
    insert_resource,
    list_resources_for_project,
    new_id,
)

router = APIRouter(tags=["resources"])


class AddResourceRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("URL is required")
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


@router.post("/projects/{project_id}/resources", status_code=201)
async def add_resource(project_id: str, body: AddResourceRequest, request: Request) -> dict[str, Any]:
    db: Database = request.app.state.db

    # Verify project exists
    project = await get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    # Create resource record
    resource_id = new_id()
    resource = await insert_resource(
        db,
        resource_id=resource_id,
        project_id=project_id,
        resource_type="webpage",  # MVP: only webpage handler
        url=body.url,
        title=body.url,  # Will be updated by handler during extraction
    )

    # Create a queued job for the ingestion pipeline
    job_id = new_id()
    await insert_job(
        db,
        job_id=job_id,
        job_type="ingestion",
        project_id=project_id,
        result=resource_id,  # Job runner reads this to know which resource to process
    )

    return resource


@router.get("/projects/{project_id}/resources")
async def list_resources(project_id: str, request: Request) -> list[dict[str, Any]]:
    db: Database = request.app.state.db

    project = await get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    return await list_resources_for_project(db, project_id)


@router.get("/resources/{resource_id}")
async def get_one(resource_id: str, request: Request) -> dict[str, Any]:
    db: Database = request.app.state.db

    resource = await get_resource(db, resource_id)
    if resource is None:
        raise HTTPException(status_code=404, detail=f"Resource {resource_id} not found")

    # Attach extraction result if available
    extraction = await get_extraction_result(db, resource_id)
    if extraction is not None:
        resource["extraction"] = extraction

    return resource
