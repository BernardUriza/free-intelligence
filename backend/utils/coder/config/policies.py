"""Simplified qwen-code policies - core configuration only.

After aggressive refactor, fi_coder is just a qwen-code CLI wrapper.
Removed 38 unused task schemas and unnecessary policy definitions.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

# Required parameters
REPO_ROOT_PATH = "/Users/bernardurizaorozco/Documents/free-intelligence"
FI_CODER_PATH = "/Users/bernardurizaorozco/Documents/free-intelligence/backend/src/fi_coder"
QWEN_CODE_BINARY = "qwen-code"


class TaskSchema(BaseModel):
    """Schema for qwen-code task configuration."""

    name: str
    description: str
    purpose: str
    parameters_schema: dict[str, Any]
    scope_rules: dict[str, Any] | None = None


# Rebuild for forward references
TaskSchema.model_rebuild()

# Simplified task catalog - only qwen-code
TASK_CATALOG: dict[str, TaskSchema] = {
    "qwen-code": TaskSchema(
        name="qwen-code",
        description="Run qwen-code with custom args",
        purpose="General AI-assisted development",
        parameters_schema={
            "repo_root_path": {"type": "string", "required": True},
            "args": {"type": "string", "required": True},
        },
        scope_rules={"allow_custom_args": False},  # No custom args for security
    ),
}

# Execution policy
EXECUTION_POLICY = {
    "default_timeout_seconds": 300,  # 5 minutes
    "retry_attempts": 0,  # No retries by default
}

# Logging policy
LOGGING_POLICY = {
    "redact_patterns": [
        r"\b\d{4}-\d{4}-\d{4}-\d{4}\b",  # Credit card numbers
        r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
        r"\+\d{1,3}\s?\d{1,4}\s?\d{1,4}\s?\d{1,4}",  # Phone numbers
    ],
}

# Security policy
SECURITY_POLICY = {
    "allowed_commands": list(TASK_CATALOG.keys()),
    "working_directory_whitelist": [REPO_ROOT_PATH],
    "environment_sanitization": True,
    "allowlist_executables": ["qwen-code"],
}
