"""Shared runner transport — HTTP clients to the persona-runner (Agent SDK).

Persona-neutral transport: the `AgentRunnerClient` (POST /v1/turn) speaks the
shared `khimeras_shared.llm.types.LLMResponse` contract and is consumed by both
the Insult process wiring and the persona_gateway, so it lives in the shared
infra layer rather than inside any persona. Moved here in Etapa 3 PR-1b.
"""

from __future__ import annotations

from khimeras_shared.runner.agent_client import (
    AgentRunnerClient,
    AgentRunnerError,
    PersonaTurnError,
    RunnerDownError,
)

__all__ = ["AgentRunnerClient", "AgentRunnerError", "PersonaTurnError", "RunnerDownError"]
