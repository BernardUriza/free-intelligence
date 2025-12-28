"""Simplified qwen-code API router.

Provides minimal HTTP endpoints for qwen-code execution.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..execution.executor import execute_qwen_code

router = APIRouter()


class QwenCodeRequest(BaseModel):
    """Request model for qwen-code execution."""

    prompt: str = Field("", description="Natural language prompt for qwen-code")
    args: str = Field("", description="Additional CLI arguments")
    repo_path: str = Field(".", description="Working directory path")
    timeout: int = Field(300, description="Maximum execution time in seconds")


class QwenCodeResponse(BaseModel):
    """Response model for qwen-code execution."""

    exit_code: int
    stdout: str
    stderr: str
    success: bool


@router.post("/execute", response_model=QwenCodeResponse)
async def execute(request: QwenCodeRequest) -> QwenCodeResponse:
    """Execute qwen-code with the given prompt.

    Example:
        curl -X POST http://localhost:7001/api/coder/execute \\
             -H "Content-Type: application/json" \\
             -d '{"prompt": "fix typo in README.md"}'
    """
    result = execute_qwen_code(
        prompt=request.prompt,
        args=request.args,
        repo_path=request.repo_path,
        timeout=request.timeout,
    )

    return QwenCodeResponse(**result)


@router.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "service": "fi_coder"}
