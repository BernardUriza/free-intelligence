"""Value types for ``fi_core.memory``.

Three dataclasses:

- :class:`Fact` — one atomic fact about a principal (user, patient,
  account, whatever the consumer scopes by). Mirrors the row shape of
  the ``user_facts`` table in discord-bot's production schema, with
  ``user_id`` generalized to ``principal_id``.
- :class:`FactSource` — provenance tier. The discord-bot distinction
  between ``auto``-extracted (wiped on every re-extraction),
  ``manual``-curated (never wiped), and ``agent``-emitted (survives
  re-extraction) generalizes cleanly across consumers.
- :class:`ConsolidationOp` — one applied operation from a Mem0-style
  consolidation pass. Pairs with ``fi_core.persona.mcp_server.
  parse_consolidation_result``: the parser produces plan dicts, the
  store applies them and emits ``ConsolidationOp`` audit rows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class FactSource(str, Enum):
    """Provenance tier for a fact.

    The distinction matters because :meth:`MemoryStore.save_facts`
    semantics differ by source:

    - :attr:`AUTO` is wiped on every re-extraction (LLM produces a
      fresh full snapshot per pass — older auto facts are stale).
    - :attr:`MANUAL` is preserved across re-extractions. Operator or
      cross-user curated entries that should never die from a fact
      pipeline omission.
    - :attr:`AGENT` is the "remember this" marker emitted in-band by
      the persona itself. Survives ``save_facts(auto)`` like MANUAL but
      stays distinguishable in audit logs.
    """

    AUTO = "auto"
    MANUAL = "manual"
    AGENT = "agent"


@dataclass(frozen=True, slots=True)
class Fact:
    """One atomic fact about a principal.

    Maps 1:1 to a row in the canonical ``principal_facts`` table that
    ``fi_core.memory.stores.PgMemoryStore`` writes. ``id`` is None for
    facts not yet persisted (e.g. an in-flight ``add_fact`` call).
    """

    fact: str
    principal_id: str
    category: str = "general"
    source: FactSource = FactSource.AUTO
    updated_at: float = 0.0
    id: int | None = None
    deleted_at: float | None = None


@dataclass(frozen=True, slots=True)
class ConsolidationOp:
    """One audit row produced by applying a consolidation plan.

    Returned by :meth:`MemoryStore.apply_consolidation_plan`. The op
    string is one of NOOP / DELETE / UPDATE / ADD; the
    ``fact_id_before`` / ``fact_id_after`` pair encodes the lifecycle
    of the row (e.g. UPDATE merges 3 ids into 1 → 3 ops with the same
    ``fact_id_after``, distinct ``fact_id_before``).
    """

    op: str  # NOOP | DELETE | UPDATE | ADD
    fact_id_before: int | None = None
    fact_id_after: int | None = None
    fact_text_before: str | None = None
    fact_text_after: str | None = None
    reason: str = ""
    run_ts: float = 0.0


@dataclass(slots=True)
class ConsolidationReport:
    """Summary of one consolidation run for a single principal.

    Returned by ``FactConsolidator.consolidate_principal``. Aggregates
    the per-op trail into rollup counts plus error / timing metadata.
    """

    principal_id: str
    facts_in: int
    facts_out: int
    ops: list[ConsolidationOp] = field(default_factory=list)
    duration_ms: int = 0
    error: str | None = None

    def counts_by_op(self) -> dict[str, int]:
        """Return ``{op_kind: count}`` for all applied operations.

        Useful for telemetry — Mem0-style consolidators care about the
        UPDATE / DELETE / NOOP ratios, not the per-op details.
        """
        out = {"NOOP": 0, "DELETE": 0, "UPDATE": 0, "ADD": 0}
        for o in self.ops:
            out[o.op] = out.get(o.op, 0) + 1
        return out
