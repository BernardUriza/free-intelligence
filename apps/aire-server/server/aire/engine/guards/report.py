"""What the door gets back: the observational contract, and nothing else.

Split from `run.py` because the two answer different questions and change on
different triggers. `run` is HOW guards execute — one raising, one overriding,
the order overrides apply. This file is WHAT the caller is told, which is the
shape of an SSE event and the only thing imported from outside the package.

The contract itself: AIRE streams `text` events as they arrive, so by the time a
guard sees a finished turn the caller has already read those bytes. A
`text_override` cannot un-send them and a `retry` would re-bill a turn nobody
asked twice for. Neither is applied. Both are REPORTED — because a safety net
whose findings vanish is worse than no net: the drift stops being visible.
"""

from __future__ import annotations

from typing import Any

from ..contract import Guard, GuardOutcome
from .run import run_guards


def guard_level(metadata: dict[str, Any]) -> str:
    """A single representative level for one guard's findings, for telemetry.
    Lives beside `run_guards` because it reads what `run_guards` produced."""
    if metadata.get("guard_failed"):
        return "error"
    return metadata.get("level") or metadata.get("severity") or "ok"


def _findings(outcomes: dict[str, GuardOutcome]) -> dict[str, Any]:
    """One flat row per guard, JSON-ready. The raw outcome is deliberately not
    shipped: a guard may park a live object in `metadata` — fi-core's triage put a
    whole score object there — and that reaches the wire as a serialization crash
    on a turn that had already succeeded."""
    return {n: {"level": guard_level(o.metadata),
                "matched": o.metadata.get("matched", []),
                "failed": bool(o.metadata.get("guard_failed"))}
            for n, o in outcomes.items()}


def observe(guards: list[Guard], text: str, user_message: str,
            request_id: str | None = None) -> dict[str, Any]:
    """The OBSERVATIONAL contract: run the guards, report what they found, and
    change nothing about the turn.

    AIRE streams `text` events as they arrive, so by the time a guard sees the
    finished text the caller has already read it — a `text_override` cannot
    un-send it and a `retry` would re-bill a turn the caller did not ask twice
    for. Neither is honoured. Both are REPORTED under `unenforced`, because a
    safety net whose findings vanish is worse than no net: the drift stops being
    visible. Whether the door should buffer a guarded turn so the transformational
    half can act is Bernard's open fork, not this function's to assume."""
    events: list[str] = []
    # `final=False` on purpose, even though no retry is coming. `final=True` tells
    # a guard "retries are exhausted, clean up instead of asking" — so it produces
    # a sanitize this function throws away AND swallows the reinforcement string,
    # which is the one actionable thing a caller could use. AIRE does not retry;
    # the caller might, and it needs to be told what to say.
    _, outcomes, wants_retry, reinforcement = run_guards(
        guards, text, user_message, final=False,
        request_id=request_id, emit=lambda e, f: events.append(e),
    )
    return {
        "type": "guards",
        "findings": _findings(outcomes),
        "signals": events,
        "unenforced": [n for n, o in outcomes.items() if not o.clean],
        "wanted_retry": wants_retry,
        "reinforcement": reinforcement,
    }
