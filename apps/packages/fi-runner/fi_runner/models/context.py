"""
fi_runner.models.context

Minimal runner context for model-backed workflow agents.

This module provides the smallest integration point required for agents to use
the ModelRegistry without knowing provider details.

Design rule:
    ctx.models resolves model infrastructure.
    Agents remain provider-agnostic.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from .contracts import (
    ModelDelta,
    ModelMessage,
    ModelRequest,
    ModelResponse,
)
from .registry import ModelRegistry, ModelResolution


class RunnerContextError(RuntimeError):
    """Raised when a RunnerContext is invalid or cannot build a model request."""


@dataclass(frozen=True, slots=True)
class RunnerContext:
    """
    Minimal workflow runner context.

    run_id:
        WorkflowRun identifier.

    models:
        ModelRegistry used to resolve agent_id -> backend/model.

    metadata:
        Optional workflow-level metadata. Must not contain secrets.

    Example:
        resolution = ctx.models.resolve("safety_agent")
        response = await resolution.backend.complete(
            ctx.model_request(
                agent_id="safety_agent",
                purpose="review_campaign_safety",
                messages=[...],
            )
        )

    Convenience:
        response = await ctx.complete_model(...)
    """

    run_id: str
    models: ModelRegistry
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        normalized_run_id = self.run_id.strip()

        if not normalized_run_id:
            raise RunnerContextError("RunnerContext.run_id must not be empty")

        object.__setattr__(self, "run_id", normalized_run_id)

        if self.models is None:
            raise RunnerContextError("RunnerContext.models must not be None")

    def resolve_model(self, agent_id: str) -> ModelResolution:
        """
        Resolve the configured model backend for an agent.
        """

        return self.models.resolve(agent_id)

    def model_request(
        self,
        *,
        agent_id: str,
        purpose: str,
        messages: Sequence[ModelMessage],
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1600,
        response_format: Literal["text", "json"] = "text",
        json_schema: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ModelRequest:
        """
        Build a provider-neutral ModelRequest for an agent.

        If model is not explicitly provided, the model resolved by registry route
        is used. This keeps agent code stable when provider/model routing changes.
        """

        normalized_agent_id = agent_id.strip()
        normalized_purpose = purpose.strip()

        if not normalized_agent_id:
            raise RunnerContextError("agent_id must not be empty")

        if not normalized_purpose:
            raise RunnerContextError("purpose must not be empty")

        if not messages:
            raise RunnerContextError("messages must not be empty")

        resolution = self.resolve_model(normalized_agent_id)
        selected_model = model or resolution.model

        request_metadata = dict(metadata or {})
        request_metadata.setdefault("model_resolution", resolution.audit_metadata)

        return ModelRequest(
            run_id=self.run_id,
            agent_id=normalized_agent_id,
            purpose=normalized_purpose,
            messages=list(messages),
            model=selected_model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
            json_schema=json_schema,
            tools=tools,
            metadata=request_metadata,
        )

    async def complete_model(
        self,
        *,
        agent_id: str,
        purpose: str,
        messages: Sequence[ModelMessage],
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1600,
        response_format: Literal["text", "json"] = "text",
        json_schema: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ModelResponse:
        """
        Resolve backend and execute a non-streaming model call.

        This is a convenience method. Agents may still call ctx.models.resolve()
        directly when they need lower-level control.
        """

        normalized_agent_id = agent_id.strip()
        resolution = self.resolve_model(normalized_agent_id)

        request = self.model_request(
            agent_id=normalized_agent_id,
            purpose=purpose,
            messages=messages,
            model=model or resolution.model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
            json_schema=json_schema,
            tools=tools,
            metadata=metadata,
        )

        return await resolution.backend.complete(request)

    async def stream_model(
        self,
        *,
        agent_id: str,
        purpose: str,
        messages: Sequence[ModelMessage],
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1600,
        response_format: Literal["text", "json"] = "text",
        json_schema: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AsyncIterator[ModelDelta]:
        """
        Resolve backend and execute a streaming model call.
        """

        normalized_agent_id = agent_id.strip()
        resolution = self.resolve_model(normalized_agent_id)

        request = self.model_request(
            agent_id=normalized_agent_id,
            purpose=purpose,
            messages=messages,
            model=model or resolution.model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
            json_schema=json_schema,
            tools=tools,
            metadata=metadata,
        )

        async for delta in resolution.backend.stream(request):
            yield delta
