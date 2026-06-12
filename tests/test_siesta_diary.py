"""Tests for diary prompt construction and run summary aggregation.

LLM and storage are NOT exercised here — they're tested separately or in
integration. This file owns the pure functions that turn a list of
:class:`ConsolidationReport` into a human-readable prompt and a status
classification.
"""

from __future__ import annotations

from personas.insult.core.memory_consolidator import ConsolidationReport, FactOperation
from personas.insult.core.siesta.diary.generator import (
    PLACEHOLDER_ON_LLM_FAILURE,
    _resolve_status,
    _summarize_reports,
)
from personas.insult.core.siesta.diary.prompts import build_user_prompt


def _ok_report(
    user_id: str, *, facts_in: int, facts_out: int, deletes: int = 0, updates: int = 0
) -> ConsolidationReport:
    """Synthesize a successful report. NOOPs fill the gap to facts_out."""
    noops = facts_out - updates  # one UPDATE row per merged fact, NOOPs cover the rest
    ops = (
        [FactOperation(op="DELETE", reason="dup") for _ in range(deletes)]
        + [FactOperation(op="UPDATE", reason="merge") for _ in range(updates)]
        + [FactOperation(op="NOOP", reason="standalone") for _ in range(max(0, noops))]
    )
    return ConsolidationReport(user_id=user_id, facts_in=facts_in, facts_out=facts_out, ops=ops, duration_ms=2000)


def _failed_report(user_id: str, facts_in: int, error: str = "judge_failed") -> ConsolidationReport:
    return ConsolidationReport(user_id=user_id, facts_in=facts_in, facts_out=facts_in, error=error, duration_ms=15000)


def test_resolve_status_all_ok():
    assert _resolve_status(failed_count=0, users_total=2) == "ok"


def test_resolve_status_some_failed_is_partial():
    assert _resolve_status(failed_count=1, users_total=2) == "partial"


def test_resolve_status_all_failed_is_failed():
    assert _resolve_status(failed_count=2, users_total=2) == "failed"


def test_summarize_reports_aggregates_totals():
    bernard = _ok_report("bernard", facts_in=55, facts_out=19, deletes=27, updates=12)
    alex = _failed_report("alex", facts_in=92)
    summary = _summarize_reports([bernard, alex])
    assert summary["users_processed"] == 1
    assert summary["facts_in_total"] == 55
    assert summary["facts_out_total"] == 19
    assert summary["deletes_total"] == 27
    assert summary["updates_total"] == 12
    assert summary["failed_users"] == ["alex"]
    assert summary["duration_ms"] == 17000  # 2000 + 15000


def test_summarize_reports_empty_input():
    summary = _summarize_reports([])
    assert summary["users_processed"] == 0
    assert summary["failed_users"] == []
    assert summary["user_summaries"] == []


def test_build_user_prompt_mentions_failures():
    summary = _summarize_reports(
        [
            _ok_report("bernard", facts_in=20, facts_out=10, deletes=10),
            _failed_report("alex", facts_in=92),
        ]
    )
    prompt = build_user_prompt(
        users_total=2,
        users_processed=summary["users_processed"],
        failed_users=summary["failed_users"],
        user_summaries=summary["user_summaries"],
        duration_ms=summary["duration_ms"],
    )
    assert "alex" in prompt
    assert "No terminé con" in prompt
    assert "bernard" in prompt
    assert "tenía 20" in prompt


def test_build_user_prompt_no_failures_omits_failed_line():
    summary = _summarize_reports([_ok_report("bernard", facts_in=10, facts_out=5, deletes=5)])
    prompt = build_user_prompt(
        users_total=1,
        users_processed=1,
        failed_users=[],
        user_summaries=summary["user_summaries"],
        duration_ms=summary["duration_ms"],
    )
    assert "No terminé con" not in prompt


def test_placeholder_string_is_in_character():
    # Sanity: the fallback diary entry should not leak "AI"/"Claude"/"error".
    assert "AI" not in PLACEHOLDER_ON_LLM_FAILURE
    assert "Claude" not in PLACEHOLDER_ON_LLM_FAILURE
    assert "Anthropic" not in PLACEHOLDER_ON_LLM_FAILURE
