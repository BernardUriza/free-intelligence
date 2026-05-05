"""Mem0-style user-fact consolidator.

After hundreds of conversation turns, the auto-extracted facts pile up
with overlap, contradictions, and stale entries. The fact-extraction
LLM in :mod:`insult.core.facts` runs per-turn and never looks at the
*global* picture; it can't notice that "Vive en México" and "Está
viviendo en CDMX" are the same fact at different granularity, or that
"Trabaja en X" was superseded six weeks ago by "Renunció a X".

This module runs OUT-OF-BAND (scheduled task, every 2 days) and:

1. Loads the live (``deleted_at IS NULL``) facts for one user.
2. Asks the summary model (Haiku) for an ADD/UPDATE/DELETE/NOOP plan
   over the entire fact set in a single call. The model sees the
   whole snapshot, not pair-wise comparisons, so it catches global
   redundancy.
3. Applies the plan transactionally:
   - DELETE → soft-delete (``deleted_at = now()``); recoverable for
     90 days, then hard-purged.
   - UPDATE → soft-delete the original AND insert the merged text.
   - ADD/NOOP → no DB writes (ADD is the extraction LLM's job).
4. Logs every decision in ``fact_consolidation_log`` for audit.

Reference: Mem0 paper (arxiv 2504.19413). The big simplification vs.
the paper: we use one LLM call over the full set instead of pair-wise
extract→resolve passes against a vector store. With ~80 facts/user
the prompt fits comfortably in Haiku's context window and one call is
~30x cheaper than N**2 pair comparisons.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import anthropic
import structlog

from insult.core.prompts_loader import load_prompt

if TYPE_CHECKING:
    from insult.core.memory import MemoryStore

log = structlog.get_logger()

# 90 days in seconds — retention window for soft-deleted facts before
# the hard-purge query removes them. Tuned with operations: 90d is long
# enough that a misclassified DELETE is almost always caught by the
# next consolidation run plus operator review, but short enough that
# the table doesn't accumulate forever.
SOFT_DELETE_RETENTION_SECONDS = 90 * 86400

# Output cap for the judge LLM. The plan must reference every input
# fact id in exactly one op (NOOP/DELETE/UPDATE), and each op carries a
# short reason string — so output tokens scale linearly with input fact
# count. The original 2048 cap silently truncated mid-JSON for users
# with ≥80 facts (Alex/CPTSD case: 92 facts → judge_failed every run
# from 2026-04-26 through 2026-04-27). Haiku 4.5 supports up to 8192
# output tokens; 4x the original headroom covers ~300+ facts/user before
# we'd need a chunking strategy.
JUDGE_MAX_OUTPUT_TOKENS = 8192


# Prompt lives in insult/prompts/memory_consolidator_judge.md


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


def _build_user_prompt(facts: list[dict]) -> str:
    """Render the user's fact set as a numbered list for the judge."""
    lines = []
    for f in facts:
        # updated_at is unix-seconds; format as ISO date for the model
        # so age comparisons are easier to reason about than raw floats.
        ts = f.get("updated_at") or 0
        when = time.strftime("%Y-%m-%d", time.gmtime(ts)) if ts else "unknown"
        lines.append(
            f'{{"id": {f["id"]}, "fact": {json.dumps(f["fact"], ensure_ascii=False)}, '
            f'"category": "{f.get("category", "general")}", "updated_at": "{when}"}}'
        )
    return "Current facts:\n[\n  " + ",\n  ".join(lines) + "\n]"


def _parse_judge_response(raw: str) -> list[dict] | None:
    """Strip markdown fences, parse JSON, return list[dict] or None on error."""
    raw = raw.strip()
    if raw.startswith("```"):
        # Markdown fence: drop opening fence + optional language tag, drop closing.
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        plan = json.loads(raw)
    except json.JSONDecodeError as e:
        log.warning("consolidator_judge_parse_failed", error=str(e), raw=raw[:200])
        return None
    if not isinstance(plan, list):
        log.warning("consolidator_judge_not_array", raw=raw[:200])
        return None
    return plan


def _validate_plan(plan: list[dict], facts: list[dict]) -> list[dict]:
    """Drop malformed ops and warn. Every input fact must be referenced exactly once."""
    valid_ids = {f["id"] for f in facts}
    seen: set[int] = set()
    valid_ops: list[dict] = []
    for op in plan:
        if not isinstance(op, dict) or "op" not in op:
            continue
        kind = op["op"]
        if kind in ("NOOP", "DELETE"):
            fid = op.get("id")
            if fid not in valid_ids or fid in seen:
                continue
            seen.add(fid)
            valid_ops.append(op)
        elif kind == "UPDATE":
            ids = op.get("merge_ids") or []
            new_text = op.get("new_fact")
            if not isinstance(ids, list) or not new_text:
                continue
            ids_int = [i for i in ids if isinstance(i, int) and i in valid_ids and i not in seen]
            if not ids_int:
                continue
            seen.update(ids_int)
            op["merge_ids"] = ids_int
            valid_ops.append(op)
    # Any fact id the judge ignored gets an implicit NOOP — never silently lose a row.
    for f in facts:
        if f["id"] not in seen:
            valid_ops.append({"op": "NOOP", "id": f["id"], "reason": "implicit (judge omitted)"})
    return valid_ops


async def _call_judge(
    client: anthropic.AsyncAnthropic,
    model: str,
    facts: list[dict],
) -> tuple[list[dict] | None, int, int]:
    """Single Haiku call. Returns (plan, input_tokens, output_tokens).

    Logs a warning when the response stop_reason is ``max_tokens`` —
    that's the canary for "we need to bump JUDGE_MAX_OUTPUT_TOKENS or
    chunk the input". Without it, truncation looks identical to a
    normal model output to ``_parse_judge_response`` and surfaces only
    as a downstream JSON parse failure.
    """
    user_prompt = _build_user_prompt(facts)
    try:
        response = await client.messages.create(
            model=model,
            max_tokens=JUDGE_MAX_OUTPUT_TOKENS,
            system=load_prompt("memory_consolidator_judge"),
            messages=[{"role": "user", "content": user_prompt}],
        )
    except (anthropic.APIError, anthropic.APIConnectionError) as e:
        log.warning("consolidator_judge_call_failed", error=str(e))
        return None, 0, 0
    if getattr(response, "stop_reason", None) == "max_tokens":
        log.warning(
            "consolidator_judge_truncated",
            facts_in=len(facts),
            output_tokens=response.usage.output_tokens,
            max_tokens=JUDGE_MAX_OUTPUT_TOKENS,
        )
    raw = response.content[0].text if response.content else ""
    plan = _parse_judge_response(raw)
    return plan, response.usage.input_tokens, response.usage.output_tokens


async def _apply_plan(
    db,
    user_id: str,
    facts: list[dict],
    plan: list[dict],
    run_ts: float,
) -> list[FactOperation]:
    """Translate the judge's plan to SQL ops + audit log entries."""
    by_id = {f["id"]: f for f in facts}
    applied: list[FactOperation] = []

    for op in plan:
        kind = op["op"]
        reason = op.get("reason", "")[:500]

        if kind == "NOOP":
            fid = op["id"]
            applied.append(
                FactOperation(
                    op="NOOP",
                    fact_id_before=fid,
                    fact_id_after=fid,
                    fact_text_before=by_id[fid]["fact"],
                    fact_text_after=by_id[fid]["fact"],
                    reason=reason,
                )
            )
            continue

        if kind == "DELETE":
            fid = op["id"]
            await db.execute(
                "UPDATE user_facts SET deleted_at = ? WHERE id = ?",
                (run_ts, fid),
            )
            applied.append(
                FactOperation(
                    op="DELETE",
                    fact_id_before=fid,
                    fact_id_after=None,
                    fact_text_before=by_id[fid]["fact"],
                    fact_text_after=None,
                    reason=reason,
                )
            )
            continue

        if kind == "UPDATE":
            ids = op["merge_ids"]
            new_text = op["new_fact"]
            category = op.get("category", "general")
            # Soft-delete originals
            for fid in ids:
                await db.execute(
                    "UPDATE user_facts SET deleted_at = ? WHERE id = ?",
                    (run_ts, fid),
                )
            # Insert merged
            cursor = await db.execute(
                "INSERT INTO user_facts (user_id, fact, category, updated_at, source) VALUES (?, ?, ?, ?, 'auto')",
                (user_id, new_text, category, run_ts),
            )
            new_id = cursor.lastrowid or 0
            for fid in ids:
                applied.append(
                    FactOperation(
                        op="UPDATE",
                        fact_id_before=fid,
                        fact_id_after=new_id,
                        fact_text_before=by_id[fid]["fact"],
                        fact_text_after=new_text,
                        reason=reason,
                    )
                )

    # Write audit rows
    for o in applied:
        await db.execute(
            "INSERT INTO fact_consolidation_log "
            "(run_ts, user_id, fact_id_before, fact_id_after, op, reason, "
            "fact_text_before, fact_text_after) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                run_ts,
                user_id,
                o.fact_id_before,
                o.fact_id_after,
                o.op,
                o.reason,
                o.fact_text_before,
                o.fact_text_after,
            ),
        )
    return applied


async def consolidate_user_facts(
    user_id: str,
    *,
    memory: MemoryStore,
    llm_client: anthropic.AsyncAnthropic,
    model: str,
    dry_run: bool = False,
) -> ConsolidationReport:
    """Run one consolidation pass for a single user. See module docstring."""
    started = time.monotonic()
    run_ts = time.time()
    facts = await memory.get_facts(user_id)

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

    plan, in_toks, out_toks = await _call_judge(llm_client, model, facts)
    report.haiku_input_tokens = in_toks
    report.haiku_output_tokens = out_toks
    if plan is None:
        report.error = "judge_failed"
        report.duration_ms = int((time.monotonic() - started) * 1000)
        log.warning("consolidator_user_failed", user_id=user_id, reason="judge_failed")
        return report

    valid_plan = _validate_plan(plan, facts)

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

    # Apply the plan transactionally — single connection, single commit.
    db = memory._db
    try:
        report.ops = await _apply_plan(db, user_id, facts, valid_plan, run_ts)
        await db.commit()
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
    db = memory._db
    cursor = await db.execute(
        "SELECT COUNT(*) FROM user_facts WHERE user_id = ? AND deleted_at IS NULL",
        (user_id,),
    )
    row = await cursor.fetchone()
    return row[0] if row else 0


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
    db = memory._db
    cursor = await db.execute(
        "DELETE FROM user_facts WHERE deleted_at IS NOT NULL AND deleted_at < ?",
        (cutoff,),
    )
    purged = cursor.rowcount or 0
    await db.commit()
    log.info("consolidator_hard_purge", purged=purged, retention_seconds=retention_seconds)
    return purged


async def consolidate_all_users(
    *,
    memory: MemoryStore,
    llm_client: anthropic.AsyncAnthropic,
    model: str,
    dry_run: bool = False,
    write_diary: bool = True,
    name_resolver: dict[str, str] | None = None,
) -> list[ConsolidationReport]:
    """Run consolidation across every user that has facts.

    Sequential (per the v3.6.0 design decision): one Haiku call per user
    rather than one batched call covering all users. Cost difference is
    ~$0.15/month total at current usage and the failure mode of a batch
    call is much harder to debug.

    Siesta integration (v3.7.0): marks the bot's blob metadata at start,
    after each user, and at the end. The bot replica polls that metadata
    and silences itself while ``phase != awake`` to avoid mtime-collision
    races on the shared blob. ``mark_finished`` runs in ``finally`` so a
    crash can never leave the bot stuck asleep.
    """
    from insult.core.siesta import (
        SiestaPhase,
        mark_finished,
        mark_progress,
        mark_started,
    )
    from insult.core.siesta.diary.generator import write_diary_for_run

    all_facts = await memory.get_all_facts()
    user_ids = sorted({f["user_id"] for f in all_facts})
    log.info("consolidator_run_started", users=len(user_ids), dry_run=dry_run)

    started_at = await _siesta_start_marker(len(user_ids), dry_run, mark_started)

    reports: list[ConsolidationReport] = []
    try:
        for idx, uid in enumerate(user_ids):
            if started_at is not None and not dry_run:
                await mark_progress(
                    phase=SiestaPhase.LIGHT,
                    started_at=started_at,
                    total_users=len(user_ids),
                    processed_users=idx,
                    current_user_id=uid,
                )
            report = await consolidate_user_facts(
                uid, memory=memory, llm_client=llm_client, model=model, dry_run=dry_run
            )
            reports.append(report)

        if not dry_run:
            if started_at is not None:
                await mark_progress(
                    phase=SiestaPhase.REM,
                    started_at=started_at,
                    total_users=len(user_ids),
                    processed_users=len(user_ids),
                )
            purged = await hard_purge_soft_deleted(memory)
            log.info("consolidator_run_complete", users=len(reports), hard_purged=purged)
            if write_diary and reports:
                await write_diary_for_run(
                    reports,
                    memory=memory,
                    llm_client=llm_client,
                    model=model,
                    name_resolver=name_resolver,
                )
        else:
            log.info("consolidator_run_complete_dry", users=len(reports))
    finally:
        if not dry_run:
            await mark_finished()

    return reports


async def _siesta_start_marker(total_users: int, dry_run: bool, mark_started_fn) -> object | None:
    """Wrapper so ``mark_started`` only runs in real (non-dry) job mode.

    Returns the started_at timestamp (UTC datetime) so per-user progress
    calls can reference it without re-reading the blob. ``None`` means
    "no marker placed" — happens on dry-run or when Azure isn't wired up
    locally; either way the caller skips per-progress updates.
    """
    if dry_run:
        return None
    from datetime import UTC, datetime

    placed = await mark_started_fn(total_users)
    return datetime.now(UTC) if placed else None
