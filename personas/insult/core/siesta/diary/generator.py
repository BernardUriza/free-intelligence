"""LLM-driven dream diary generation.

Glues :mod:`prompts` to the Anthropic SDK and :mod:`storage` to persist
the resulting entry. Designed to be called ONCE at the end of a
consolidation run, not in any hot path. Fail-soft: if the diary call
errors, the consolidation run is still considered successful — we just
write a placeholder entry so the diary table never has gaps.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import anthropic
import structlog

from personas.insult.core.siesta.diary import storage as diary_storage
from personas.insult.core.siesta.diary.prompts import build_user_prompt, get_diary_system_prompt

if TYPE_CHECKING:
    from personas.insult.core.memory import MemoryStore
    from personas.insult.core.memory_consolidator import ConsolidationReport

log = structlog.get_logger()

DIARY_MAX_TOKENS = 240
"""Cap on diary text length. 60-90 word entries fit in well under this."""

PLACEHOLDER_ON_LLM_FAILURE = "Soñé pero no me acuerdo bien. Vuelvo a intentar mañana."


def _summarize_reports(reports: list[ConsolidationReport]) -> dict:
    """Pre-aggregate consolidation reports into prompt-friendly shapes.

    Pure function — no I/O, easy to test. ``user_summaries`` is sorted
    by user_id for deterministic prompt rendering. The caller is
    expected to enrich with display names (the report only has
    ``user_id``).
    """
    failed_users: list[str] = []
    user_summaries: list[dict] = []
    facts_in_total = 0
    facts_out_total = 0
    deletes_total = 0
    updates_total = 0
    duration_ms = 0
    users_processed = 0

    for r in reports:
        duration_ms += r.duration_ms
        ops = r.counts_by_op()
        deletes = ops.get("DELETE", 0)
        updates = ops.get("UPDATE", 0)
        noops = ops.get("NOOP", 0)
        if r.error:
            failed_users.append(r.user_id)
            user_summaries.append(
                {
                    "name": r.user_id,
                    "facts_in": r.facts_in,
                    "facts_out": r.facts_out,
                    "error": r.error,
                }
            )
            continue
        users_processed += 1
        facts_in_total += r.facts_in
        facts_out_total += r.facts_out
        deletes_total += deletes
        updates_total += updates
        user_summaries.append(
            {
                "name": r.user_id,
                "facts_in": r.facts_in,
                "facts_out": r.facts_out,
                "deletes": deletes,
                "updates": updates,
                "noops": noops,
                "error": None,
            }
        )
    return {
        "failed_users": failed_users,
        "user_summaries": user_summaries,
        "facts_in_total": facts_in_total,
        "facts_out_total": facts_out_total,
        "deletes_total": deletes_total,
        "updates_total": updates_total,
        "duration_ms": duration_ms,
        "users_processed": users_processed,
    }


def _resolve_status(failed_count: int, users_total: int) -> str:
    if failed_count == 0:
        return "ok"
    if failed_count >= users_total:
        return "failed"
    return "partial"


async def _call_llm(
    llm,
    model: str,
    user_prompt: str,
) -> tuple[str, str | None]:
    """Single Haiku call via the injected client's utility_call. Returns (text, error_or_none).

    The diary system prompt is identical across runs, so prompt cache
    pays off cycle to cycle. utility_call (not chat) is the right
    wrapper — diary entries are persisted, not user-facing prose, so
    character_break / language_cure overhead would be wasted Haiku
    tokens on a path that already runs at the end of consolidation.
    """
    try:
        response = await llm.utility_call(
            get_diary_system_prompt(),
            [{"role": "user", "content": user_prompt}],
            model=model,
            max_tokens=DIARY_MAX_TOKENS,
        )
    except anthropic.APIError as e:
        return PLACEHOLDER_ON_LLM_FAILURE, f"api_error: {e}"
    text = response.text.strip()
    if not text:
        return PLACEHOLDER_ON_LLM_FAILURE, "empty_response"
    return text, None


async def write_diary_for_run(
    reports: list[ConsolidationReport],
    *,
    memory: MemoryStore,
    llm,
    model: str,
    name_resolver: dict[str, str] | None = None,
) -> int | None:
    """Render and persist the diary entry for a consolidation run.

    ``name_resolver`` maps ``user_id`` → display name (e.g. "Alex"). If
    None, user_ids are used directly. Returns the new diary row id, or
    None on persistence failure.
    """
    summary = _summarize_reports(reports)
    if name_resolver:
        for entry in summary["user_summaries"]:
            entry["name"] = name_resolver.get(entry["name"], entry["name"])
        summary["failed_users"] = [name_resolver.get(uid, uid) for uid in summary["failed_users"]]

    user_prompt = build_user_prompt(
        users_total=len(reports),
        users_processed=summary["users_processed"],
        failed_users=summary["failed_users"],
        user_summaries=summary["user_summaries"],
        duration_ms=summary["duration_ms"],
    )

    content, llm_error = await _call_llm(llm, model, user_prompt)
    status = _resolve_status(len(summary["failed_users"]), len(reports))

    log.info(
        "siesta_diary_generated",
        status=status,
        users_total=len(reports),
        users_processed=summary["users_processed"],
        failed_users=len(summary["failed_users"]),
        duration_ms=summary["duration_ms"],
        llm_error=llm_error,
    )

    return await diary_storage.insert_entry(
        memory,
        duration_ms=summary["duration_ms"],
        users_total=len(reports),
        users_processed=summary["users_processed"],
        facts_in_total=summary["facts_in_total"],
        facts_out_total=summary["facts_out_total"],
        deletes_total=summary["deletes_total"],
        updates_total=summary["updates_total"],
        status=status,
        content=content,
        error=llm_error,
    )
