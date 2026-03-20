"""Agent chat API. Context-aware conversation with LLM provider."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator

from foundry.agents.actions import execute_action, extract_suggestions
from foundry.agents.context import build_context, build_fallback_response
from foundry.agents.provider_factory import get_llm_provider
from foundry.storage.database import Database
from foundry.storage.queries import (
    get_agent_session,
    insert_agent_message,
    insert_agent_session,
    list_agent_messages,
    new_id,
)

router = APIRouter(prefix="/agent", tags=["agent"])


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    project_id: str | None = None
    resource_id: str | None = None
    subproject_id: str | None = None

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Message is required")
        return v


class ActionRequest(BaseModel):
    subproject_id: str
    action_type: str  # task | note
    title: str
    description: str = ""
    content: str = ""


@router.post("/chat")
async def chat(body: ChatRequest, request: Request) -> dict[str, Any]:
    db: Database = request.app.state.db
    settings = request.app.state.settings

    # Get or create session
    session_id = body.session_id
    if session_id:
        session = await get_agent_session(db, session_id)
        if session is None:
            session_id = None  # Session not found, create new

    if not session_id:
        session_id = new_id()
        provider = await get_llm_provider(settings)
        await insert_agent_session(
            db, session_id,
            project_id=body.project_id,
            subproject_id=body.subproject_id,
            provider=provider.name,
        )

    # Store user message
    await insert_agent_message(db, new_id(), session_id, "user", body.message)

    # Build context
    context = await build_context(
        db,
        project_id=body.project_id,
        resource_id=body.resource_id,
        subproject_id=body.subproject_id,
    )

    # Get provider and generate response
    provider = await get_llm_provider(settings)

    if provider.name == "fallback":
        response_text = await build_fallback_response(
            db,
            subproject_id=body.subproject_id,
            resource_id=body.resource_id,
        )
        is_synthetic = True
    else:
        full_prompt = f"{context}\n\nUser: {body.message}\n\nAssistant:"
        response_text = await provider.analyze("", full_prompt)
        is_synthetic = False

    # Store assistant message
    await insert_agent_message(db, new_id(), session_id, "assistant", response_text)

    # Extract any actionable suggestions
    suggestions = extract_suggestions(response_text)

    return {
        "session_id": session_id,
        "message": response_text,
        "is_synthetic": is_synthetic,
        "provider": provider.name,
        "suggestions": suggestions,
    }


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, request: Request) -> dict[str, Any]:
    db: Database = request.app.state.db

    session = await get_agent_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = await list_agent_messages(db, session_id)
    session["messages"] = messages
    return session


@router.post("/action")
async def execute_suggested_action(body: ActionRequest, request: Request) -> dict[str, Any]:
    """Execute a user-approved action suggested by the agent."""
    db: Database = request.app.state.db

    result = await execute_action(db, body.subproject_id, {
        "type": body.action_type,
        "title": body.title,
        "description": body.description,
        "content": body.content,
    })

    if result is None:
        raise HTTPException(status_code=400, detail="Could not execute action")

    return result
