"""
fi_runner.models.audit

Provider-neutral audit events for model calls.

These events are intentionally separate from workflow-domain events such as
AgentHandoff. They describe model infrastructure usage without leaking secrets
or coupling model providers to domain contracts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from .contracts import ModelRequest, ModelResponse, ModelUsage
from .registry import ModelResolution


ModelAuditEventType = Literal[
    "model_call_started",
    "model_call_completed",
    "model_call_failed",
]


@dataclass(frozen=True, slots=True)
class ModelAuditEvent:
    """
    Provider-neutral model call audit event.

    This object is safe to attach to workflow audit trails because it does not
    contain API keys, base URLs, clients, raw prompts outside request metadata,
    or provider-specific SDK objects.
    """

    event_type: ModelAuditEventType
    run_id: str
    agent_id: str
    purpose: str
    provider: str
    model: str

    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    backend: str | None = None
    finish_reason: str | None = None
    usage: dict[str, Any] | None = None
    error_type: str | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in ("event_type", "run_id", "agent_id", "purpose", "provider", "model"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"ModelAuditEvent.{field_name} must not be empty")
            object.__setattr__(self, field_name, value.strip())

        if self.backend is not None:
            object.__setattr__(self, "backend", self.backend.strip() or None)

    def to_dict(self) -> dict[str, Any]:
        """
        Return a JSON-serializable dict.
        """

        return asdict(self)


def model_call_started_event(
    *,
    request: ModelRequest,
    resolution: ModelResolution | None = None,
    metadata: dict[str, Any] | None = None,
) -> ModelAuditEvent:
    """
    Build a model_call_started event.
    """

    resolved = _resolve_audit_identity(request=request, resolution=resolution)

    return ModelAuditEvent(
        event_type="model_call_started",
        run_id=request.run_id,
        agent_id=request.agent_id,
        purpose=request.purpose,
        backend=resolved["backend"],
        provider=resolved["provider"],
        model=resolved["model"],
        metadata=_merge_metadata(request=request, metadata=metadata),
    )


def model_call_completed_event(
    *,
    request: ModelRequest,
    response: ModelResponse,
    resolution: ModelResolution | None = None,
    metadata: dict[str, Any] | None = None,
) -> ModelAuditEvent:
    """
    Build a model_call_completed event.
    """

    resolved = _resolve_audit_identity(request=request, resolution=resolution)

    return ModelAuditEvent(
        event_type="model_call_completed",
        run_id=request.run_id,
        agent_id=request.agent_id,
        purpose=request.purpose,
        backend=resolved["backend"],
        provider=response.provider or resolved["provider"],
        model=response.model or resolved["model"],
        finish_reason=response.finish_reason,
        usage=_usage_to_dict(response.usage),
        metadata=_merge_metadata(
            request=request,
            metadata={
                **(metadata or {}),
                "response_metadata": response.metadata,
            },
        ),
    )


def model_call_failed_event(
    *,
    request: ModelRequest,
    error: BaseException,
    resolution: ModelResolution | None = None,
    metadata: dict[str, Any] | None = None,
) -> ModelAuditEvent:
    """
    Build a model_call_failed event.
    """

    resolved = _resolve_audit_identity(request=request, resolution=resolution)

    return ModelAuditEvent(
        event_type="model_call_failed",
        run_id=request.run_id,
        agent_id=request.agent_id,
        purpose=request.purpose,
        backend=resolved["backend"],
        provider=resolved["provider"],
        model=resolved["model"],
        error_type=type(error).__name__,
        error_message=str(error),
        metadata=_merge_metadata(request=request, metadata=metadata),
    )


def _resolve_audit_identity(
    *,
    request: ModelRequest,
    resolution: ModelResolution | None,
) -> dict[str, str | None]:
    if resolution is not None:
        return {
            "backend": resolution.backend_name,
            "provider": resolution.provider,
            "model": request.model or resolution.model,
        }

    model_resolution = request.metadata.get("model_resolution", {})
    if not isinstance(model_resolution, dict):
        model_resolution = {}

    provider = str(model_resolution.get("provider") or "unknown")
    model = str(request.model or model_resolution.get("model") or "unknown")
    backend = model_resolution.get("backend")

    return {
        "backend": str(backend) if backend is not None else None,
        "provider": provider,
        "model": model,
    }


def _merge_metadata(
    *,
    request: ModelRequest,
    metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    merged: dict[str, Any] = {}

    model_resolution = request.metadata.get("model_resolution")
    if model_resolution is not None:
        merged["model_resolution"] = model_resolution

    if metadata:
        merged.update(metadata)

    return merged


def _usage_to_dict(usage: ModelUsage | None) -> dict[str, Any] | None:
    if usage is None:
        return None

    return {
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "total_tokens": usage.total_tokens,
        "cost_usd": usage.cost_usd,
    }
