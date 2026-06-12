"""Turn-runtime PORTS — the contracts the pipeline depends on, not the impls.

The turn pipeline (``stages.py``) is host-facing plumbing: it must NOT import
the smart/persona domain services directly (see
``tests/test_arch_import_boundaries.py``). Instead it depends on these
``Protocol``s and receives a concrete adapter via ``TurnRuntimeDeps``. The
concrete adapters live in the smart-side composition seam
(``insult/composition.py``), which is the only place allowed to know both the
Protocol and the underlying ``insult.core.*`` module.

Each domain service is a read-modify-write cycle split across two turn phases:
S2 (render the per-turn block, pre-LLM) and S5 (derive + persist, post-LLM).
A single port per service covers BOTH facets — designing the read side without
its write side is what produced the coupling these ports pay down.

Design plan: ``.claude/plans/s2_s5_domain_facets_multipr.md``.
"""

from __future__ import annotations

from typing import Any, Protocol


class ArcPort(Protocol):
    """The conversational-arc domain service as the turn pipeline consumes it.

    OPACITY INVARIANT (the reason this port exists): ``ArcState`` is NOT a
    public contract between phases. The pipeline transports the value returned
    by ``load``/``advance`` as an opaque carry — it must never read or mutate
    its fields. Any scalar the pipeline needs (e.g. the phase label for
    telemetry) is exposed as a port method. The resistance test fails on any
    ``*.arc_state.<attr>`` access in stages.

    - ``load`` (S2/pre-LLM): raw persisted dict (or None) → opaque arc carry.
    - ``phase``: the arc's phase label, for telemetry only.
    - ``render_block`` (S2): system-prompt section for the current arc.
    - ``advance`` (S5): fold the turn's signals into the next arc carry.
    - ``dump`` (S5): opaque carry → plain dict for the memory upsert.
    """

    def load(self, raw: dict | None) -> Any: ...

    def phase(self, arc: Any) -> str: ...

    def render_block(self, arc: Any) -> str: ...

    def advance(self, arc: Any, *, disclosure_severity: int, user_state: str, preset_mode: str) -> Any: ...

    def dump(self, arc: Any) -> dict: ...


class StancePort(Protocol):
    """The stance-log domain service as the turn pipeline consumes it.

    - ``render_block`` (S2): build the system-prompt section with the bot's
      prior positions. Replaces a direct ``build_stance_prompt`` call.
    - ``derive`` (S5): extract stated positions from the completed response
      (returns the core ``StanceExtraction``, opaque to the pipeline beyond
      iterating ``.entries``). Replaces the inline ``extract_stances`` import.

    Persistence (``get_stances`` / ``store_stance``) stays on the ``memory``
    store — the data plane is already a port; this port owns only the smart
    render + derivation logic.
    """

    def render_block(self, stances: list[dict]) -> str: ...

    def derive(self, response_text: str, assertion_density: float, timestamp: float) -> Any: ...


class FactsPort(Protocol):
    """The facts domain service as the turn pipeline consumes it.

    - ``render_block`` (S2): build the system-prompt section listing the
      author's known facts. Replaces a direct ``build_facts_prompt`` call.
    - ``extract_fn`` / ``merge_fn`` (S5): the callables injected into the
      background fact-extraction task — kept as attributes so the existing
      ``extract_user_facts(..., extract_facts_fn=, merge_facts_fn=)`` call
      site is unchanged in behavior.
    """

    def render_block(self, user_name: str, facts: list[dict]) -> str: ...

    @property
    def extract_fn(self) -> Any: ...

    @property
    def merge_fn(self) -> Any: ...
