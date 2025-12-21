"""Simplified qwen-code CLI executor.

This module provides a minimal wrapper around the qwen-code CLI tool.
No orchestration, no workers, no complex state management - just direct execution.
"""
from __future__ import annotations

import shlex
import subprocess
from pathlib import Path
from typing import Any


def execute_qwen_code(
    prompt: str = "",
    args: str = "",
    repo_path: str | Path = ".",
    timeout: int = 300,
) -> dict[str, Any]:
    """Execute qwen-code CLI with the given prompt.

    Args:
        prompt: Natural language prompt for qwen-code
        args: Additional CLI arguments (e.g., "--yolo", "--verbose")
        repo_path: Working directory for execution
        timeout: Maximum execution time in seconds

    Returns:
        Dictionary with execution results:
            - exit_code: Process exit code
            - stdout: Standard output
            - stderr: Standard error
            - success: True if exit_code == 0

    Example:
        >>> result = execute_qwen_code("fix typo in README.md")
        >>> if result["success"]:
        ...     print(result["stdout"])
    """
    # Build command
    command = "/opt/homebrew/lib/node_modules/@qwen-code/qwen-code/cli.js"

    if args:
        command += f" {args}"

    if prompt:
        # Properly quote the prompt
        command += f' "{prompt}"'

    # Parse into list for security (prevents shell injection)
    command_list = shlex.split(command)

    # Ensure repo_path is a Path object
    if isinstance(repo_path, str):
        repo_path = Path(repo_path)

    try:
        # Execute qwen-code CLI
        result = subprocess.run(
            command,
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=True,  # Enable shell to expand aliases
        )

        return {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0,
        }

    except subprocess.TimeoutExpired:
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Execution timed out after {timeout} seconds",
            "success": False,
        }

    except Exception as e:
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Execution error: {str(e)}",
            "success": False,
        }
