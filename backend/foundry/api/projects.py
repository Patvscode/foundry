from __future__ import annotations

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("")
async def list_projects() -> list[dict[str, str]]:
    return []


@router.post("")
async def create_project() -> None:
    raise HTTPException(status_code=501, detail="Project creation is not implemented yet.")


@router.get("/{project_id}")
async def get_project(project_id: str) -> None:
    raise HTTPException(
        status_code=501,
        detail=f"Project retrieval is not implemented yet for id={project_id}.",
    )
