"""Common security and configuration policies for FI system."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class TaskSchema(BaseModel):
    """Schema for task configuration."""

    parameters_schema: dict[str, Any]


# Repository root path
REPO_ROOT_PATH = "/Users/bernardurizaorozco/Documents/free-intelligence"

# Task catalog for security validation
TASK_CATALOG = {
    "qwen-code": TaskSchema(
        parameters_schema={
            "repo_root_path": {"type": "string", "required": True},
            "args": {"type": "string", "required": True},
        }
    )
}

# Security policy
SECURITY_POLICY = {
    "allowed_commands": ["qwen-code"],
    "working_directory_whitelist": [REPO_ROOT_PATH],
    "environment_sanitization": True,
    "allowlist_executables": ["qwen-code"],
}

# Scope policy
SCOPE_POLICY = {
    "forbid_absolute_outside_repo": True,
    "forbid_directories": ["etc", "usr", "var", "root", "home"],
}
