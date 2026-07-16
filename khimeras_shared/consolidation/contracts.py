"""Data contracts of a consolidation run: the audit ops, the per-user report,
and the persona-side hooks protocol.

Everything persona-flavored (sleep coordination, the dream diary, any voice)
lives behind ``ConsolidationHooks`` so the orchestrator stays neutral and
``khimeras_shared`` never imports a persona. Insult implemented them with
siesta + dream diary; ALICE uses ``NoopConsolidationHooks``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class FactOperation:
    """One row to write to fact_consolidation_log + apply to user_facts."""

    op: str
    fact_id_before: int | None = None
    fact_id_after: int | None = None
    fact_text_before: str | None = None
    fact_text_after: str | None = None
    reason: str = ""


@dataclass
class ConsolidationReport:
    """Summary of one consolidation run for a single user."""

    user_id: str
    facts_in: int
    facts_out: int
    ops: list[FactOperation] = field(default_factory=list)
    duration_ms: int = 0
    haiku_input_tokens: int = 0
    haiku_output_tokens: int = 0
    error: str | None = None

    def counts_by_op(self) -> dict[str, int]:
        out = {"NOOP": 0, "DELETE": 0, "UPDATE": 0, "ADD": 0}
        for o in self.ops:
            out[o.op] = out.get(o.op, 0) + 1
        return out


def _op_factory(
    op: str,
    fact_id_before: int | None,
    fact_id_after: int | None,
    text_before: str | None,
    text_after: str | None,
    reason: str,
) -> FactOperation:
    """Bridge between FactsRepository.apply_consolidation_plan (which doesn't
    know about FactOperation) and this package's dataclass."""
    return FactOperation(
        op=op,
        fact_id_before=fact_id_before,
        fact_id_after=fact_id_after,
        fact_text_before=text_before,
        fact_text_after=text_after,
        reason=reason,
    )


class ConsolidationHooks(Protocol):
    """Persona-side hooks the neutral orchestrator calls at run boundaries."""

    async def on_run_started(self, *, total_users: int, dry_run: bool) -> object | None:
        """Return an opaque marker (passed back to progress hooks), or None."""
        ...

    async def on_user_progress(
        self, *, marker: object, total_users: int, processed_users: int, current_user_id: str
    ) -> None:
        """Called before each user's consolidation when a marker is active."""
        ...

    async def after_user(self, *, user_id: str) -> None:
        """Called after each user's consolidation succeeds (real runs only)."""
        ...

    async def on_pre_finish(self, *, marker: object, total_users: int) -> None:
        """Called once after the loop, before hard-purge (real runs only)."""
        ...

    async def write_diary(self, reports: list[ConsolidationReport], *, memory, llm, model, name_resolver) -> None:
        """Called once at the end with all reports (real runs only)."""
        ...

    async def on_run_finished(self) -> None:
        """Called in ``finally`` on real runs — never leaves the bot asleep."""
        ...


class NoopConsolidationHooks:
    """Default no-op hooks — for personas without sleep/diary (e.g. ALICE) and
    for callers that want the bare capability with no persona side effects."""

    async def on_run_started(self, *, total_users: int, dry_run: bool) -> object | None:
        return None

    async def on_user_progress(
        self, *, marker: object, total_users: int, processed_users: int, current_user_id: str
    ) -> None:
        return None

    async def after_user(self, *, user_id: str) -> None:
        return None

    async def on_pre_finish(self, *, marker: object, total_users: int) -> None:
        return None

    async def write_diary(self, reports: list[ConsolidationReport], *, memory, llm, model, name_resolver) -> None:
        return None

    async def on_run_finished(self) -> None:
        return None
