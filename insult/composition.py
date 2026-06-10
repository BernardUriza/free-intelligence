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

from insult.core.facts import build_facts_prompt, extract_facts, merge_facts_additive


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


def default_facts_port() -> _CoreFactsAdapter:
    """Return the process-wide FactsPort adapter for the turn pipeline."""
    return _FACTS_PORT
