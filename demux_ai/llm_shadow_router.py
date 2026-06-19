"""LLM shadow router — the demux host's gpt-4.1 routing decision (HOST 5/6 slice A.2).

Slice A shipped a DETERMINISTIC shadow (``shadow_router.py``) that mirrors the
live ``@vultur``/``~vultur`` rule by construction. Because it is identical to the
live path, it can never diverge — proven in prod (2026-06-18): every event came
back ``diverged=false``. A GENUINE divergence — the signal that tells us whether
an LLM receptionist would route differently than today's prefix rule — needs a
router that is NOT a copy of the live rule. This is that router: it asks the
gpt-4.1 host brain to classify the target persona independently, runs in SHADOW
only (logged next to ``current_target``, never acted on), and is spend-gated by
``settings.llm_shadow_router_enabled`` (default OFF, unlike the deterministic
shadow which is free).

It NEVER serves a persona and NEVER impersonates — it emits a routing label, the
turn still goes wherever the live rule sent it (no cutover).

Boundary: ``demux_ai`` must never import ``personas.*`` (host→persona ratchet is
0). The valid-target set is mirrored as a constant — parity with
``shadow_router._VULTUR_PREFIXES`` — kept in lockstep with the registered
personas (``shared/personas/registry.py``) + the implicit Insult host, WITHOUT
importing any persona package.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from demux_ai.host_llm import HostRouterLLM

log = structlog.get_logger()

# Azure OpenAI defaults — mirror demux_ai.host_llm so the direct transport reads
# the SAME env (AZURE_OPENAI_ENDPOINT/KEY/GPT_DEPLOYMENT/API_VERSION) the agentic
# one does, without importing host_llm (which would drag fi_runner onto the cheap
# direct path).
_DEFAULT_DEPLOYMENT = "gpt-4.1"
_DEFAULT_API_VERSION = "2024-10-21"

# The default target when the host LLM gives nothing parseable. Mirrors the
# deterministic shadow's ``_DEFAULT_TARGET`` → Insult downstream.
_DEFAULT_TARGET = "insult"

# Valid routing targets the host brain may pick. Mirrors the Insult host plus the
# registered sibling personas (shared/personas/registry.py). Kept as a constant —
# NOT an import — so demux_ai stays free of any persona dependency; the lockstep
# is guarded by ``test_valid_targets_mirror_the_registry_in_lockstep``.
_VALID_TARGETS = ("insult", "vultur")

_ROUTING_INSTRUCTION = (
    "You are the routing brain of a multi-persona Discord system. Decide which "
    "persona should handle the user's message.\n\n"
    "Personas:\n"
    "- insult: the default host — abrasive, psychologically probing. Handles "
    "everything by default.\n"
    "- vultur: a film-criticism specialist. ONLY for messages clearly about "
    "cinema, films, directors, movie recommendations or reviews.\n\n"
    "Reply with EXACTLY one lowercase word and nothing else: insult or vultur."
)


@dataclass(frozen=True)
class LLMShadowDecision:
    """A gpt-4.1 shadow routing decision: which persona the host brain would pick,
    plus a greppable reason token (``llm_<target>`` clean / ``llm_<target>_loose``
    extracted-from-prose / ``llm_unparseable``) so divergence telemetry can be
    bucketed by parse quality. Token counts ride along for spend accounting."""

    target: str
    reason: str
    input_tokens: int = 0
    output_tokens: int = 0


def _parse_target(text: str) -> tuple[str, str]:
    """Map a host-LLM completion onto a (target, reason) pair. Tolerant: a clean
    one-word reply is ``llm_<target>``; a target name buried in prose is
    ``llm_<target>_loose``; nothing recognizable falls back to the default with
    ``llm_unparseable`` so the shadow never crashes on a chatty model."""
    lowered = text.strip().lower()
    for target in _VALID_TARGETS:
        if lowered == target:
            return target, f"llm_{target}"
    for target in _VALID_TARGETS:
        if target in lowered:
            return target, f"llm_{target}_loose"
    return _DEFAULT_TARGET, "llm_unparseable"


class LLMShadowRouter:
    """Wraps the gpt-4.1 ``HostRouterLLM`` as a shadow-only persona classifier.

    Construct it (which builds ``HostRouterLLM`` → ``CodexBackend``) ONLY behind
    the ``llm_shadow_router_enabled`` flag — that construction is the spend gate.
    ``route`` is async (a real Azure call); callers run it OFF the turn's critical
    path (a background task) so the user's reply is never delayed by routing
    telemetry."""

    def __init__(self, llm: HostRouterLLM | None = None) -> None:
        if llm is None:
            from demux_ai.host_llm import HostRouterLLM  # deferred: keeps fi_runner off the direct path

            llm = HostRouterLLM()
        self._llm = llm

    async def route(self, text: str) -> LLMShadowDecision:
        """Classify ``text`` to a target persona via gpt-4.1. Returns a decision
        with the parsed target + reason + token counts. Raises on a hard LLM
        failure (``HostRouterError``) — the caller wraps it so a shadow fault is
        invisible to the turn."""
        result = await self._llm.complete(_ROUTING_INSTRUCTION, text)
        target, reason = _parse_target(result.text)
        return LLMShadowDecision(
            target=target,
            reason=reason,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )


class DirectAzureLLMRouter:
    """Direct Azure OpenAI chat-completion transport for the shadow router.

    The cheap alternative to ``LLMShadowRouter`` (which goes through the agentic
    ``CodexBackend`` → ``codex exec`` CLI and pays ~9.5k input tokens of agent
    harness per call, HOST 5/6 slice A.2 token-bloat fix). This sends ONLY the
    routing instruction + the user input over ``openai.AsyncAzureOpenAI`` against
    the SAME ``insult-openai`` deployment — no agent harness, no tool schemas — so
    a one-word classification costs hundreds of tokens, not thousands. Shape-
    compatible: same ``route(text) -> LLMShadowDecision`` contract, so it drops
    into ``TurnRuntimeDeps.llm_shadow_route`` behind the same seam."""

    def __init__(self, client: object | None = None, deployment: str | None = None) -> None:
        self._client = client  # injectable for tests (no Azure, no spend)
        self._deployment = deployment or os.environ.get("AZURE_OPENAI_GPT_DEPLOYMENT", _DEFAULT_DEPLOYMENT)

    def _ensure_client(self) -> object:
        if self._client is None:
            from openai import AsyncAzureOpenAI  # deferred: only when the direct path is actually used

            self._client = AsyncAzureOpenAI(
                azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/"),
                api_key=os.environ.get("AZURE_OPENAI_KEY", ""),
                api_version=os.environ.get("AZURE_OPENAI_API_VERSION", _DEFAULT_API_VERSION),
            )
        return self._client

    async def route(self, text: str) -> LLMShadowDecision:
        """Classify ``text`` via a plain Azure chat completion. Returns the parsed
        target + reason + REAL token counts (``usage.prompt_tokens`` is the number
        the whole exercise is measuring). Raises on a hard API failure — the caller
        wraps it so a shadow fault stays invisible to the turn."""
        client = self._ensure_client()
        resp = await client.chat.completions.create(  # type: ignore[attr-defined]
            model=self._deployment,
            messages=[
                {"role": "system", "content": _ROUTING_INSTRUCTION},
                {"role": "user", "content": text},
            ],
            max_tokens=8,
            temperature=0,
        )
        out = resp.choices[0].message.content or ""
        target, reason = _parse_target(out)
        usage = resp.usage
        return LLMShadowDecision(
            target=target,
            reason=reason,
            input_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
        )


__all__ = ["DirectAzureLLMRouter", "LLMShadowDecision", "LLMShadowRouter"]
