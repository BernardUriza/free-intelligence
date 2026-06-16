"""Host router LLM — gpt-4.1 over Azure OpenAI, the demux host's reception brain.

PR-4b. Per the north-star ADR (`khimeras_demux_destilado.md`, "Las 3 verdades"):
gpt-4.1 is RECYCLED, not retired — it moves from being ALICE's brain to being
the demux HOST's brain. The host is a dumb router/receptionist: it classifies
intent, picks the target persona, detects a downed runner, and produces honest
operational degradation text when no persona can run. It does NOT serve a
persona and NEVER impersonates Insult / ALICE / Vultur — every persona runs on
the Claude runner. The deliberate provider split (OpenAI host vs Claude
personas) is the resilience play: the host survives a full Claude-runner outage
and can still route or degrade honestly.

This is the same `fi_runner.CodexBackend` over the shared `insult-openai` Azure
account that `personas/alice/core/llm.py` uses — minus the persona machinery.
The router has no character to protect, so there is NO persona prompt baked in
and NO anti-drift guard: callers pass the full instruction per call.

Boundary: `demux_ai` must never import `personas.*` (the host→persona ratchet is
0). Azure config is read from env vars (AZURE_OPENAI_*), the same env ALICE's
config reads — so the host stays independent of any persona package.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

import structlog
from fi_runner import CodexBackend, PermissionMode, RetryPolicy, Runner, ToolPolicy

log = structlog.get_logger()

DEFAULT_DEPLOYMENT = "gpt-4.1"
DEFAULT_API_VERSION = "2024-10-21"
_KEY_ENV = "AZURE_OPENAI_API_KEY"


class HostRouterError(Exception):
    """The host router (gpt-4.1) failed while classifying / routing / producing
    degradation text. Distinct from a persona-runner failure: this is the
    RECEPTIONIST brain breaking, not a persona's. Consumers classify it as
    ``FailoverReason.ROUTER_ERROR`` so logs never conflate a downed persona
    runner with a downed host router."""


@dataclass(frozen=True)
class HostLLMResult:
    """Token-accounted result of a host-router completion.

    Same shape family as ALICE's / Insult's ``LLMResponse`` so observability
    stays parallel, but this is the HOST's result — no persona attached.
    """

    text: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int


class HostRouterLLM:
    """The demux host's gpt-4.1 reception brain over Azure OpenAI via Codex.

    Thin: maps an instruction + input onto ``fi_runner.CodexBackend`` and reads
    back a token-accounted result. No persona, no anti-drift guard — the host is
    a router, not a character. Used for classification, routing decisions, and
    honest degradation text, never to answer AS a persona.
    """

    def __init__(
        self,
        api_key: str | None = None,
        endpoint: str | None = None,
        deployment: str | None = None,
        api_version: str | None = None,
    ):
        self.api_key = api_key or os.environ.get("AZURE_OPENAI_KEY", "")
        self.endpoint = (endpoint or os.environ.get("AZURE_OPENAI_ENDPOINT", "")).rstrip("/")
        self.model = deployment or os.environ.get("AZURE_OPENAI_GPT_DEPLOYMENT", DEFAULT_DEPLOYMENT)
        self.api_version = api_version or os.environ.get("AZURE_OPENAI_API_VERSION", DEFAULT_API_VERSION)

        # Codex reads the key from an env var name, not a value. Bridge our held
        # value to the name Codex expects; setdefault so an explicit one wins.
        if self.api_key:
            os.environ.setdefault(_KEY_ENV, self.api_key)

        # One stateless backend reused across calls, pointed at the SAME Azure
        # endpoint ALICE used — recycled brain, no ChatGPT subscription.
        self._backend = CodexBackend(
            default_model=self.model,
            azure_endpoint=self.endpoint,
            azure_api_key_env=_KEY_ENV,
        )

    async def complete(self, instruction: str, user_text: str, *, model: str | None = None) -> HostLLMResult:
        """Run one host-router completion: instruction + input -> text.

        ``instruction`` is the routing/classification/degradation directive (the
        host's operational prompt, NOT a persona). ``user_text`` is the input to
        act on. Codex owns retry/backoff internally; we run with NO guards
        because the host has no character to keep in. A hard API failure
        surfaces as RuntimeError from the runner.
        """
        chosen_model = model or self.model
        runner = Runner(
            backend=self._backend,
            persona=instruction,
            guards=[],
            retry_policy=RetryPolicy(max_attempts=2),
            tool_policy=ToolPolicy(permission_mode=PermissionMode.DEFAULT),
            model=chosen_model,
        )
        start = time.monotonic()
        try:
            result = await runner.run(user_text)
        except Exception as e:
            latency_ms = int((time.monotonic() - start) * 1000)
            log.warning(
                "host_router_llm_error",
                model=chosen_model,
                error_type=type(e).__name__,
                error_msg=str(e)[:200],
                latency_ms=latency_ms,
                backend="codex",
            )
            raise HostRouterError(f"host router {chosen_model} failed: {type(e).__name__}: {e}") from e
        latency_ms = int((time.monotonic() - start) * 1000)

        usage = result.usage or {}
        input_tokens = int(usage.get("input_tokens", 0))
        output_tokens = int(usage.get("output_tokens", 0))
        log.info(
            "host_router_llm_response",
            model=chosen_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            backend="codex",
        )
        return HostLLMResult(
            text=result.text,
            model=chosen_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
        )
