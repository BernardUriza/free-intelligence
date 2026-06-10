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
