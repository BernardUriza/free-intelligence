"""Retrieval evaluation: labelled cases, per-stage metrics, and a flip gate.

Retrieval only, no model judging. Two stages are scored apart, because they fail
apart: the SHORTLIST (did the right source reach the reranker?) and the FINAL
set (did it survive the reranker and the floor?). Off-topic cases have no gold
source, and pass when nothing at all is accepted.

`gate` compares against a saved run and reports flips per case. Corpus and models
are frozen between two runs, so a flip is a real change; on a set this small an
average would hide it.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from fnmatch import fnmatchcase
from typing import Any


@dataclass(frozen=True)
class EvalCase:
    """One labelled query. `gold` holds source_ref patterns (`*` allowed); empty means off-topic."""

    id: str
    query: str
    gold: tuple[str, ...] = ()
    split: str = "dev"
    must_pass: bool = False

    @property
    def answerable(self) -> bool:
        return bool(self.gold)

    def matches(self, source_ref: str) -> bool:
        return any(fnmatchcase(source_ref, pattern) for pattern in self.gold)


@dataclass(frozen=True)
class Retrieved:
    """What one query got: the sources the reranker saw, and the ones that were kept."""

    shortlist: Sequence[str]
    accepted: Sequence[str]
    top_score: float | None = None


@dataclass(frozen=True)
class CaseResult:
    id: str
    answerable: bool
    must_pass: bool
    in_shortlist: bool
    passed: bool
    gold_rank: int | None
    top_score: float | None

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


def score_case(case: EvalCase, got: Retrieved) -> CaseResult:
    rank = next((i for i, ref in enumerate(got.shortlist, start=1) if case.matches(ref)), None)
    passed = any(case.matches(ref) for ref in got.accepted) if case.answerable else not got.accepted
    return CaseResult(
        case.id, case.answerable, case.must_pass, rank is not None, passed, rank, got.top_score
    )


async def run_cases(
    cases: Iterable[EvalCase], retrieve: Callable[[str], Awaitable[Retrieved]]
) -> list[CaseResult]:
    return [score_case(case, await retrieve(case.query)) for case in cases]


def summarize(results: Sequence[CaseResult]) -> dict[str, float | int]:
    """Counts and rates: shortlist recall and final hit on answerable cases, false accepts on the rest."""
    on = [r for r in results if r.answerable]
    off = [r for r in results if not r.answerable]
    return {
        "answerable": len(on),
        "shortlist_recall": _rate(sum(r.in_shortlist for r in on), len(on)),
        "final_hit": _rate(sum(r.passed for r in on), len(on)),
        "off_topic": len(off),
        "false_accept": _rate(sum(not r.passed for r in off), len(off)),
    }


def _rate(hits: int, total: int) -> float:
    return round(hits / total, 4) if total else 0.0


def gate(
    baseline: Mapping[str, Mapping[str, Any]], current: Sequence[CaseResult], *, max_lost_hits: int = 1
) -> list[str]:
    """Reasons this run is worse than `baseline` (empty list = green).

    Fails on: a gold source that left the shortlist, a `must_pass` case that
    fails and is new or used to pass, an off-topic query that starts accepting, more than `max_lost_hits`
    lost final hits, and a baseline case that was not run.
    """
    reasons: list[str] = []
    lost: list[str] = []
    for r in current:
        before = baseline.get(r.id)
        if r.must_pass and not r.passed and (before is None or before["passed"]):
            reasons.append(f"{r.id}: must_pass case fails")
        if before is None:
            continue
        if r.answerable and before["in_shortlist"] and not r.in_shortlist:
            reasons.append(f"{r.id}: the right source left the shortlist (was rank {before['gold_rank']})")
        if before["passed"] and not r.passed:
            if r.answerable:
                lost.append(r.id)
            else:
                reasons.append(f"{r.id}: an off-topic query now gets passages")
    if len(lost) > max_lost_hits:
        reasons.append(f"lost {len(lost)} final hits: {', '.join(lost)}")
    missing = sorted(set(baseline) - {r.id for r in current})
    if missing:
        reasons.append(f"{len(missing)} baseline cases were not run: {', '.join(missing[:5])}")
    return reasons


__all__ = ["CaseResult", "EvalCase", "Retrieved", "gate", "run_cases", "score_case", "summarize"]
