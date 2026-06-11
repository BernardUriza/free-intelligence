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
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from insult.core.contracts import PresetSelection


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
