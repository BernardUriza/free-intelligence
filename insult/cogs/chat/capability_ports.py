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

from typing import Protocol


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
