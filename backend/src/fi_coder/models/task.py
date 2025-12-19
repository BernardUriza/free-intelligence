from __future__ import annotations

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from typing import Any, Dict, List
from uuid import UUID, uuid4


class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
    TIMED_OUT = "timed_out"


class ExecutionFingerprint(BaseModel):
    qwen_code_version: str | None = None
    model_parameters: Dict[str, Any] = Field(default_factory=dict)
    workspace_commit: str | None = None
    workspace_dirty: bool = False
    touched_files: List[str] = Field(default_factory=list)
    operated_paths: List[str] = Field(default_factory=list)
    working_directory: str | None = None
    scope_restrictions: Dict[str, Any] = Field(default_factory=dict)
    python_version: str | None = None
    dependencies_fingerprint: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)


class Task(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    command: str | None = None
    status: TaskStatus = TaskStatus.QUEUED
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    exit_code: int | None = None
    error_message: str | None = None
    logs_path: str | None = None
    timeout_seconds: int | None = None
    execution_fingerprint: ExecutionFingerprint | None = None

# Rebuild model for forward references
Task.model_rebuild()