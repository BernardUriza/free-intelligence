"""Consolidation orchestration — the per-user pass, the all-users run, the purge.

This is the persona-NEUTRAL core of fact consolidation (PR-3d split): the dedup
judge call, the transactional apply, the SAFETY-CAP P0, and the per-run
orchestration over a ``ConsolidationHooks`` contract. It contains NO persona
voice — the siesta sleep-coordination and the dream-diary live behind the hooks.

After hundreds of conversation turns, the auto-extracted facts pile up with
overlap, contradictions, and stale entries. The fact-extraction LLM runs
per-turn and never looks at the *global* picture; it can't notice that "Vive en
México" and "Está viviendo en CDMX" are the same fact at different granularity,
or that "Trabaja en X" was superseded six weeks ago by "Renunció a X".

This runs OUT-OF-BAND (scheduled job, every 2 days) and:

1. Loads the live (``deleted_at IS NULL``) facts for one user.
2. Asks the summary model (Haiku) for an ADD/UPDATE/DELETE/NOOP plan over the
   entire fact set in a single call — the model sees the whole snapshot, so it
   catches global redundancy.
3. Applies the plan transactionally (DELETE → soft-delete; UPDATE → soft-delete
   original + insert merged; ADD/NOOP → no write).
4. Logs every decision in ``fact_consolidation_log`` for audit.

Reference: Mem0 paper (arxiv 2504.19413). The big simplification: one LLM call
over the full set instead of pair-wise extract→resolve passes against a vector
store.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import structlog

from khimeras_shared.consolidation.clinical_guard import filter_clinical_destruction
from khimeras_shared.consolidation.contracts import (
    ConsolidationHooks,
    ConsolidationReport,
    FactOperation,
    _op_factory,
)
from khimeras_shared.consolidation.judge import _call_judge

if TYPE_CHECKING:
    from khimeras_shared.memory import MemoryStore

log = structlog.get_logger()

# 90 days in seconds — retention window for soft-deleted facts before the
# hard-purge query removes them. 90d is long enough that a misclassified DELETE
# is almost always caught by the next consolidation run plus operator review,
# but short enough that the table doesn't accumulate forever.
SOFT_DELETE_RETENTION_SECONDS = 90 * 86400

# SAFETY CAP (2026-06-03 P0, hardened to ZERO by operator order): the
# consolidator may NOT destroy memory. After it buried Alex's entire
# CPTSD/treatment history and nearly wiped 328 of Bernard's curated imports,
# the policy is absolute: a consolidation pass that would delete or merge-away
# ANY fact is REJECTED WHOLESALE — nothing is applied, and the run logs a loud
# alert with the exact ops it refused (justify + retract). The consolidator is
# now effectively non-destructive: it can only NOOP (or, in future, ADD). It
# cannot forget anything. "Destroyed" = DELETE ops + net facts consumed by
# UPDATE merges (merge_ids - 1 each). Raise this ONLY with a human-reviewed,
# test-backed redesign — never let an LLM silently decide what to forget again.
CONSOLIDATION_MAX_DESTROY_FRACTION = 0.0
# Any destruction at all (>= 1 fact) trips the cap. Zero tolerance.
CONSOLIDATION_MIN_DESTROY_TO_CAP = 1

# Curated provenance — these sources are NEVER eligible for consolidation.
# 'manual' (operator-written, rescued, OR bulk-imported-then-curated from the
# ChatGPT export) and 'agent' ([REMEMBER:]-tagged). The consolidator only ever
# sees auto-extracted facts; curated memory is untouchable.
#
# HARD CONSTRAINT (2026-06-03 P0): every value stored in principal_facts.source
# MUST be a member of fi_core's `FactSource` enum (auto / manual / agent). The
# store does `FactSource(row["source"])` on read, so any out-of-enum value
# (we once bulk-imported 328 rows as 'chatgpt_import') makes get_facts() raise
# `ValueError` for that whole principal — the bot then loads ZERO facts and acts
# amnesiac. Those rows were relabeled to 'manual'. Do NOT introduce a new source
# string without first adding it to fi_core's FactSource enum.
CURATED_SOURCES = frozenset({"manual", "agent"})


async def consolidate_user_facts(
    user_id: str,
    *,
    memory: MemoryStore,
    llm,
    model: str,
    dry_run: bool = False,
) -> ConsolidationReport:
    """Run one consolidation pass for a single user. See module docstring."""
    started = time.monotonic()
    run_ts = time.time()
    facts = await memory.get_facts(user_id)

    # PROVENANCE GUARD (2026-06-03): curated facts are NEVER eligible for
    # consolidation. Sources 'manual' (operator-written, rescued, OR the
    # bulk-imported-then-curated ChatGPT export) and 'agent' ([REMEMBER:]-tagged)
    # are deliberate and MUST survive untouched. Without this guard the judge (a
    # small model) over-grouped substantive facts and soft-deleted them: it
    # nearly wiped 328 of Bernard's curated imports and had already buried Alex's
    # entire CPTSD/treatment history. See memory_consolidator P0, 2026-06-03.
    curated = [f for f in facts if f.get("source") in CURATED_SOURCES]
    facts = [f for f in facts if f.get("source") not in CURATED_SOURCES]
    if curated:
        log.info("consolidator_curated_protected", user_id=user_id, protected=len(curated), eligible=len(facts))

    report = ConsolidationReport(user_id=user_id, facts_in=len(facts), facts_out=len(facts))

    if not facts:
        report.duration_ms = int((time.monotonic() - started) * 1000)
        log.info("consolidator_user_skipped", user_id=user_id, reason="no_facts")
        return report

    if len(facts) < 3:
        # No meaningful overlap to detect — skip the LLM call.
        report.duration_ms = int((time.monotonic() - started) * 1000)
        log.info("consolidator_user_skipped", user_id=user_id, reason="below_min_facts", facts=len(facts))
        return report

    plan, in_toks, out_toks = await _call_judge(llm, model, facts)
    report.haiku_input_tokens = in_toks
    report.haiku_output_tokens = out_toks
    if plan is None:
        report.error = "judge_failed"
        report.duration_ms = int((time.monotonic() - started) * 1000)
        log.warning("consolidator_user_failed", user_id=user_id, reason="judge_failed")
        return report

    # fi-core's parse_consolidation_result already validated op shape, dropped
    # malformed ops, and backfilled implicit NOOPs — `plan` is ready to apply.
    valid_plan = plan

    # CLINICAL GUARD: whatever the judge asked, a health/trauma fact is NOT
    # destroyable. Blocked ops become NOOPs; the rest of the plan survives.
    by_id = {f["id"]: f for f in facts}
    valid_plan, blocked = filter_clinical_destruction(valid_plan, by_id)
    if blocked:
        log.warning(
            "consolidator_clinical_destruction_blocked",
            user_id=user_id,
            blocked=len(blocked),
            ops=[{"op": o["op"], "id": o.get("id"), "merge_ids": o.get("merge_ids")} for o in blocked[:10]],
        )

    # SAFETY CAP: reject any plan that would destroy too much of the user's
    # memory in one pass. This is the hard backstop against a judge model
    # decimating substantive facts (the 2026-06-03 Alex P0). Counts DELETE ops
    # plus net facts consumed by UPDATE merges. Over the cap → apply NOTHING.
    destroyed = sum(1 for op in valid_plan if op["op"] == "DELETE") + sum(
        max(0, len(op.get("merge_ids", [])) - 1) for op in valid_plan if op["op"] == "UPDATE"
    )
    if (
        facts
        and destroyed >= CONSOLIDATION_MIN_DESTROY_TO_CAP
        and (destroyed / len(facts)) > CONSOLIDATION_MAX_DESTROY_FRACTION
    ):
        report.error = "rejected_excessive_destruction"
        report.duration_ms = int((time.monotonic() - started) * 1000)
        log.warning(
            "consolidator_plan_rejected",
            user_id=user_id,
            reason="excessive_destruction",
            facts_in=len(facts),
            would_destroy=destroyed,
            fraction=round(destroyed / len(facts), 2),
            cap=CONSOLIDATION_MAX_DESTROY_FRACTION,
        )
        return report

    if dry_run:
        # Build the report without touching the DB.
        for op in valid_plan:
            kind = op["op"]
            if kind == "NOOP":
                report.ops.append(
                    FactOperation(
                        op="NOOP",
                        fact_id_before=op["id"],
                        fact_id_after=op["id"],
                        fact_text_before=by_id[op["id"]]["fact"],
                        fact_text_after=by_id[op["id"]]["fact"],
                        reason=op.get("reason", ""),
                    )
                )
            elif kind == "DELETE":
                report.ops.append(
                    FactOperation(
                        op="DELETE",
                        fact_id_before=op["id"],
                        fact_text_before=by_id[op["id"]]["fact"],
                        reason=op.get("reason", ""),
                    )
                )
            elif kind == "UPDATE":
                for fid in op["merge_ids"]:
                    report.ops.append(
                        FactOperation(
                            op="UPDATE",
                            fact_id_before=fid,
                            fact_text_before=by_id[fid]["fact"],
                            fact_text_after=op["new_fact"],
                            reason=op.get("reason", ""),
                        )
                    )
        report.facts_out = sum(1 for o in report.ops if o.op == "NOOP") + sum(
            1 for op in valid_plan if op["op"] == "UPDATE"
        )
        report.duration_ms = int((time.monotonic() - started) * 1000)
        log.info(
            "consolidator_user_dry_run",
            user_id=user_id,
            facts_in=report.facts_in,
            facts_out=report.facts_out,
            ops=report.counts_by_op(),
            duration_ms=report.duration_ms,
        )
        return report

    # Apply the plan transactionally — the repo wraps every UPDATE/INSERT plus
    # the audit-log writes in a single asyncpg transaction so a crash mid-plan
    # can't leave user_facts and fact_consolidation_log out of sync.
    try:
        report.ops = await memory._facts.apply_consolidation_plan(user_id, by_id, valid_plan, run_ts, _op_factory)
    except Exception as e:
        log.exception("consolidator_apply_failed", user_id=user_id, error=str(e))
        report.error = f"apply_failed: {e}"
        report.duration_ms = int((time.monotonic() - started) * 1000)
        return report

    report.facts_out = await _count_live_facts(memory, user_id)
    report.duration_ms = int((time.monotonic() - started) * 1000)
    log.info(
        "consolidator_user_applied",
        user_id=user_id,
        facts_in=report.facts_in,
        facts_out=report.facts_out,
        ops=report.counts_by_op(),
        duration_ms=report.duration_ms,
        haiku_input_tokens=in_toks,
        haiku_output_tokens=out_toks,
    )
    return report


async def _count_live_facts(memory: MemoryStore, user_id: str) -> int:
    """Live (non-deleted) facts after applying a plan."""
    return await memory._facts.count_live(user_id)


async def hard_purge_soft_deleted(
    memory: MemoryStore,
    *,
    retention_seconds: int = SOFT_DELETE_RETENTION_SECONDS,
) -> int:
    """Delete rows whose ``deleted_at`` is older than the retention window.

    Returns the number of rows actually purged. Runs at the END of every
    consolidation invocation in the same scheduled job.
    """
    cutoff = time.time() - retention_seconds
    purged = await memory._facts.purge_soft_deleted(cutoff)
    log.info("consolidator_hard_purge", purged=purged, retention_seconds=retention_seconds)
    return purged


async def consolidate_all_users(
    *,
    memory: MemoryStore,
    llm,
    model: str,
    hooks: ConsolidationHooks,
    dry_run: bool = False,
    name_resolver: dict[str, str] | None = None,
) -> list[ConsolidationReport]:
    """Run consolidation across every user that has facts (host-job orchestrator).

    Neutral: the persona-flavored side effects (siesta sleep coordination, dream
    diary) are delegated to ``hooks`` so this function never imports a persona.

    Sequential (per the v3.6.0 design decision): one Haiku call per user. The
    siesta integration (v3.7.0) marks blob metadata at start/per-user/end through
    the hooks; ``on_run_finished`` runs in ``finally`` so a crash can never leave
    the bot stuck asleep.
    """
    all_facts = await memory.get_all_facts()
    user_ids = sorted({f["user_id"] for f in all_facts})
    log.info("consolidator_run_started", users=len(user_ids), dry_run=dry_run)

    marker = await hooks.on_run_started(total_users=len(user_ids), dry_run=dry_run)

    reports: list[ConsolidationReport] = []
    try:
        for idx, uid in enumerate(user_ids):
            if marker is not None:
                await hooks.on_user_progress(
                    marker=marker,
                    total_users=len(user_ids),
                    processed_users=idx,
                    current_user_id=uid,
                )
            report = await consolidate_user_facts(uid, memory=memory, llm=llm, model=model, dry_run=dry_run)
            reports.append(report)

            # Per-user post-step (e.g. incremental deep_memory ingest) is a
            # persona/capability concern delegated to the hook. Real runs only —
            # skipped on dry_run for cost parity.
            if not dry_run:
                await hooks.after_user(user_id=uid)

        if not dry_run:
            if marker is not None:
                await hooks.on_pre_finish(marker=marker, total_users=len(user_ids))
            purged = await hard_purge_soft_deleted(memory)
            log.info("consolidator_run_complete", users=len(reports), hard_purged=purged)
            if reports:
                await hooks.write_diary(reports, memory=memory, llm=llm, model=model, name_resolver=name_resolver)
        else:
            log.info("consolidator_run_complete_dry", users=len(reports))
    finally:
        if not dry_run:
            await hooks.on_run_finished()

    return reports
