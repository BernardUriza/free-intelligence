"""Turn-runtime CAPABILITY ports — cross-cutting capabilities the pipeline
consumes, not domain read/write facets.

Sibling of ``ports.py`` but intentionally a separate module: ``ports.py``
holds the S2/S5 *domain-service* facets (Facts/Stance/Arc — read-modify-write
cycles owned by one domain service each). The contracts here are transversal
*capabilities* (retrieval today; the Preset Engine later) — they serve many
turn phases and own no per-turn domain state. Mixing the two would dilute the
distinction the seam design already paid for: phases vs nouns, domain
services vs capabilities.

Same composition rule as ``ports.py``: the pipeline (``stages.py``) depends
on these ``Protocol``s and receives a concrete adapter via
``TurnRuntimeDeps``; the adapter is wired in ``insult/composition.py``, the
only module allowed to know both the Protocol and the ``insult.core.*``
implementation behind it (see ``tests/test_arch_import_boundaries.py``).

Design plan: ``.claude/plans/capability_seams_retrieval_preset.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from personas.insult.core.contracts import PresetSelection
    from personas.insult.core.contracts.flows import FlowAnalysis


class RetrievalPort(Protocol):
    """Semantic retrieval as the turn pipeline consumes it (S2 read-only).

    Both methods return a FINISHED system-prompt block (header + bulleted
    chunks) or ``None`` — the rendering policy (similarity floor, char
    budget, authoritative header) is owned by the capability, never by the
    pipeline. Both are best-effort: they NEVER raise; any retrieval failure
    logs and returns ``None`` (no memory this turn, same as pre-v4.3.0).

    - ``user_memory_block``: top chunks from the author's own raw history
      (per-user partition). ``None`` on trivial text, weak hits, or failure.
    - ``film_references_block``: film-theory corpus chunks under the Vultur
      frame. Topic-gated INSIDE the port (lexical ``detect_film_topic``) so
      off-topic turns don't pay an embed call; the pipeline just asks.

    Deliberately NOT a generic ``corpus_block(namespace)``: the film corpus
    is the only namespace the pipeline consumes today. Generalize when the
    second real consumer exists, not before.
    """

    async def user_memory_block(self, *, user_id: str, text: str | None) -> str | None: ...

    async def film_references_block(self, text: str | None) -> str | None: ...


@dataclass(frozen=True)
class PresetEngineResult:
    """What the Preset Engine hands the pipeline for one turn.

    Lives HERE (not in ``insult.core.contracts``) on purpose:
    ``PresetSelection``/``PresetModifier`` are reusable domain vocabulary;
    this is the return shape of one concrete capability — classifier
    telemetry scalars plus a rendered guidance fragment are orchestration
    output, not stable domain vocabulary.

    - ``selection``: the effective classification. It is contracts
      vocabulary, NOT an opaque carry (unlike ``ArcState``) — the pipeline
      may read ``mode``/``modifiers``/``display_label``/``reason`` and pass
      it on to ``build_adaptive_prompt`` / ``analyze_flows`` /
      ``select_model``, all of which already type it.
    - ``classifier_source``: ``"llm"`` or ``"regex"`` — which strategy won.
    - ``classifier_ms``: wall-clock of the LLM attempt (0 when disabled).
    - ``vulnerable_overlay``: whether the selection carries the safety
      overlay (absorbs ``is_vulnerable_overlay_selection``).
    - ``guidance_block``: preset guidance + vulnerability overlay already
      rendered (``""`` when there is nothing to add) — S3 receives
      fragments, not nouns.
    """

    selection: PresetSelection
    classifier_source: str
    classifier_ms: int
    vulnerable_overlay: bool
    guidance_block: str


class PresetEnginePort(Protocol):
    """Preset classification + guidance rendering as ONE logical operation.

    The engine has two internal strategies (LLM judge + rule-based regex);
    NONE of that duality leaks here. Inside ``resolve`` live: the LLM
    attempt with timeout + cancel, the regex fallback, the permanent regex
    shadow-run, and the divergence telemetry (same event names as the
    inline implementation it replaces — KQL continuity).

    Concurrency contract: ``resolve`` is a plain coroutine. The PIPELINE
    owns scheduling — it may start it early with
    ``asyncio.create_task(port.resolve(...))`` and await it stages later to
    overlap the LLM latency with other pre-LLM work. No bespoke
    start/carry/complete API: the carry is a standard ``asyncio.Task``.

    Failure contract: LLM-path failures (timeout, API error, bad JSON)
    NEVER propagate — they fall back to the rule-based classifier. The
    rule-based path is pure regex (no I/O); if it raises, that is a code
    bug and it propagates loud, exactly as the inline version did.
    """

    async def resolve(self, text: str, recent: list[dict], user_facts: list[dict]) -> PresetEngineResult: ...


@dataclass(frozen=True)
class PolicyBundle:
    """What the S1b Policy Engine hands the pipeline for one turn.

    Lives HERE (not in ``insult.core.contracts``) for the same reason as
    ``PresetEngineResult``: it is the return shape of one concrete
    capability, not reusable domain vocabulary.

    - ``system_prompt``: the FULLY composed legacy system prompt (persona +
      time + preset layer + style + flow + arc + stance + facts + serenity +
      other-people). What ``LLMClient.chat`` receives on the legacy path.
    - ``flow_guidance``: the rendered flow-behavioral fragment alone — the
      runner path (``_build_behavioral_guidance``) re-uses it so both paths
      render flows ONCE from the same analysis (no drift, same contract as
      ``PresetEngineResult.guidance_block``).
    - ``flow_analysis``: the 4-flow analysis. Contracts vocabulary
      (``insult.core.contracts.flows``), NOT an opaque carry — the pipeline
      reads its fields for telemetry and forwards it to ``select_model`` /
      stance derive / ``assess_adherence``, all of which already type it.
    - ``preset``: the effective ``PresetSelection`` (passes through the
      pre-resolved Preset Engine selection unchanged; kept in the bundle so
      the pipeline never assumes that invariant).
    """

    system_prompt: str
    flow_guidance: str
    flow_analysis: FlowAnalysis
    preset: PresetSelection


class S1bPolicyPort(Protocol):
    """Behavioral policy/guidance composition as ONE logical operation (S1b).

    Absorbs the pre-LLM half of ``insult.core.character`` (adaptive prompt +
    extra layers) and ALL of ``insult.core.flows`` as the pipeline consumed
    them: classify-aware prompt building, 4-flow analysis, flow guidance
    rendering and layer composition happen INSIDE ``compose``. The pipeline
    supplies pre-rendered domain blocks (arc/stance/facts — its existing
    ports) and receives finished strings; rendering policy is owned by the
    capability. Ground truth + design: ``.claude/plans/s1b_ground_truth.md``.

    The adapter is constructed WITH the anti-repetition ledger
    (``ExpressionHistory``, contracts vocabulary) — the state stays host-owned
    (born in ``app.Container``), the capability only consults it.

    ``assess_adherence`` / ``assess_lifelessness`` are the S5 telemetry facet:
    COSMETIC validators of the port's own analysis (log-feeding dicts, never
    block, never raise into the turn). They live on this port because they
    judge the response against the same ``flow_analysis`` this port produced.

    ``other_people_block`` renders third-party facts for the runner path (S2
    knowledge assembly) — replaces the pipeline's reach into the private
    ``_format_other_people_block`` (same fix-shape as the PR-D header move).

    Everything here is pure computation (no I/O) — sync methods; failures
    propagate loud, exactly as the inline calls did.
    """

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
    ) -> PolicyBundle: ...

    def other_people_block(self, facts: dict[str, list[dict]]) -> str: ...

    def assess_adherence(self, response: str, flow_analysis: FlowAnalysis) -> dict: ...

    def assess_lifelessness(self, response: str, user_text: str) -> dict: ...


class OutputMutationPort(Protocol):
    """Post-LLM text mutation as ONE logical operation (S4).

    Absorbs the post-LLM half of ``insult.core.character``: the guardrailed
    mutation pipeline (echo-strip → length variation → opener dedup →
    marker stripping) the stage ran inline. The pipeline ORDER, the shrink
    guardrails (``max_shrink_pct`` / ``on_violation`` / ``must_preserve``)
    and the per-stage telemetry are internal policy of the adapter — the
    pipeline hands raw model text in and receives the deliverable text out.

    The ``[REACT:]`` / ``[REMEMBER:]`` PARSERS are NOT behind this port —
    parse_reactions/parse_remembers stay host-side in the stage (they read
    the raw text BEFORE mutation; the port only owns the mutation chain,
    which includes stripping those markers from the visible text).

    The mutators honor `.claude/rules/robustness.md` (quote-adjacency,
    marker rescue, resistance tests) — those contracts travel WITH the
    capability, enforced by the parity tests in
    ``tests/test_output_mutation_port.py``.

    Pure text computation (no I/O): failures propagate loud, exactly as the
    inline pipeline did (each stage individually degrades via its own
    ``on_violation="skip_stage"`` guardrail, never the whole call).
    """

    async def mutate(
        self,
        raw_text: str,
        *,
        user_text: str,
        recent_response_lengths: list[int],
        recent_openers: list[str],
    ) -> str: ...
