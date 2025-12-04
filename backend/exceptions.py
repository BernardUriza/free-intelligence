"""Free Intelligence - Standard Exception Hierarchy

Centralized exception definitions for consistent error handling across the system.

Philosophy:
  - Domain-specific exceptions (not generic Exception)
  - Preserve exception chains (raise ... from e)
  - Include context (session_id, resource_id, etc.)
  - Map to HTTP status codes for API layer

Architecture:
  FIException (base)
    ├── StorageError
    │   ├── CorpusOperationError
    │   ├── SessionNotFoundError
    │   └── TranscriptionReadError
    ├── LLMError
    │   ├── LLMProviderError
    │   ├── LLMTimeoutError
    │   └── LLMValidationError
    ├── ValidationError
    │   ├── SessionValidationError
    │   └── SOAPValidationError
    ├── PolicyViolationError
    │   ├── AppendOnlyViolation
    │   ├── ExportPolicyViolation
    │   └── LLMRouterViolation
    └── WorkflowError
        ├── WorkflowNotFoundError
        └── TaskExecutionError

Created: 2025-01-XX
Author: Claude Code (P1 Architectural Fix)
"""

from __future__ import annotations

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BASE EXCEPTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class FIException(Exception):
    """Base exception for all Free Intelligence errors.

    All custom exceptions should inherit from this to enable
    consistent error handling and logging across the system.

    Attributes:
        message: Human-readable error message
        context: Optional dict with additional context (session_id, resource_id, etc.)
        status_code: Suggested HTTP status code for API responses
    """

    def __init__(
        self,
        message: str,
        context: dict[str, str] | None = None,
        status_code: int = 500,
    ):
        """Initialize exception.

        Args:
            message: Human-readable error message
            context: Optional context dict (session_id, resource_id, etc.)
            status_code: Suggested HTTP status code
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.status_code = status_code

    def __str__(self) -> str:
        """String representation with context."""
        if self.context:
            ctx_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} [{ctx_str}]"
        return self.message


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STORAGE ERRORS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class StorageError(FIException):
    """Base exception for storage/HDF5 operations."""

    def __init__(
        self,
        message: str,
        context: dict[str, str] | None = None,
        status_code: int = 500,
    ):
        super().__init__(message, context, status_code)


class CorpusOperationError(StorageError):
    """Error during corpus read/write operations."""

    def __init__(
        self,
        message: str,
        operation: str | None = None,
        context: dict[str, str] | None = None,
    ):
        ctx = context or {}
        if operation:
            ctx["operation"] = operation
        super().__init__(f"Corpus operation failed: {message}", ctx, 500)


class SessionNotFoundError(StorageError):
    """Session not found in storage."""

    def __init__(self, session_id: str, context: dict[str, str] | None = None):
        ctx = context or {}
        ctx["session_id"] = session_id
        super().__init__(
            f"Session not found: {session_id}",
            ctx,
            404,
        )


class TranscriptionReadError(StorageError):
    """Error reading transcription from storage."""

    def __init__(
        self,
        message: str,
        session_id: str | None = None,
        context: dict[str, str] | None = None,
    ):
        ctx = context or {}
        if session_id:
            ctx["session_id"] = session_id
        super().__init__(f"Transcription read failed: {message}", ctx, 500)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LLM ERRORS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class LLMError(FIException):
    """Base exception for LLM provider errors."""

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        context: dict[str, str] | None = None,
        status_code: int = 500,
    ):
        ctx = context or {}
        if provider:
            ctx["provider"] = provider
        super().__init__(message, ctx, status_code)


class LLMProviderError(LLMError):
    """Error from LLM provider (API failure, rate limit, etc.)."""

    def __init__(
        self,
        message: str,
        provider: str,
        context: dict[str, str] | None = None,
    ):
        super().__init__(
            f"LLM provider error ({provider}): {message}",
            provider,
            context,
            502,  # Bad Gateway
        )


class LLMTimeoutError(LLMError):
    """LLM request timed out."""

    def __init__(
        self,
        provider: str,
        timeout_seconds: float,
        context: dict[str, str] | None = None,
    ):
        ctx = context or {}
        ctx["timeout_seconds"] = str(timeout_seconds)
        super().__init__(
            f"LLM request timed out after {timeout_seconds}s ({provider})",
            provider,
            ctx,
            504,  # Gateway Timeout
        )


class LLMValidationError(LLMError):
    """LLM response validation failed (invalid JSON, schema mismatch, etc.)."""

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        context: dict[str, str] | None = None,
    ):
        super().__init__(
            f"LLM response validation failed: {message}",
            provider,
            context,
            422,  # Unprocessable Entity
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# VALIDATION ERRORS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ValidationError(FIException):
    """Base exception for validation errors."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        context: dict[str, str] | None = None,
    ):
        ctx = context or {}
        if field:
            ctx["field"] = field
        super().__init__(message, ctx, 400)


class SessionValidationError(ValidationError):
    """Session data validation failed."""

    def __init__(
        self,
        message: str,
        session_id: str | None = None,
        field: str | None = None,
        context: dict[str, str] | None = None,
    ):
        ctx = context or {}
        if session_id:
            ctx["session_id"] = session_id
        super().__init__(message, field, ctx)


class SOAPValidationError(ValidationError):
    """SOAP note validation failed."""

    def __init__(
        self,
        message: str,
        session_id: str | None = None,
        section: str | None = None,
        context: dict[str, str] | None = None,
    ):
        ctx = context or {}
        if session_id:
            ctx["session_id"] = session_id
        if section:
            ctx["section"] = section
        super().__init__(message, None, ctx)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# POLICY VIOLATION ERRORS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class PolicyViolationError(FIException):
    """Base exception for policy violations."""

    def __init__(
        self,
        message: str,
        policy_name: str | None = None,
        context: dict[str, str] | None = None,
        status_code: int = 403,
    ):
        ctx = context or {}
        if policy_name:
            ctx["policy"] = policy_name
        super().__init__(message, ctx, status_code)


class AppendOnlyViolation(PolicyViolationError):
    """Attempted mutation of append-only data structure."""

    def __init__(
        self,
        message: str,
        resource_path: str | None = None,
        context: dict[str, str] | None = None,
    ):
        ctx = context or {}
        if resource_path:
            ctx["resource_path"] = resource_path
        super().__init__(
            f"Append-only violation: {message}",
            "append_only_policy",
            ctx,
            403,
        )


class ExportPolicyViolation(PolicyViolationError):
    """Export operation violates policy."""

    def __init__(
        self,
        message: str,
        context: dict[str, str] | None = None,
    ):
        super().__init__(
            f"Export policy violation: {message}",
            "export_policy",
            context,
            403,
        )


class LLMRouterViolation(PolicyViolationError):
    """Direct LLM provider import violates router policy."""

    def __init__(
        self,
        provider: str,
        context: dict[str, str] | None = None,
    ):
        ctx = context or {}
        ctx["provider"] = provider
        super().__init__(
            f"LLM router policy violation: Direct import of {provider}",
            "llm_router_policy",
            ctx,
            403,
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# WORKFLOW ERRORS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class WorkflowError(FIException):
    """Base exception for workflow execution errors."""

    def __init__(
        self,
        message: str,
        session_id: str | None = None,
        context: dict[str, str] | None = None,
        status_code: int = 500,
    ):
        ctx = context or {}
        if session_id:
            ctx["session_id"] = session_id
        super().__init__(message, ctx, status_code)


class WorkflowNotFoundError(WorkflowError):
    """Workflow not found."""

    def __init__(
        self,
        session_id: str,
        context: dict[str, str] | None = None,
    ):
        super().__init__(
            f"Workflow not found for session: {session_id}",
            session_id,
            context,
            404,
        )


class TaskExecutionError(WorkflowError):
    """Error during task execution."""

    def __init__(
        self,
        message: str,
        task_type: str,
        session_id: str | None = None,
        context: dict[str, str] | None = None,
    ):
        ctx = context or {}
        ctx["task_type"] = task_type
        super().__init__(
            f"Task execution failed ({task_type}): {message}",
            session_id,
            ctx,
            500,
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SEARCH ERRORS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class SearchError(FIException):
    """Error during search operation."""

    def __init__(
        self,
        message: str,
        query: str | None = None,
        context: dict[str, str] | None = None,
    ):
        ctx = context or {}
        if query:
            ctx["query"] = query[:100]  # Truncate long queries
        super().__init__(f"Search failed: {message}", ctx, 500)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EXPORTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

__all__ = [
    # Base
    "FIException",
    # Storage
    "StorageError",
    "CorpusOperationError",
    "SessionNotFoundError",
    "TranscriptionReadError",
    # LLM
    "LLMError",
    "LLMProviderError",
    "LLMTimeoutError",
    "LLMValidationError",
    # Validation
    "ValidationError",
    "SessionValidationError",
    "SOAPValidationError",
    # Policy
    "PolicyViolationError",
    "AppendOnlyViolation",
    "ExportPolicyViolation",
    "LLMRouterViolation",
    # Workflow
    "WorkflowError",
    "WorkflowNotFoundError",
    "TaskExecutionError",
    # Search
    "SearchError",
]

