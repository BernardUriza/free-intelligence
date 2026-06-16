"""Mem0-style user-fact consolidator — NEUTRAL capability + host-job orchestrator.

PR-3d split: this module is the persona-NEUTRAL core of fact consolidation —
the dedup judge call, the transactional apply, the SAFETY-CAP P0, and the
per-run orchestration over a ``ConsolidationHooks`` contract. It contains NO
persona voice: the siesta sleep-coordination and the dream-diary (Insult's
voice) live behind hooks the persona implements (``personas/insult/core/
consolidation_hooks.py``). ``khimeras_shared`` never imports a persona.

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
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

import anthropic
import structlog

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

# Output cap for the judge LLM. The plan must reference every input fact id in
# exactly one op (NOOP/DELETE/UPDATE), and each op carries a short reason string
# — so output tokens scale linearly with input fact count. The original 2048 cap
# silently truncated mid-JSON for users with ≥80 facts (Alex/CPTSD case: 92 facts
# → judge_failed every run from 2026-04-26 through 2026-04-27). Haiku 4.5 supports
# up to 8192 output tokens; 4x the original headroom covers ~300+ facts/user.
JUDGE_MAX_OUTPUT_TOKENS = 8192


@dataclass
class FactOperation:
    """One row to write to fact_consolidation_log + apply to user_facts."""

    op: str  # NOOP | DELETE | UPDATE | ADD
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


class ConsolidationHooks(Protocol):
    """Persona-side hooks the neutral orchestrator calls at run boundaries.

    Everything persona-flavored (sleep coordination, the dream diary, any voice)
    lives behind these hooks so the orchestrator stays neutral and ``khimeras_shared``
    never imports a persona. Insult implements them with siesta + dream diary;
    ALICE uses ``NoopConsolidationHooks``.
    """

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


async def _call_judge(
    llm,
    model: str,
    facts: list[dict],
) -> tuple[list[dict] | None, int, int]:
    """Single Haiku call. Returns (plan, input_tokens, output_tokens).

    Shape B per memory:[[mcp-shape-b-canonical]]. fi-core
    (``build_consolidation_prompt`` + ``parse_consolidation_result``) owns the
    prompt content, the JSON parser, op-shape validation, and implicit-NOOP
    backfill. This function only orchestrates: build → execute via
    ``llm.utility_call`` (RunnerJudgeClient in prod, mock in tests) → parse.
    """
    from fi_core.persona.mcp_server import (
        build_consolidation_prompt,
        parse_consolidation_result,
    )

    prompt_spec = await build_consolidation_prompt(
        facts=facts,
        max_tokens_hint=JUDGE_MAX_OUTPUT_TOKENS,
    )

    try:
        response = await llm.utility_call(
            prompt_spec["system_prompt"],
            [{"role": "user", "content": prompt_spec["user_text"]}],
            model=model,
            max_tokens=prompt_spec["max_tokens"],
        )
    except (anthropic.APIError, anthropic.APIConnectionError) as e:
        log.warning("consolidator_judge_call_failed", error=str(e))
        return None, 0, 0
    if response.stop_reason == "max_tokens":
        log.warning(
            "consolidator_judge_truncated",
            facts_in=len(facts),
            max_tokens=prompt_spec["max_tokens"],
        )

    parsed = await parse_consolidation_result(
        raw_response=response.text,
        facts=facts,
    )
    if not parsed["ok"]:
        log.warning(
            "consolidator_judge_parse_failed",
            error=parsed["error"],
            raw_len=parsed["raw_len"],
        )
        return None, 0, 0
    return parsed["ops"], 0, 0


def _op_factory(
    op: str,
    fact_id_before: int | None,
    fact_id_after: int | None,
    text_before: str | None,
    text_after: str | None,
    reason: str,
) -> FactOperation:
    """Bridge between FactsRepository.apply_consolidation_plan (which doesn't
    know about FactOperation) and this module's dataclass."""
    return FactOperation(
        op=op,
        fact_id_before=fact_id_before,
        fact_id_after=fact_id_after,
        fact_text_before=text_before,
        fact_text_after=text_after,
        reason=reason,
    )


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
        by_id = {f["id"]: f for f in facts}
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
    by_id = {f["id"]: f for f in facts}
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
