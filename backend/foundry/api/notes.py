"""Note API endpoints for subprojects."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator

from foundry.storage.database import Database
from foundry.storage.queries import (
    delete_note,
    get_subproject,
    insert_note,
    list_notes_for_subproject,
    new_id,
    update_note,
)

router = APIRouter(tags=["notes"])


class CreateNoteRequest(BaseModel):
    title: str
    content: str = ""

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Note title is required")
        return v


class UpdateNoteRequest(BaseModel):
    title: str | None = None
    content: str | None = None


@router.get("/subprojects/{subproject_id}/notes")
async def list_notes(subproject_id: str, request: Request) -> list[dict[str, Any]]:
    db: Database = request.app.state.db
    sub = await get_subproject(db, subproject_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="Subproject not found")
    return await list_notes_for_subproject(db, subproject_id)


@router.post("/subprojects/{subproject_id}/notes", status_code=201)
async def create_note(subproject_id: str, body: CreateNoteRequest, request: Request) -> dict[str, Any]:
    db: Database = request.app.state.db
    sub = await get_subproject(db, subproject_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="Subproject not found")

    note_id = new_id()
    return await insert_note(db, note_id, subproject_id, body.title, body.content)


@router.patch("/subprojects/{subproject_id}/notes/{note_id}")
async def patch_note(
    subproject_id: str, note_id: str, body: UpdateNoteRequest, request: Request
) -> dict[str, Any]:
    db: Database = request.app.state.db

    fields: dict[str, Any] = {}
    if body.title is not None:
        fields["title"] = body.title.strip()
    if body.content is not None:
        fields["content"] = body.content

    updated = await update_note(db, note_id, **fields)
    if updated is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return updated


@router.delete("/subprojects/{subproject_id}/notes/{note_id}")
async def remove_note(subproject_id: str, note_id: str, request: Request) -> dict[str, str]:
    db: Database = request.app.state.db
    deleted = await delete_note(db, note_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"status": "deleted", "note_id": note_id}
