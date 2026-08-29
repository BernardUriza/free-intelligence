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
0). The valid-target set is mirrored as a constant, kept in lockstep with the
registered personas (``shared/personas/registry.py``) + the implicit Insult host,
WITHOUT importing any persona package.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

from demux_ai.router_budget import RouterBudget
from khimeras_shared.prompts import PromptCache, load_prompt

if TYPE_CHECKING:
    from demux_ai.host_llm import HostRouterLLM

log = structlog.get_logger()

# Azure OpenAI defaults. These USED to mirror demux_ai.host_llm, which read the
# same AZURE_OPENAI_* env through fi_runner's Codex backend; since the 2026-08-29
# AIREBackend consolidation host_llm speaks to AIRE's door instead, so this is
# now the ONLY reader of these vars in the repo — no longer a mirror, the
# original. Still declared here rather than imported, so the cheap direct path
# never drags fi_runner in.
_DEFAULT_DEPLOYMENT = "gpt-4.1"
_DEFAULT_API_VERSION = "2024-10-21"

# The default target when the host LLM gives nothing parseable. Mirrors the
# deterministic shadow's ``_DEFAULT_TARGET`` → Insult downstream.
_DEFAULT_TARGET = "insult"
DEFAULT_TARGET = _DEFAULT_TARGET

# Valid routing targets the host brain may pick. Mirrors the Insult host plus the
# registered sibling personas (shared/personas/registry.py). Kept as a constant —
# NOT an import — so demux_ai stays free of any persona dependency; the lockstep
# is guarded by ``test_valid_targets_mirror_the_registry_in_lockstep``.
_VALID_TARGETS = ("insult", "vultur", "alice", "frugivoro", "unborn_being", "valentis")

_PROMPTS_DIR = Path(__file__).parent / "prompts"
_PROMPT_CACHE: PromptCache = {}


def _routing_instruction() -> str:
    return load_prompt(_PROMPTS_DIR, "host_routing", _PROMPT_CACHE)


def _compose_route_input(text: str, context: str | None) -> str:
    """Build the user-message payload for the routing completion. Without context
    it is the bare message (byte-identical to the pre-context router, so existing
    telemetry stays comparable); with context the recent-conversation block rides
    ABOVE the current message so the brain can detect continuations."""
    if not context:
        return text
    return f"Recent channel conversation (oldest first):\n{context}\n---\nCurrent message to route:\n{text}"


@dataclass(frozen=True)
class LLMShadowDecision:
    """A gpt-4.1 shadow routing decision: which persona the host brain would pick,
    plus a greppable reason token (``llm_<target>`` clean / ``llm_<target>_loose``
    extracted-from-prose / ``llm_unparseable``) so divergence telemetry can be
    bucketed by parse quality. Token counts ride along for spend accounting.

    (Hubo un campo ``effort`` aquí: el prompt le pedía al modelo una estimación
    de esfuerzo y le aseguraba que "this sets how long the persona is given to
    work". No tenía UN SOLO consumidor — se parseaba y se tiraba, así que la
    promesa era mentira y el razonamiento del modelo, desperdicio. Borrado el
    2026-08-06 con su sección del prompt. Si alguna vez se quiere de vuelta,
    vuelve CON su consumidor en el mismo PR, nunca antes.)"""

    target: str
    reason: str
    input_tokens: int = 0
    output_tokens: int = 0


def _parse_target(text: str) -> tuple[str, str]:
    """Map a host-LLM completion onto a (target, reason) pair. Tolerant: a clean
    one-word FIRST LINE is ``llm_<target>``; a target name buried in prose is
    ``llm_<target>_loose``; nothing recognizable falls back to the default with
    ``llm_unparseable`` so the shadow never crashes on a chatty model. Matching
    the FIRST LINE (not the whole text) survives a model that adds prose after
    the word."""
    stripped = text.strip()
    first_line = stripped.splitlines()[0].strip().lower() if stripped else ""
    for target in _VALID_TARGETS:
        if first_line == target:
            return target, f"llm_{target}"
    lowered = stripped.lower()
    for target in _VALID_TARGETS:
        if target in lowered:
            return target, f"llm_{target}_loose"
    return _DEFAULT_TARGET, "llm_unparseable"


def _is_content_filter(error: BaseException) -> bool:
    """True when Azure OpenAI rejected the PROMPT under its content management
    policy (HTTP 400, ``code='content_filter'``). Checked structurally first and
    by message text second, because the SDK surfaces the code on the exception
    for a real API error but callers/tests may only carry the message."""
    if getattr(error, "code", None) == "content_filter":
        return True
    message = str(error)
    return "content management policy" in message or "'content_filter'" in message


class LLMShadowRouter:
    """Wraps the gpt-4.1 ``HostRouterLLM`` as a shadow-only persona classifier.

    Construct it (which builds ``HostRouterLLM`` → ``AIREBackend``) ONLY behind
    the ``llm_shadow_router_enabled`` flag — that construction is the spend gate.
    ``route`` is async (a real Azure call); callers run it OFF the turn's critical
    path (a background task) so the user's reply is never delayed by routing
    telemetry."""

    def __init__(self, llm: HostRouterLLM | None = None) -> None:
        if llm is None:
            from demux_ai.host_llm import HostRouterLLM  # deferred: keeps fi_runner off the direct path

            llm = HostRouterLLM()
        self._llm = llm

    async def route(self, text: str, context: str | None = None) -> LLMShadowDecision:
        """Classify ``text`` to a target persona via gpt-4.1. ``context`` is an
        optional recent-conversation block (newline-joined ``user: message`` lines)
        that lets the brain route continuations to the persona already holding the
        exchange. Returns a decision with the parsed target + reason + token
        counts. Raises on a hard LLM failure (``HostRouterError``) — the caller
        wraps it so a shadow fault is invisible to the turn."""
        result = await self._llm.complete(_routing_instruction(), _compose_route_input(text, context))
        target, reason = _parse_target(result.text)
        return LLMShadowDecision(
            target=target,
            reason=reason,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )


class DirectAzureLLMRouter:
    """Direct Azure OpenAI chat-completion transport for the shadow router.

    The cheap alternative to ``LLMShadowRouter``, which routes through an agentic
    backend: when it was measured (HOST 5/6 slice A.2 token-bloat fix) that was
    ``CodexBackend`` → ``codex exec``, paying ~9.5k input tokens of agent harness
    per call; since 2026-08-29 it is ``AIREBackend`` and the harness cost has NOT
    been re-measured. This class sends ONLY the routing instruction + the user
    input over ``openai.AsyncAzureOpenAI`` against the ``insult-openai``
    deployment — no agent harness, no tool schemas — so a one-word classification
    costs hundreds of tokens, not thousands. It is also the only brain in this
    repo that does not depend on AIRE's door: the provider split the host used to
    get from Codex now lives here alone. Shape-compatible: same
    ``route(text) -> LLMShadowDecision`` contract, so it drops into
    ``TurnRuntimeDeps.llm_shadow_route`` behind the same seam."""

    def __init__(
        self,
        client: object | None = None,
        deployment: str | None = None,
        budget: RouterBudget | None = None,
    ) -> None:
        self._client = client  # injectable for tests (no Azure, no spend)
        self._deployment = deployment or os.environ.get("AZURE_OPENAI_GPT_DEPLOYMENT", _DEFAULT_DEPLOYMENT)
        self._budget = RouterBudget() if budget is None else budget

    def _ensure_client(self) -> object:
        if self._client is None:
            from openai import AsyncAzureOpenAI  # deferred: only when the direct path is actually used

            self._client = AsyncAzureOpenAI(
                azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/"),
                api_key=os.environ.get("AZURE_OPENAI_KEY", ""),
                api_version=os.environ.get("AZURE_OPENAI_API_VERSION", _DEFAULT_API_VERSION),
            )
        return self._client

    async def route(self, text: str, context: str | None = None) -> LLMShadowDecision:
        """Classify ``text`` via a plain Azure chat completion. ``context`` is the
        same optional recent-conversation block ``LLMShadowRouter.route`` takes
        (shape-compatible contract). Returns the parsed target + reason + REAL
        token counts (``usage.prompt_tokens`` is the number the whole exercise is
        measuring). Raises on a hard API failure — the caller wraps it so a shadow
        fault stays invisible to the turn.

        Azure's content filter is the exception that must NOT raise. It rejects
        the whole prompt with a 400, and the prompt carries the recent channel
        conversation — so one drug/self-harm/sexual turn anywhere in the window
        poisons every later message in that thread, including a message as inert
        as "explica mejor lo anterior". A filtered prompt is a brain that refuses
        to have an opinion, not a transport failure: retry WITHOUT the context
        (usually the poisoned half, and the current message routes fine alone),
        and if the bare message is filtered too, fall back to the same
        ``DEFAULT_TARGET`` an unparseable reply already falls back to. Silence is
        never the answer — the personas run on Claude and are perfectly able to
        reply while gpt-4.1 refuses to route.

        El cap semanal se consulta ANTES de gastar. Bernard lo autorizó en
        `d194292` (2026-06-21, $5/semana) y `RouterBudget` existe desde entonces
        para hacerlo cumplir — pero la purga se llevó a su único llamador y el
        router siguió gastando un mes sin tope, con el módulo intacto en el árbol
        diciendo en su propio docstring que era "an honored constraint, not a
        fake-green". Rebasar el cap degrada al `DEFAULT_TARGET`, el mismo
        fail-safe que ya usa el filtro de contenido: el ruteo se vuelve tonto,
        nunca mudo."""
        if not self._budget.can_spend():
            log.warning(
                "host_router_budget_exceeded",
                spent_usd=round(self._budget.spent_this_week(), 4),
                cap_usd=self._budget.cap_usd,
                target=DEFAULT_TARGET,
            )
            return LLMShadowDecision(target=DEFAULT_TARGET, reason="llm_budget_exceeded")
        try:
            return await self._complete(text, context)
        except Exception as e:
            if not _is_content_filter(e):
                raise
            if context:
                try:
                    decision = await self._complete(text, None)
                except Exception as retry_error:
                    if not _is_content_filter(retry_error):
                        raise
                else:
                    log.warning(
                        "host_router_content_filtered",
                        model=self._deployment,
                        target=decision.target,
                        recovered_without_context=True,
                    )
                    return decision
            log.warning(
                "host_router_content_filtered",
                model=self._deployment,
                target=DEFAULT_TARGET,
                recovered_without_context=False,
            )
            return LLMShadowDecision(target=DEFAULT_TARGET, reason="llm_content_filtered")

    async def _complete(self, text: str, context: str | None) -> LLMShadowDecision:
        """One routing completion against Azure. Raises on any API failure."""
        client = self._ensure_client()
        start = time.monotonic()
        try:
            resp = await client.chat.completions.create(  # type: ignore[attr-defined]
                model=self._deployment,
                messages=[
                    {"role": "system", "content": _routing_instruction()},
                    {"role": "user", "content": _compose_route_input(text, context)},
                ],
                max_tokens=16,
                temperature=0,
            )
        except Exception as e:
            log.warning(
                "host_router_llm_error",
                model=self._deployment,
                error_type=type(e).__name__,
                error_msg=str(e)[:200],
                latency_ms=int((time.monotonic() - start) * 1000),
                backend="azure_direct",
            )
            raise
        latency_ms = int((time.monotonic() - start) * 1000)
        out = resp.choices[0].message.content or ""
        target, reason = _parse_target(out)
        usage = resp.usage
        input_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        spent_usd = self._budget.record(input_tokens, output_tokens)
        log.info(
            "host_router_llm_response",
            model=self._deployment,
            target=target,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            backend="azure_direct",
            spent_usd=round(spent_usd, 4),
            cap_usd=self._budget.cap_usd,
        )
        return LLMShadowDecision(
            target=target,
            reason=reason,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )


__all__ = ["DEFAULT_TARGET", "DirectAzureLLMRouter", "LLMShadowDecision", "LLMShadowRouter"]
