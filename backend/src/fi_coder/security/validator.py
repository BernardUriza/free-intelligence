from __future__ import annotations

import os
import re
from typing import Any, Dict

from ..config.policies import SECURITY_POLICY, TASK_CATALOG


class SecurityValidator:
    def __init__(self):
        self.allowed_commands = SECURITY_POLICY["allowed_commands"]
        self.working_directory_whitelist = SECURITY_POLICY["working_directory_whitelist"]

    def validate_task_name(self, task_name: str) -> bool:
        """Check if task name is in allowlist."""
        return task_name in self.allowed_commands

    def validate_working_directory(self, cwd: str) -> bool:
        """Check if working directory is allowed."""
        return any(cwd.startswith(allowed) for allowed in self.working_directory_whitelist)

    def sanitize_environment(self, env: Dict[str, str]) -> Dict[str, str]:
        """Remove potentially dangerous environment variables."""
        sanitized = env.copy()
        dangerous_vars = ["LD_LIBRARY_PATH", "PYTHONPATH"]  # Keep PATH for commands
        for var in dangerous_vars:
            if var in sanitized:
                del sanitized[var]
        return sanitized

    def validate_parameters(self, task_name: str, parameters: Dict[str, Any]) -> None:
        """Validate task parameters against schema and security. Raises ValueError on failure."""
        # Schema validation
        schema = TASK_CATALOG[task_name]
        required = [k for k, v in schema.parameters_schema.items() if v.get("required")]
        for req in required:
            if req not in parameters:
                raise ValueError(f"Missing required parameter: {req}")
        
        # No shell injection
        for key, value in parameters.items():
            if isinstance(value, str):
                if ";" in value or "|" in value or "&" in value or "`" in value:
                    raise ValueError(f"Potentially dangerous characters in parameter {key}")
        
        # Scope validation
        self.validate_scope(parameters)

    def validate_scope(self, parameters: Dict[str, Any]) -> None:
        """Validate scope restrictions. Raises ValueError on failure."""
        from ..config.policies import REPO_ROOT_PATH, SCOPE_POLICY
        
        repo_root_path = parameters.get('repo_root_path')
        if not repo_root_path:
            raise ValueError("repo_root_path is required")
        
        # Allow absolute paths within repo root
        if SCOPE_POLICY["forbid_absolute_outside_repo"]:
            if repo_root_path.startswith('/') and not repo_root_path.startswith(REPO_ROOT_PATH):
                raise ValueError("Absolute path outside repo not allowed")
        
        # Check for path traversal
        if '..' in repo_root_path:
            raise ValueError("Path traversal detected")
        
        # Check forbidden directories (only for absolute paths outside repo)
        if repo_root_path.startswith('/') and not repo_root_path.startswith(REPO_ROOT_PATH):
            forbidden_dirs = SCOPE_POLICY.get("forbid_directories", [])
            if any(f"/{d}/" in repo_root_path or repo_root_path.endswith(f"/{d}") for d in forbidden_dirs):
                raise ValueError("Access to forbidden directory")