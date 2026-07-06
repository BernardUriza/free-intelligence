"""
fi_runner.models.contracts

Provider-agnostic model backend contracts for fi-runner.

This module defines the minimal interface required for workflow agents to
request model capabilities without knowing which provider executes the call.

Design rule:
    Agents declare intent and constraints.
    fi-runner resolves the backend.
    Product applications never hardcode provider clients inside agents.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Literal, Protocol, runtime_checkable


ModelRole = Literal["system", "developer", "user", "assistant", "tool"]

ModelFeature = Literal[
    "chat",
    "json",
    "streaming",
    "tools",
    "vision",
    "embeddings",
    "reasoning",
]


@dataclass(frozen=True, slots=True)
class ModelMessage:
    """
    Provider-neutral chat message.

    Notes:
        - The "developer" role is allowed at the contract layer even if a
          specific backend must map it to "system".
        - metadata is intentionally provider-neutral.
    """

    role: ModelRole
    content: str
    name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ModelRequest:
    """
    Provider-neutral model request.

    run_id:
        WorkflowRun identifier.
    agent_id:
        Logical agent identifier, e.g. "evidence_agent".
    purpose:
        Stable semantic purpose for audit logs, e.g. "review_campaign_safety".
    model:
        Optional model override. If omitted, backend default is used.
    response_format:
        "json" means the caller expects parseable JSON. Backends may implement
        this with provider-native JSON mode or prompt-level constraints.
    json_schema:
        Optional schema hint. Backends that do not support native JSON schema
        should preserve it in metadata or use it as instruction context.
    """

    run_id: str
    agent_id: str
    purpose: str

    messages: list[ModelMessage]

    model: str | None = None
    temperature: float = 0.2
    max_tokens: int = 1600

    response_format: Literal["text", "json"] = "text"
    json_schema: dict[str, Any] | None = None

    tools: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ModelUsage:
    """
    Normalized usage accounting.

    Token/cost fields are optional because not every provider returns them
    consistently.
    """

    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    cost_usd: float | None = None


@dataclass(frozen=True, slots=True)
class ModelResponse:
    """
    Provider-neutral completion response.
    """

    provider: str
    model: str
    content: str

    parsed: dict[str, Any] | list[Any] | None = None
    finish_reason: str | None = None
    usage: ModelUsage | None = None

    raw: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ModelDelta:
    """
    Provider-neutral streaming delta.
    """

    provider: str
    model: str
    delta: str
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class ModelBackend(Protocol):
    """
    Minimal pluggable model backend interface.

    Implementations:
        - ClaudeBackend
        - OpenAICompatibleBackend
        - AimlAPIBackend
        - FeatherlessBackend

    Backends must not know about domain contracts such as WorkflowRun,
    AgentHandoff, CampaignPacket, or SafetyVeto. Those remain workflow-layer
    concerns.
    """

    name: str
    provider: str
    default_model: str
    features: set[ModelFeature]

    async def complete(self, request: ModelRequest) -> ModelResponse:
        """
        Execute a non-streaming model request.
        """
        ...

    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelDelta]:
        """
        Execute a streaming model request.
        """
        ...

    async def healthcheck(self) -> bool:
        """
        Return True when the backend is configured and reachable enough to be
        considered usable by fi-runner.
        """
        ...
