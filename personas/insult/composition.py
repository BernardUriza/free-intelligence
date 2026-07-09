"""Composition seam — wires smart/persona domain services to their host PORTS.

This module is the composition root for the turn-runtime domain ports
(``insult/cogs/chat/ports.py``) and capability ports
(``insult/cogs/chat/capability_ports.py``). It is the ONE place that legitimately imports
both a host-side ``Protocol`` and the concrete ``insult.core.*`` service behind
it, then hands the host a ready-built adapter. The host plumbing
(``cog.py`` → ``TurnRuntimeDeps``) imports the *built port* from here and never
the ``insult.core`` internals directly — keeping the host→smart boundary
(``tests/test_arch_import_boundaries.py``) clean.

This is intentionally NOT in ``HOST_FACING_PATTERNS``: a composition root is the
wiring layer, neither pure host plumbing nor a smart internal. It is allowed to
know both sides; that is its job. Distinct from the deferred app/__main__→memory
governance question — those are the legacy container imports; this is the
purpose-built seam for the S2/S5 domain ports.

Design plan: ``.claude/plans/s2_s5_domain_facets_multipr.md``.

Adapter map
-----------
All adapters live here. ``cog.py`` is the sole consumer — it imports the
``default_*`` factory functions and the two ``build_*`` builders. No other
module wires domain services to ports.

+--------------------------------+----------+----------------------------------+
| Adapter                        | Lifecycle | Factory                          |
+================================+==========+==================================+
| ``_CoreFactsAdapter``          | stateless | ``default_facts_port()``         |
+--------------------------------+----------+----------------------------------+
| ``_CoreStanceAdapter``         | stateless | ``default_stance_port()``        |
+--------------------------------+----------+----------------------------------+
| ``_CoreArcAdapter``            | stateless | ``default_arc_port()``           |
+--------------------------------+----------+----------------------------------+
| ``_CoreRetrievalAdapter``      | stateless | ``default_retrieval_port()``     |
+--------------------------------+----------+----------------------------------+
| ``_CoreOutputMutationAdapter`` | stateless | ``default_output_mutation_port()`` |
+--------------------------------+----------+----------------------------------+
| ``_CorePresetEngineAdapter``   | stateful  | ``build_preset_engine_port()``   |
+--------------------------------+----------+----------------------------------+
| ``_CoreS1bPolicyAdapter``      | stateful  | ``build_s1b_policy_port()``      |
+--------------------------------+----------+----------------------------------+
| ``_CoreTranscriptionAdapter``  | stateless | ``default_transcription_port()`` |
+--------------------------------+----------+----------------------------------+

Stateless adapters close over nothing — a single process-wide instance is
sufficient. Stateful adapters close over runtime deps (``ExpressionHistory``,
``judge_client``, ``settings``); they are built once per cog instance.
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any

import structlog

from khimeras_shared.corpus import detect_film_topic
from khimeras_shared.corpus.film_references import build_film_references_block
from personas.insult.core.arc_tracker import ArcState, arc_from_dict, arc_to_dict, build_arc_prompt, update_arc
from personas.insult.core.character import (
    MutationStage,
    build_adaptive_prompt,
    compose_extra_layers,
    deduplicate_opener,
    enforce_length_variation,
    preserve_react_markers,
    strip_echoed_quotes,
)
from personas.insult.core.character import (
    run_pipeline as run_character_pipeline,
)
from personas.insult.core.character.prompts import _format_other_people_block
from personas.insult.core.deep_memory import build_user_memory_block
from personas.insult.core.facts import build_facts_prompt, extract_facts, merge_facts_additive
from personas.insult.core.flows import analyze_flows, build_flow_prompt, detect_lifelessness, validate_flow_adherence
from personas.insult.core.memory_consolidator import (
    consolidate_all_users as consolidate_all_users,
)
from personas.insult.core.memory_consolidator import (
    consolidate_user_facts as consolidate_user_facts,
)
from personas.insult.core.presets import (
    build_preset_prompt,
    build_vulnerable_overlay_prompt,
    classify_preset,
    is_vulnerable_overlay_selection,
)
from personas.insult.core.presets_llm import classify_preset_llm
from personas.insult.core.stance_log import StanceExtraction, build_stance_prompt, extract_stances

if TYPE_CHECKING:
    from personas.insult.cogs.chat.capability_ports import PolicyBundle, PresetEngineResult
    from personas.insult.core.contracts import PresetSelection
    from personas.insult.core.contracts.flows import FlowAnalysis

log = structlog.get_logger()


class _CoreArcAdapter:
    """Adapts the ``insult.core.arc_tracker`` module to the ``ArcPort`` Protocol.

    Sole owner of ``ArcState`` on the pipeline side: the values returned by
    ``load``/``advance`` are opaque carries to the caller (see the opacity
    invariant on the Protocol).
    """

    def load(self, raw: dict | None) -> ArcState:
        return arc_from_dict(raw) if raw else ArcState()

    def phase(self, arc: ArcState) -> str:
        return arc.phase

    def render_block(self, arc: ArcState) -> str:
        return build_arc_prompt(arc)

    def advance(self, arc: ArcState, *, disclosure_severity: int, user_state: str, preset_mode: str) -> ArcState:
        return update_arc(
            arc,
            disclosure_severity=disclosure_severity,
            user_state=user_state,
            preset_mode=preset_mode,
        )

    def dump(self, arc: ArcState) -> dict:
        return arc_to_dict(arc)


class _CoreStanceAdapter:
    """Adapts the ``insult.core.stance_log`` module to the ``StancePort`` Protocol."""

    def render_block(self, stances: list[dict]) -> str:
        return build_stance_prompt(stances)

    def derive(self, response_text: str, assertion_density: float, timestamp: float) -> StanceExtraction:
        return extract_stances(response_text, assertion_density, timestamp)


class _CoreFactsAdapter:
    """Adapts the ``insult.core.facts`` module to the ``FactsPort`` Protocol."""

    def render_block(self, user_name: str, facts: list[dict]) -> str:
        return build_facts_prompt(user_name, facts)

    @property
    def extract_fn(self):
        return extract_facts

    @property
    def merge_fn(self):
        return merge_facts_additive


_LATE_PRESET_TASKS: set[asyncio.Task] = set()


def _observe_late_preset(task: asyncio.Task, started: float, regex_preset: Any, timeout_s: float) -> None:
    """Let a timed-out preset classification finish, and log what it cost and said.

    The old code called ``task.cancel()`` here. But the Haiku was ALREADY paid by
    then: ``/v1/judge`` spawns a Node subprocess per call, so by the time our
    ceiling fires the runner is mid-generation. Cancelling threw away a result we
    had bought, and — worse — left `preset_llm_timeout_fallback` logging only the
    ceiling, never the latency it was exceeded by. 210 of 219 prod turns fell back
    to regex and NOBODY could tell whether the ceiling was off by 50ms or by 5s.

    So: observe instead of cancel. Costs nothing extra, and answers the only two
    questions that decide the ceiling's fate — how long it really takes, and
    whether the LLM would have classified this turn differently from the regex.
    """
    _LATE_PRESET_TASKS.add(task)

    def _done(finished: asyncio.Task) -> None:
        _LATE_PRESET_TASKS.discard(finished)
        if finished.cancelled():
            return
        exc = finished.exception()
        if exc is not None:
            log.warning("preset_llm_late_failed", error=type(exc).__name__)
            return
        late = finished.result()
        log.info(
            "preset_llm_late_result",
            latency_ms=int((time.monotonic() - started) * 1000),
            timeout_ms=int(timeout_s * 1000),
            llm_mode=late.mode.value if late is not None else None,
            regex_mode=regex_preset.mode.value,
            would_have_diverged=bool(late is not None and late.mode != regex_preset.mode),
        )

    task.add_done_callback(_done)


class _CorePresetEngineAdapter:
    """Adapts the preset classification stack (``insult.core.presets`` +
    ``insult.core.presets_llm``) to the ``PresetEnginePort`` Protocol.

    NOT a stateless singleton like the other adapters: it is constructed at
    the composition root WITH its runtime deps (the judge client and the
    settings handle), because the LLM strategy needs both and neither exists
    at import time. The flag/model/timeout are read per-call (parity with
    the inline implementation: a settings change needs no rewire).

    Encapsulates the dual-strategy arbitration the pipeline must not see:
    LLM attempt (timeout + cancel) → regex fallback, permanent regex
    shadow-run, divergence telemetry — same event names as the inline
    stage-08 block this replaces (``preset_llm_timeout_fallback``,
    ``preset_llm_task_failed_fallback``, ``preset_llm_regex_divergence``).
    """

    def __init__(self, judge_client: Any, settings: Any) -> None:
        self._judge = judge_client
        self._settings = settings

    async def resolve(self, text: str, recent: list[dict], user_facts: list[dict]) -> PresetEngineResult:
        # Deferred import: a module-level `from personas.insult.cogs.chat...` here is
        # circular — importing any insult.cogs.chat submodule runs the cogs
        # package __init__, which imports cog.py, which imports THIS module.
        # By first resolve() call every package is fully initialized.
        from personas.insult.cogs.chat.capability_ports import PresetEngineResult

        # Shadow-run the regex classifier ALWAYS so we can detect LLM/regex
        # divergence (F5 hybrid recommendation). Cost is ~0.1ms vs the Haiku
        # 300ms — trivial. The regex is also the fallback when llm_preset is
        # None. Pure regex, no I/O: if THIS raises it is a code bug and it
        # propagates loud (same behavior as the inline version).
        regex_preset = classify_preset(text, recent, user_facts)

        llm_preset = None
        classifier_source = "regex"
        classifier_ms = 0
        if getattr(self._settings, "preset_classifier_llm_enabled", False) and self._judge is not None:
            classifier_start = time.monotonic()
            timeout_s = float(getattr(self._settings, "preset_classifier_timeout_ms", 1500)) / 1000.0
            task = asyncio.create_task(
                classify_preset_llm(
                    text,
                    recent,
                    user_facts,
                    self._judge,
                    model=getattr(self._settings, "preset_classifier_model", "claude-haiku-4-5-20251001"),
                )
            )
            try:
                llm_preset = await asyncio.wait_for(task, timeout=timeout_s)
            except TimeoutError:
                log.warning("preset_llm_timeout_fallback", timeout_s=timeout_s)
                _observe_late_preset(task, classifier_start, regex_preset, timeout_s)
                llm_preset = None
            except Exception:
                log.exception("preset_llm_task_failed_fallback")
                llm_preset = None
            classifier_ms = int((time.monotonic() - classifier_start) * 1000)
            if llm_preset is not None:
                classifier_source = "llm"

        selection = llm_preset if llm_preset is not None else regex_preset

        if llm_preset is not None and llm_preset.mode != regex_preset.mode:
            log.info(
                "preset_llm_regex_divergence",
                llm_mode=llm_preset.mode.value,
                regex_mode=regex_preset.mode.value,
                llm_reason=llm_preset.reason,
                regex_reason=regex_preset.reason,
                llm_modifiers=[m.value for m in llm_preset.modifiers],
                regex_modifiers=[m.value for m in regex_preset.modifiers],
            )

        overlay = is_vulnerable_overlay_selection(selection)
        parts = [build_preset_prompt(selection)]
        if overlay:
            parts.append(build_vulnerable_overlay_prompt())
        return PresetEngineResult(
            selection=selection,
            classifier_source=classifier_source,
            classifier_ms=classifier_ms,
            vulnerable_overlay=overlay,
            guidance_block="\n\n".join(p for p in parts if p),
        )


class _CoreS1bPolicyAdapter:
    """Adapts the pre-LLM behavioral stack (``insult.core.character`` prompts
    + ``insult.core.flows``) to the ``S1bPolicyPort`` Protocol.

    Constructed WITH the anti-repetition ledger (``ExpressionHistory``) — the
    state stays host-owned (born in ``app.Container``, forwarded by the cog);
    the capability only consults it, exactly as the inline stage-08 calls did.

    Pure computation throughout (no I/O): same call sequence, same renders,
    same internal log events (``preset_classified`` from prompts.py,
    ``flow_*`` from the analyzers) as the inline block this replaces — zero
    behavior change, KQL continuity.
    """

    def __init__(self, expression_history: Any) -> None:
        self._expression_history = expression_history

    def compose(
        self,
        *,
        base_prompt: str,
        profile: Any,
        context_len: int,
        preset: PresetSelection,
        text: str,
        recent: list[dict],
        user_facts: list[dict],
        context_key: str,
        server_pulse: str,
        recent_response_lengths: list[int],
        arc_block: str,
        stance_block: str,
        facts_block: str,
        other_participants_facts: dict[str, list[dict]] | None,
        serenityops_snapshot: dict | None,
        serenityops_user_name: str,
    ) -> PolicyBundle:
        # Deferred import: module-level `from personas.insult.cogs.chat...` is circular
        # (cogs __init__ → cog.py → THIS module) — same shape as the Preset
        # Engine adapter above. By first compose() call everything is loaded.
        from personas.insult.cogs.chat.capability_ports import PolicyBundle

        system_prompt, effective_preset = build_adaptive_prompt(
            base_prompt,
            profile,
            context_len,
            preset=preset,
            current_message=text,
            recent_messages=recent,
            user_facts=user_facts,
            server_pulse=server_pulse,
            recent_response_lengths=recent_response_lengths,
        )
        flow_analysis = analyze_flows(text, recent, effective_preset, self._expression_history, context_key)
        flow_guidance = build_flow_prompt(flow_analysis)
        composed = compose_extra_layers(
            system_prompt,
            flow_prompt=flow_guidance,
            arc_prompt=arc_block,
            stance_prompt=stance_block,
            facts_prompt=facts_block,
            other_participants_facts=other_participants_facts,
            serenityops_snapshot=serenityops_snapshot,
            serenityops_user_name=serenityops_user_name,
        )
        return PolicyBundle(
            system_prompt=composed,
            flow_guidance=flow_guidance,
            flow_analysis=flow_analysis,
            preset=effective_preset,
        )

    def other_people_block(self, facts: dict[str, list[dict]]) -> str:
        return _format_other_people_block(facts)

    def assess_adherence(self, response: str, flow_analysis: FlowAnalysis) -> dict:
        return validate_flow_adherence(response, flow_analysis)

    def assess_lifelessness(self, response: str, user_text: str) -> dict:
        return detect_lifelessness(response, user_text)


class _CoreOutputMutationAdapter:
    """Adapts the post-LLM mutation stack (``insult.core.character`` engine +
    mutators, host marker strippers) to the ``OutputMutationPort`` Protocol.

    Owns the pipeline ORDER and the shrink guardrails as internal policy —
    same stages, same ``max_shrink_pct``/``on_violation``/``must_preserve``,
    same per-stage telemetry (``_structlog_sink`` events) as the inline
    block it replaces. Stateless: all turn inputs arrive per call.
    """

    async def mutate(
        self,
        raw_text: str,
        *,
        user_text: str,
        recent_response_lengths: list[int],
        recent_openers: list[str],
    ) -> str:
        # Deferred import: the invite/remember strippers live host-side
        # (insult.cogs.chat.{invites,remembers}) and a module-level import
        # here is circular (cogs __init__ → cog.py → THIS module) — same
        # shape as the Preset Engine / S1b adapters above.
        from khimeras_shared.reactions import strip_reactions
        from personas.insult.cogs.chat.invites import strip_invites
        from personas.insult.cogs.chat.remembers import strip_remembers
        from personas.insult.cogs.chat.reminds import strip_reminds

        return await run_character_pipeline(
            [
                MutationStage(
                    name="strip_echoed_quotes",
                    apply=lambda t, _ctx, _user_text=user_text: strip_echoed_quotes(t, _user_text),
                    max_shrink_pct=0.30,
                    on_violation="skip_stage",
                ),
                MutationStage(
                    name="enforce_length_variation",
                    apply=lambda t, _ctx, _lens=recent_response_lengths: enforce_length_variation(t, _lens),
                    max_shrink_pct=0.50,
                    on_violation="skip_stage",
                ),
                MutationStage(
                    name="deduplicate_opener",
                    apply=lambda t, _ctx, _openers=recent_openers: deduplicate_opener(t, _openers),
                    max_shrink_pct=0.30,
                    must_preserve=[preserve_react_markers],
                    on_violation="skip_stage",
                ),
                MutationStage(
                    name="strip_reactions",
                    apply=lambda t, _ctx: strip_reactions(t),
                    max_shrink_pct=None,
                    on_violation="skip_stage",
                ),
                MutationStage(
                    name="strip_remembers",
                    apply=lambda t, _ctx: strip_remembers(t),
                    max_shrink_pct=None,
                    on_violation="skip_stage",
                ),
                MutationStage(
                    name="strip_reminds",
                    apply=lambda t, _ctx: strip_reminds(t),
                    max_shrink_pct=None,
                    on_violation="skip_stage",
                ),
                MutationStage(
                    name="strip_invites",
                    apply=lambda t, _ctx: strip_invites(t),
                    max_shrink_pct=None,
                    on_violation="skip_stage",
                ),
            ],
            raw_text,
            ctx={},
        )


class _CoreRetrievalAdapter:
    """Adapts ``insult.core.deep_memory`` to the ``RetrievalPort`` Protocol.

    Owns the capability's best-effort contract: every method catches, logs
    (same event names the inline stages helpers emitted, for KQL continuity)
    and returns ``None`` — a retrieval failure NEVER breaks the turn. The
    rendering policy itself (similarity floor, char budget, headers) lives in
    the domain service builders; this adapter only composes the lexical film
    gate and the failure boundary.
    """

    async def user_memory_block(self, *, user_id: str, text: str | None) -> str | None:
        try:
            return await build_user_memory_block(user_id=user_id, text=text)
        except Exception as e:  # retrieval is best-effort; never break the turn
            log.warning("deep_memory_prefetch_failed", user_id=user_id, error=str(e))
            return None

    async def film_references_block(self, text: str | None) -> str | None:
        # Topic-gated so off-topic turns don't pay an embed call.
        if not detect_film_topic(text or ""):
            return None
        try:
            return await build_film_references_block(text)
        except Exception as e:  # retrieval is best-effort; never break the turn
            log.warning("film_references_prefetch_failed", error=str(e))
            return None


# Stateless — a single shared instance is sufficient and avoids per-turn churn.
_FACTS_PORT = _CoreFactsAdapter()
_STANCE_PORT = _CoreStanceAdapter()
_ARC_PORT = _CoreArcAdapter()
_RETRIEVAL_PORT = _CoreRetrievalAdapter()
_OUTPUT_MUTATION_PORT = _CoreOutputMutationAdapter()


def default_output_mutation_port() -> _CoreOutputMutationAdapter:
    """Return the process-wide OutputMutationPort adapter for the turn pipeline."""
    return _OUTPUT_MUTATION_PORT


def default_arc_port() -> _CoreArcAdapter:
    """Return the process-wide ArcPort adapter for the turn pipeline."""
    return _ARC_PORT


def default_facts_port() -> _CoreFactsAdapter:
    """Return the process-wide FactsPort adapter for the turn pipeline."""
    return _FACTS_PORT


def default_stance_port() -> _CoreStanceAdapter:
    """Return the process-wide StancePort adapter for the turn pipeline."""
    return _STANCE_PORT


def default_retrieval_port() -> _CoreRetrievalAdapter:
    """Return the process-wide RetrievalPort adapter for the turn pipeline."""
    return _RETRIEVAL_PORT


def build_s1b_policy_port(expression_history: Any) -> _CoreS1bPolicyAdapter:
    """Build the S1bPolicyPort adapter with its runtime dep.

    Like the Preset Engine, NOT a stateless singleton: it closes over the
    anti-repetition ledger (``ExpressionHistory``), which is born in
    ``app.Container`` — call this once where the cog receives the handle."""
    return _CoreS1bPolicyAdapter(expression_history)


def build_preset_engine_port(judge_client: Any, settings: Any) -> _CorePresetEngineAdapter:
    """Build the PresetEnginePort adapter with its runtime deps.

    Unlike the stateless ``default_*`` singletons, this one closes over the
    judge client and the settings handle — call it once where they are born
    (the cog wires the Container's handles at construction time)."""
    return _CorePresetEngineAdapter(judge_client, settings)


def build_host_degrader_port(settings: Any) -> Any | None:
    """Build the HostDegraderPort (gpt-4.1 honest-degradation) — or ``None``.

    PR-4b slice 3, INERT by default. Returns ``None`` unless
    ``settings.host_router_enabled`` is True; the cog forwards that None onto
    ``TurnRuntimeDeps.host_degrader``, and the honest-degradation tail keeps using
    the static in-character notice. The ``demux_ai`` import is DEFERRED inside the
    enabled branch so the host router + its heavy ``fi_runner`` backend are never
    loaded when the flag is off — the whole gpt-4.1 path stays cold in prod.

    Typed ``Any`` (like ``create_memory_store``) so this composition root is the
    ONE place that touches ``demux_ai.host_degrader``; hosts hold the handle as a
    ``HostDegraderPort | None`` without importing the concrete. The concrete
    ``HostDegrader`` already satisfies the Protocol, so no adapter is needed."""
    if not getattr(settings, "host_router_enabled", False):
        # Decision point: log the inert state so a deploy's logs reveal at a
        # glance that the gpt-4.1 degrader is NOT wired (no spend, no router).
        log.info("host_degrader_disabled")
        return None
    # Enabled boot path: constructing HostDegrader → HostRouterLLM → CodexBackend
    # is a blocking model-client setup at cog __init__ time. Bracket it so a hang
    # or crash here is never a silent boot blind spot (boot-zombie doctrine).
    log.info("host_degrader_building")  # pragma: no cover
    from demux_ai.host_degrader import HostDegrader  # pragma: no cover

    degrader = HostDegrader()  # pragma: no cover
    log.info("host_degrader_built")  # pragma: no cover
    return degrader  # pragma: no cover


def build_llm_shadow_router(settings: Any) -> Any | None:
    """Build the gpt-4.1 LLM shadow router callable — or ``None`` (HOST 5/6 slice A.2).

    Returns the bound ``LLMShadowRouter.route`` (async ``str -> LLMShadowDecision``)
    only when ``settings.llm_shadow_router_enabled`` is True; otherwise ``None`` and
    the bind-identity stage runs no LLM shadow. Unlike ``build_shadow_router`` (free,
    default ON), this one is default OFF: constructing the router builds
    ``HostRouterLLM`` → ``CodexBackend`` (a blocking model-client setup) and every
    ``route`` call SPENDS gpt-4.1 — so the build is bracketed by boot logs
    (boot-zombie doctrine) and the ``demux_ai`` import is DEFERRED inside the enabled
    branch so the heavy ``fi_runner`` backend stays cold in prod when off. Typed
    ``Any`` so this composition root is the ONE place that touches the concrete; the
    cog forwards the handle onto ``TurnRuntimeDeps.llm_shadow_route``."""
    if not getattr(settings, "llm_shadow_router_enabled", False):
        log.info("llm_shadow_router_disabled")
        return None
    transport = getattr(settings, "llm_shadow_transport", "agentic")  # pragma: no cover
    log.info("llm_shadow_router_building", transport=transport)  # pragma: no cover
    if transport == "direct":  # pragma: no cover
        from demux_ai.llm_shadow_router import DirectAzureLLMRouter

        router: Any = DirectAzureLLMRouter()
    else:  # pragma: no cover
        from demux_ai.llm_shadow_router import LLMShadowRouter

        router = LLMShadowRouter()
    log.info("llm_shadow_router_built", transport=transport)  # pragma: no cover
    return router.route  # pragma: no cover


def build_router_budget(settings: Any) -> Any | None:
    """Build the gpt-4.1 router's weekly spend cap — or ``None`` (HOST 5/6).

    Returns a process-level ``RouterBudget`` (single-replica → one event-loop owns
    the counter) ONLY when a gpt-4.1 router is enabled (shadow OR cutover), since
    the cap only has meaning where there is spend to cap. ``$5/week`` by default
    (Bernard, 2026-06-21), overridable via ``ROUTER_WEEKLY_BUDGET_USD``. ``demux_ai``
    import deferred so the composition root stays the one place that touches it; the
    cog forwards the handle onto ``TurnRuntimeDeps.router_budget`` and the router
    stages consult it."""
    if not (
        getattr(settings, "llm_shadow_router_enabled", False) or getattr(settings, "llm_router_cutover_enabled", False)
    ):
        return None
    from demux_ai.router_budget import RouterBudget

    budget = RouterBudget()
    log.info("router_budget_built", cap_usd=budget.cap_usd)
    return budget


def build_llm_router_cutover_route(settings: Any) -> Any | None:
    """Build the LLM router CUTOVER callable — or ``None`` (HOST 5/6 slice C).

    Returns the bound ``DirectAzureLLMRouter.route`` (async
    ``(text, context) -> LLMShadowDecision``) only when
    ``settings.llm_router_cutover_enabled`` is True. Always the DIRECT transport:
    the decision now sits ON the turn's critical path, so the ~9.5k-token agentic
    harness (multi-second codex call) is disqualified — a one-word classification
    must cost hundreds of tokens and land inside the cutover timeout. The
    ``demux_ai`` import is DEFERRED inside the enabled branch; the cog forwards
    the handle onto ``TurnRuntimeDeps.llm_router_cutover_route``."""
    if not getattr(settings, "llm_router_cutover_enabled", False):
        log.info("llm_router_cutover_disabled")
        return None
    from demux_ai.llm_shadow_router import DirectAzureLLMRouter

    router = DirectAzureLLMRouter()
    log.info("llm_router_cutover_built", transport="direct")
    return router.route


# ---------------------------------------------------------------------------
# Governance bridges — app.py / __main__.py are host-facing and must not
# import personas.insult.core.memory or insult.core.memory_consolidator directly.
# This module is the composition root (not host-facing), so it is the ONE
# sanctioned place to cross that boundary for DI / admin CLI purposes.
# ---------------------------------------------------------------------------


def create_memory_store(postgres_url: str) -> Any:
    """Construct a MemoryStore without exposing the concrete type to hosts.

    Returns an object satisfying ``MemoryLifecyclePort`` (connect/close).
    Typed as ``Any`` so host callers (app.py) can hold the reference in a
    ``MemoryLifecyclePort``-annotated field without importing MemoryStore.
    """
    from personas.insult.core.memory import MemoryStore  # pragma: no cover

    return MemoryStore(postgres_url)  # pragma: no cover


# consolidate_all_users and consolidate_user_facts are re-exported at the top
# import block above so __main__.py can reach them via composition without a
# direct insult.core.memory_consolidator import.


class _CoreTranscriptionAdapter:
    """Adapts ``insult.core.transcribe`` to the ``TranscriptionPort`` Protocol.

    Closes the last ``host → smart`` import-boundary violation:
    ``insult.cogs.chat.voice`` calls ``default_transcription_port().transcribe()``
    instead of importing ``transcribe_voice_message`` directly.
    """

    async def transcribe(
        self,
        audio_data: bytes,
        *,
        base_url: str,
        api_key: str,
        language: str = "es",
        content_type: str = "audio/ogg",
    ) -> str | None:
        from personas.insult.core.transcribe import transcribe_voice_message  # pragma: no cover

        return await transcribe_voice_message(  # pragma: no cover
            audio_data,
            base_url=base_url,
            api_key=api_key,
            language=language,
            content_type=content_type,
        )


_TRANSCRIPTION_PORT = _CoreTranscriptionAdapter()


def default_transcription_port() -> _CoreTranscriptionAdapter:
    """Return the process-wide TranscriptionPort adapter."""
    return _TRANSCRIPTION_PORT
