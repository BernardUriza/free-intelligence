"""Insult's ConsolidationHooks — the persona voice/runtime behind the neutral job.

PR-3d split: the neutral consolidation core + orchestrator live in
``khimeras_shared.memory_consolidation``. Everything persona-flavored about a
run lives HERE: the siesta sleep-coordination (the bot silences itself while the
consolidator runs to avoid the shared-blob mtime race) and the dream diary
(Insult's voice). The orchestrator calls these hooks at run boundaries; this is
the ONLY place that knows siesta + the diary generator.

Imports are lazy (inside methods) to mirror the original module's pattern and to
keep this import-light + cycle-free.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import structlog

from khimeras_shared.memory_consolidation import ConsolidationReport

if TYPE_CHECKING:
    from datetime import datetime

log = structlog.get_logger()


class InsultConsolidationHooks:
    """Siesta markers + dream diary + incremental deep_memory ingest."""

    def __init__(self, *, write_diary: bool = True) -> None:
        self._write_diary = write_diary

    async def on_run_started(self, *, total_users: int, dry_run: bool) -> object | None:
        """Place the siesta start marker (real runs only).

        Returns the started_at timestamp (UTC datetime) so per-user progress
        calls can reference it without re-reading the blob. ``None`` means "no
        marker placed" — happens on dry-run or when Azure isn't wired up
        locally; either way the orchestrator skips per-progress updates.
        """
        if dry_run:
            return None
        from datetime import UTC, datetime

        from personas.insult.core.siesta import mark_started

        placed = await mark_started(total_users)
        return datetime.now(UTC) if placed else None

    async def on_user_progress(
        self, *, marker: object, total_users: int, processed_users: int, current_user_id: str
    ) -> None:
        from personas.insult.core.siesta import SiestaPhase, mark_progress

        await mark_progress(
            phase=SiestaPhase.LIGHT,
            started_at=cast("datetime", marker),
            total_users=total_users,
            processed_users=processed_users,
            current_user_id=current_user_id,
        )

    async def after_user(self, *, user_id: str) -> None:
        # DM-6: incremental deep_memory ingest. Runs AFTER fact consolidation
        # succeeds, so the embedding budget only gets spent on users whose facts
        # the judge accepted. Best-effort — the helper logs and returns 0 on any
        # failure, never raises, so a flaky Azure OpenAI call can't poison the run.
        from personas.insult.core.deep_memory import ingest_new_user_messages

        inserted = await ingest_new_user_messages(user_id)
        if inserted:
            log.info("consolidator_deep_memory_ingested", user_id=user_id, new_chunks=inserted)

    async def on_pre_finish(self, *, marker: object, total_users: int) -> None:
        from personas.insult.core.siesta import SiestaPhase, mark_progress

        await mark_progress(
            phase=SiestaPhase.REM,
            started_at=cast("datetime", marker),
            total_users=total_users,
            processed_users=total_users,
        )

    async def write_diary(self, reports: list[ConsolidationReport], *, memory, llm, model, name_resolver) -> None:
        if not self._write_diary:
            return
        from personas.insult.core.siesta.diary.generator import write_diary_for_run

        await write_diary_for_run(reports, memory=memory, llm=llm, model=model, name_resolver=name_resolver)

    async def on_run_finished(self) -> None:
        from personas.insult.core.siesta import mark_finished

        await mark_finished()
