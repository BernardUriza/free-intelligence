"""Composition seam — wires smart/persona domain services to their host PORTS.

This module is the composition root for the turn-runtime domain ports
(``insult/cogs/chat/ports.py``). It is the ONE place that legitimately imports
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
"""

from __future__ import annotations

from insult.core.arc_tracker import ArcState, arc_from_dict, arc_to_dict, build_arc_prompt, update_arc
from insult.core.facts import build_facts_prompt, extract_facts, merge_facts_additive
from insult.core.stance_log import StanceExtraction, build_stance_prompt, extract_stances


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


# Stateless — a single shared instance is sufficient and avoids per-turn churn.
_FACTS_PORT = _CoreFactsAdapter()
_STANCE_PORT = _CoreStanceAdapter()
_ARC_PORT = _CoreArcAdapter()


def default_arc_port() -> _CoreArcAdapter:
    """Return the process-wide ArcPort adapter for the turn pipeline."""
    return _ARC_PORT


def default_facts_port() -> _CoreFactsAdapter:
    """Return the process-wide FactsPort adapter for the turn pipeline."""
    return _FACTS_PORT


def default_stance_port() -> _CoreStanceAdapter:
    """Return the process-wide StancePort adapter for the turn pipeline."""
    return _STANCE_PORT
