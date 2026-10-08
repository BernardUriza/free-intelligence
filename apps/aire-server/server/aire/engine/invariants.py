"""What a text mutation is not allowed to do, and how a violation is measured.

The `pipeline` runs mutation stages; this module is the CONTRACT each stage
declares about its own damage. Split from the runner because it composes across
stages and is the half worth testing alone: every check takes `(before, after)`
and nothing else — never the stage's ctx — so any check works in any stage.

Each returns True when the invariant HOLDS, False when it is violated.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from .pipeline import MutationStage

MustPreserve = Callable[[str, str], bool]


def preserve_question_marks(before: str, after: str) -> bool:
    """A mutation may not swallow the questions the model asked."""
    return after.count("?") >= before.count("?")


def preserve_min_length(min_chars: int) -> MustPreserve:
    """Build a check refusing any mutation that leaves fewer than `min_chars`."""

    def check(before: str, after: str) -> bool:
        return len(after) >= min_chars

    check.__name__ = f"preserve_min_length({min_chars})"
    return check


def shrink_pct(before: str, after: str) -> float:
    """The fraction of the text a mutation removed. 0.0 when it grew."""
    if not before:
        return 0.0
    return max(0.0, (len(before) - len(after)) / len(before))


def broken(stage: "MutationStage", before: str, after: str) -> list[str]:
    """The names of the invariants this mutation broke. Empty means it is clean."""
    failed: list[str] = []
    if stage.max_shrink_pct is not None and shrink_pct(before, after) > stage.max_shrink_pct:
        failed.append(f"max_shrink_pct({stage.max_shrink_pct:.2f})")
    for check in stage.must_preserve:
        try:
            if not check(before, after):
                failed.append(check.__name__ or repr(check))
        except Exception:  # noqa: BLE001 — a check that raises is itself a violation
            failed.append(f"{getattr(check, '__name__', 'check')}:raised")
    return failed
