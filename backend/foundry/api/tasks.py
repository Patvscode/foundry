"""Task API endpoints for subprojects."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator

from foundry.storage.database import Database
from foundry.storage.queries import (
    count_extracted_tasks,
    get_subproject,
    insert_task,
    list_tasks_for_subproject,
    new_id,
    update_task,
)

router = APIRouter(tags=["tasks"])


class CreateTaskRequest(BaseModel):
    title: str
    description: str = ""

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Task title is required")
        return v


class UpdateTaskRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None  # todo | done


@router.get("/subprojects/{subproject_id}/tasks")
async def list_tasks(subproject_id: str, request: Request) -> list[dict[str, Any]]:
    db: Database = request.app.state.db
    sub = await get_subproject(db, subproject_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="Subproject not found")
    return await list_tasks_for_subproject(db, subproject_id)


@router.post("/subprojects/{subproject_id}/tasks", status_code=201)
async def create_task(subproject_id: str, body: CreateTaskRequest, request: Request) -> dict[str, Any]:
    db: Database = request.app.state.db
    sub = await get_subproject(db, subproject_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="Subproject not found")

    task_id = new_id()
    return await insert_task(db, task_id, subproject_id, body.title, body.description, source="user")


@router.patch("/subprojects/{subproject_id}/tasks/{task_id}")
async def patch_task(subproject_id: str, task_id: str, body: UpdateTaskRequest, request: Request) -> dict[str, Any]:
    db: Database = request.app.state.db

    fields: dict[str, Any] = {}
    if body.title is not None:
        fields["title"] = body.title.strip()
    if body.description is not None:
        fields["description"] = body.description
    if body.status is not None:
        if body.status not in ("todo", "done"):
            raise HTTPException(status_code=422, detail="Status must be 'todo' or 'done'")
        fields["status"] = body.status

    updated = await update_task(db, task_id, **fields)
    if updated is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return updated


@router.post("/subprojects/{subproject_id}/tasks/generate", status_code=201)
async def generate_starter_tasks(subproject_id: str, request: Request) -> list[dict[str, Any]]:
    """Generate starter tasks from subproject setup_steps, dependencies, and repos.

    Idempotent: only generates if no extracted tasks exist yet.
    """
    db: Database = request.app.state.db
    sub = await get_subproject(db, subproject_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="Subproject not found")

    existing = await count_extracted_tasks(db, subproject_id)
    if existing > 0:
        return await list_tasks_for_subproject(db, subproject_id)

    created: list[dict[str, Any]] = []
    order = 0

    # Dependencies task
    deps = sub.get("dependencies", [])
    if deps:
        task = await insert_task(
            db, new_id(), subproject_id,
            title=f"Install dependencies: {', '.join(deps)}",
            description=f"Required packages: {', '.join(deps)}",
            source="extracted", sort_order=order,
        )
        created.append(task)
        order += 1

    # Setup steps as individual tasks
    steps = sub.get("setup_steps", [])
    for step in steps:
        task = await insert_task(
            db, new_id(), subproject_id,
            title=step,
            source="extracted", sort_order=order,
        )
        created.append(task)
        order += 1

    # Repo clone tasks from provenance
    from foundry.storage.queries import get_provenance_for_target
    provenance = await get_provenance_for_target(db, "subproject", subproject_id)
    for prov in provenance:
        if prov.get("resource_url"):
            task = await insert_task(
                db, new_id(), subproject_id,
                title=f"Review source: {prov['resource_url']}",
                description=f"Source context: {prov.get('context', '')}",
                source="extracted", sort_order=order,
            )
            created.append(task)
            order += 1

    if not created:
        task = await insert_task(
            db, new_id(), subproject_id,
            title="Review subproject and define next steps",
            source="extracted", sort_order=0,
        )
        created.append(task)

    return created
