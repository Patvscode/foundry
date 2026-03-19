from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict


class ProjectStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class SubprojectStatus(StrEnum):
    DISCOVERED = "discovered"
    PLANNED = "planned"
    ACTIVE = "active"
    DONE = "done"


class ResourcePipelineStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETE = "complete"
    ERROR = "error"


class TaskStatus(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"


class NoteSource(StrEnum):
    USER = "user"
    EXTRACTED = "extracted"
    AGENT = "agent"


class EnvironmentStatus(StrEnum):
    PLANNED = "planned"
    PROVISIONING = "provisioning"
    READY = "ready"
    ERROR = "error"


class AgentSessionMode(StrEnum):
    EXPLORE = "explore"
    BUILD = "build"


class AgentSessionStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class BaseEntity(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Project(BaseEntity):
    id: str
    name: str | None = None
    description: str | None = None
    status: ProjectStatus = ProjectStatus.ACTIVE
    workspace_path: str | None = None
    settings: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Subproject(BaseEntity):
    id: str
    project_id: str | None = None
    name: str | None = None
    description: str | None = None
    type: str | None = None
    status: SubprojectStatus = SubprojectStatus.DISCOVERED
    workspace_path: str | None = None
    dependencies: list[str] | dict[str, Any] | None = None
    setup_steps: list[str] | dict[str, Any] | None = None
    complexity: str | None = None
    sort_order: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Resource(BaseEntity):
    id: str
    project_id: str | None = None
    type: str | None = None
    url: str | None = None
    title: str | None = None
    original_filename: str | None = None
    mime_type: str | None = None
    metadata: dict[str, Any] | None = None
    content_hash: str | None = None
    raw_content_path: str | None = None
    pipeline_status: ResourcePipelineStatus = ResourcePipelineStatus.PENDING
    pipeline_error: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ExtractionResult(BaseEntity):
    id: str
    resource_id: str | None = None
    summary: str | None = None
    key_concepts: list[str] | dict[str, Any] | None = None
    entities: list[dict[str, Any]] | dict[str, Any] | None = None
    content_sections: list[dict[str, Any]] | dict[str, Any] | None = None
    discovered_projects: list[dict[str, Any]] | dict[str, Any] | None = None
    open_questions: list[str] | dict[str, Any] | None = None
    follow_up_suggestions: list[str] | dict[str, Any] | None = None
    model_used: str | None = None
    token_usage: dict[str, Any] | None = None
    raw_response: str | None = None
    created_at: datetime | None = None


class Task(BaseEntity):
    id: str
    subproject_id: str | None = None
    title: str | None = None
    description: str | None = None
    status: TaskStatus = TaskStatus.TODO
    priority: str | None = None
    source: str = "extracted"
    sort_order: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Note(BaseEntity):
    id: str
    project_id: str | None = None
    subproject_id: str | None = None
    title: str | None = None
    content: str | None = None
    source: NoteSource = NoteSource.USER
    created_at: datetime | None = None
    updated_at: datetime | None = None


class FileAsset(BaseEntity):
    id: str
    subproject_id: str | None = None
    path: str | None = None
    type: str | None = None
    description: str | None = None
    size_bytes: int | None = None
    created_at: datetime | None = None


class Environment(BaseEntity):
    id: str
    subproject_id: str | None = None
    type: str | None = None
    status: EnvironmentStatus = EnvironmentStatus.PLANNED
    config: dict[str, Any] | None = None
    path: str | None = None
    error: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AgentSession(BaseEntity):
    id: str
    project_id: str | None = None
    subproject_id: str | None = None
    provider: str | None = None
    model: str | None = None
    mode: AgentSessionMode = AgentSessionMode.EXPLORE
    status: AgentSessionStatus = AgentSessionStatus.ACTIVE
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AgentMessage(BaseEntity):
    id: str
    session_id: str | None = None
    role: str | None = None
    content: str | None = None
    tool_call: dict[str, Any] | None = None
    created_at: datetime | None = None


class ProvenanceLink(BaseEntity):
    id: str
    resource_id: str | None = None
    target_type: str | None = None
    target_id: str | None = None
    context: str | None = None
    quote: str | None = None
    confidence: float = 1.0
    created_at: datetime | None = None


class GitConfig(BaseEntity):
    id: str
    project_id: str | None = None
    remote_url: str | None = None
    branch: str = "main"
    auto_push: bool = False
    last_push_at: datetime | None = None
    status: str = "disconnected"


class Job(BaseEntity):
    id: str
    type: str | None = None
    project_id: str | None = None
    subproject_id: str | None = None
    status: JobStatus = JobStatus.QUEUED
    progress_pct: int = 0
    progress_steps: list[str] | dict[str, Any] | None = None
    pid: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    result: dict[str, Any] | None = None
    created_at: datetime | None = None


class SearchDocument(BaseEntity):
    entity_type: str
    entity_id: str
    project_id: str | None = None
    title: str | None = None
    content: str | None = None
