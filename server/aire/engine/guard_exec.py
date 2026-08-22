"""Running a guard list over one turn, and aggregating what they found.

Separate from `guards.py` (what a guard IS, and which ones exist) because this
is the WHAT-HAPPENS: run each guard once, apply overrides in order, collect the
outcomes, and surface a CRITICAL signal as telemetry. It is pure-functional —
guards + text + sink in, aggregate out — so it is testable without a client, a
session, or a database.

A guard is a safety NET, never a single point of failure: one that raises (a
malformed pattern, a missing backing) is logged and skipped, and the turn ships
the model's valid text rather than dying. That asymmetry is deliberate — a
broken guard must not be able to take a paid turn down with it.
"""

from __future__ import annotations

from typing import Any, Callable

from .contract import Guard, GuardOutcome

EmitSink = Callable[[str, dict[str, Any]], None]


def _named(guard: Guard) -> str:
    """A guard's telemetry name. `repr` is the lazy fallback — it is expensive
    for a guard holding compiled-pattern lists, so it only runs when `.name` is
    absent."""
    return getattr(guard, "name", None) or repr(guard)


def _is_critical(outcome: GuardOutcome) -> bool:
    meta = outcome.metadata
    return meta.get("critical") is True or meta.get("level") == "CRITICAL"


def _inspect_one(
    guard: Guard, text: str, user_message: str, *, final: bool, emit: EmitSink
) -> GuardOutcome:
    """One guard's outcome, or a `guard_failed` outcome if it raised."""
    try:
        return guard.inspect(response_text=text, context=(user_message,), final=final)
    except Exception as exc:  # noqa: BLE001 — a guard never kills the turn
        emit("guard_error", {"guard": _named(guard), "error": str(exc)})
        return GuardOutcome(metadata={"guard_failed": True, "error": str(exc)})


def _emit_critical(name: str, outcome: GuardOutcome, request_id: str | None, emit: EmitSink) -> None:
    """A guaranteed safety signal must SURFACE as telemetry so a consumer can
    escalate — including for an observational guard that never edits the text."""
    emit(
        "guard_critical",
        {
            "guard": name,
            "request_id": request_id,
            "level": outcome.metadata.get("level"),
            "gravity": outcome.metadata.get("gravity"),
            "reasons": outcome.metadata.get("reasons"),
        },
    )


def _absorb(
    guard: Guard, text: str, user_message: str, *, final: bool,
    request_id: str | None, emit: EmitSink, outcomes: dict[str, GuardOutcome],
) -> tuple[str, str | None]:
    """Run one guard, record its outcome, and return the text it leaves behind
    plus the reinforcement it asks for (None when it wants no retry)."""
    name = _named(guard)
    outcome = _inspect_one(guard, text, user_message, final=final, emit=emit)
    outcomes[name] = outcome
    if _is_critical(outcome):
        _emit_critical(name, outcome, request_id, emit)
    if outcome.text_override is not None:
        text = outcome.text_override
    return text, (outcome.reinforcement if outcome.retry else None)


def run_guards(
    guards: list[Guard],
    text: str,
    user_message: str,
    *,
    final: bool,
    request_id: str | None = None,
    emit: EmitSink,
) -> tuple[str, dict[str, GuardOutcome], bool, str]:
    """Run each guard over the turn text once.

    Returns the (possibly sanitized) text, the per-guard outcomes, whether any
    guard wants a retry, and the combined reinforcement to append. A
    `text_override` applies sequentially, so a later guard sees the cleaned text.
    """
    outcomes: dict[str, GuardOutcome] = {}
    reinforcements: list[str] = []
    wants_retry = False
    for guard in guards:
        text, asked = _absorb(guard, text, user_message, final=final,
                              request_id=request_id, emit=emit, outcomes=outcomes)
        if asked is not None:
            wants_retry = True
            if asked:
                reinforcements.append(asked)
    return text, outcomes, wants_retry, "\n\n".join(reinforcements)
