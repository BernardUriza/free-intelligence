"""Host router LLM — the demux host's reception brain, over AIRE.

PR-4b. Per the north-star ADR (`khimeras_demux_destilado.md`, "Las 3 verdades"):
the host is a dumb router/receptionist: it classifies intent, picks the target
persona, detects a downed runner, and produces honest operational degradation
text when no persona can run. It does NOT serve a persona and NEVER impersonates
Insult / ALICE / Vultur. The router has no character to protect, so there is NO
persona prompt baked in and NO anti-drift guard: callers pass the full
instruction per call.

TRANSPORT (2026-08-29, the AIREBackend consolidation). This used to be
`fi_runner.CodexBackend` against the shared `insult-openai` Azure deployment
(gpt-4.1). fi-runner deleted `CodexBackend`/`ClaudeCodeBackend`/
`SubprocessCLIBackend`; `AIREBackend` is the only backend left, so this module
now speaks to AIRE's door like `persona_runner.engine.aire_route` does.

WHAT THAT COSTS, stated plainly instead of buried: the deliberate provider split
is GONE. The old docstring's resilience play — "the host survives a full
Claude-runner outage and can still route or degrade honestly" — depended on the
host brain running on OpenAI while the personas ran on Claude. AIRE wraps the
Claude Agent SDK, so host and personas now share one provider and one door: an
AIRE outage takes both down at once. The cheap live path
(`DirectAzureLLMRouter`, which talks to Azure through the `openai` SDK and never
imported fi_runner) is the only Azure-independent brain left in this repo.

Config: `AIRE_GATE_URL` + `AIRE_AUTH_TOKEN` (read from the env by
`AIREBackend`), the same pair `persona_runner` already requires. The Azure
knobs this module used to read (`AZURE_OPENAI_KEY`/`_ENDPOINT`/
`_GPT_DEPLOYMENT`/`_API_VERSION`) are no longer consumed here — they still feed
`DirectAzureLLMRouter`.

Casita: `HOST_ROUTER_PROJECT` (default `demux`), separate from every persona's
casita so a routing turn can never rewrite a persona's living CLAUDE.md. NOTE
the door's shape: the instruction passed to `complete()` becomes the casita's
FIXED prompt via `/init`, re-sent only when it changes — so a caller that
alternates between two instructions re-inits the casita on every alternation.
Today there is exactly one (`demux_ai/prompts/host_routing.md`).

Boundary: `demux_ai` must never import `personas.*` (the host→persona ratchet is
0), and it does not import `persona_runner` either — the AIRE config is read
from the env, so the host stays independent of every persona package.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

import structlog
from fi_runner import AIREBackend, RetryPolicy, Runner, ToolPolicy

log = structlog.get_logger()

# The host's own AIRE casita — never a persona's.
DEFAULT_PROJECT = "demux"
# A one-word classification does not need a frontier model; AIRE accepts a short
# name and pins it on the session's pooled client.
DEFAULT_MODEL = "haiku"
# The router calls no tools and needs no builtins. `complete` grants none;
# `agent` would drag in Read/Write/Glob/Grep/WebSearch/WebFetch for a task that
# emits one word. (Bash is prohibited in both.)
ROUTER_MODE = "complete"


class HostRouterError(Exception):
    """The host router failed while classifying / routing / producing
    degradation text. Distinct from a persona-runner failure: this is the
    RECEPTIONIST brain breaking, not a persona's. Consumers classify it as
    ``FailoverReason.ROUTER_ERROR`` so logs never conflate a downed persona
    runner with a downed host router."""


@dataclass(frozen=True)
class HostLLMResult:
    """Token-accounted result of a host-router completion.

    Same shape family as ALICE's / Insult's ``LLMResponse`` so observability
    stays parallel, but this is the HOST's result — no persona attached.

    ``model`` is the model that ANSWERED when AIRE reports it (the door reads it
    off the AssistantMessages), falling back to the requested one if it does not.
    """

    text: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int


class HostRouterLLM:
    """The demux host's reception brain, over AIRE's door.

    Thin: maps an instruction + input onto ``fi_runner.AIREBackend`` and reads
    back a token-accounted result. No persona, no anti-drift guard — the host is
    a router, not a character. Used for classification, routing decisions, and
    honest degradation text, never to answer AS a persona.
    """

    def __init__(
        self,
        project: str | None = None,
        model: str | None = None,
        gate_url: str | None = None,
        auth_token: str | None = None,
    ):
        self.project = project or os.environ.get("HOST_ROUTER_PROJECT", DEFAULT_PROJECT)
        self.model = model or os.environ.get("HOST_ROUTER_MODEL", DEFAULT_MODEL)

        # One stateless backend reused across calls. It holds a pooled
        # httpx.AsyncClient — see `aclose()`.
        self._backend = AIREBackend(
            project=self.project,
            gate_url=gate_url,
            auth_token=auth_token,
            default_model=self.model,
            default_mode=ROUTER_MODE,
        )

    async def complete(self, instruction: str, user_text: str, *, model: str | None = None) -> HostLLMResult:
        """Run one host-router completion: instruction + input -> text.

        ``instruction`` is the routing/classification/degradation directive (the
        host's operational prompt, NOT a persona) and lands as the casita's
        fixed prompt. ``user_text`` is the input to act on. We run with NO guards
        because the host has no character to keep in. No ``session_id`` is
        passed: a classification is stateless, so AIRE mints a throwaway session
        per turn instead of accumulating a transcript nobody resumes.
        """
        chosen_model = model or self.model
        runner = Runner(
            backend=self._backend,
            persona=instruction,
            guards=[],
            retry_policy=RetryPolicy(max_attempts=2),
            # AIRE governs tools server-side (`ROUTER_MODE`); a non-default
            # policy here would only earn a warning, never an effect.
            tool_policy=ToolPolicy(),
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
                backend="aire",
            )
            raise HostRouterError(f"host router {chosen_model} failed: {type(e).__name__}: {e}") from e
        latency_ms = int((time.monotonic() - start) * 1000)

        usage = result.usage or {}
        input_tokens = int(usage.get("input_tokens", 0))
        output_tokens = int(usage.get("output_tokens", 0))
        answered_model = result.model or chosen_model
        log.info(
            "host_router_llm_response",
            model=answered_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            backend="aire",
        )
        return HostLLMResult(
            text=result.text,
            model=answered_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
        )

    async def aclose(self) -> None:
        """Close the backend's pooled HTTP client. Mirrors
        ``aire_route.close_backends()`` — a door client that nobody closes leaks
        its connections and TLS sessions past shutdown."""
        await self._backend.aclose()
