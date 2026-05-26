"""Guard-list executor — runs every guard once and aggregates outcomes.

Extracted from :class:`Runner` so the logic is pure-functional (takes
guards + text + sink, returns the aggregate) and unit-testable without
spinning up a backend or a full Runner. The Runner itself is the
orchestrator (it decides WHEN to call this, based on retry policy +
final-attempt flag); this module is the WHAT (run them, collect outcomes,
escalate CRITICAL signals)."""

from __future__ import annotations

from .guards import Guard, GuardOutcome
from ._flow_delivery import EmitSink


def run_guards(
    guards: list[Guard],
    text: str,
    user_message: str,
    *,
    final: bool,
    request_id: str | None = None,
    emit: EmitSink,
) -> tuple[str, dict[str, GuardOutcome], bool, str]:
    """Run each guard over the turn text once. Returns the (possibly
    sanitized) text, the per-guard outcomes, whether any guard wants a retry,
    and the combined reinforcement to append. ``text_override`` is applied
    sequentially so a later guard sees the cleaned text. Emits
    ``guard_critical`` when a guard flags a CRITICAL outcome via ``emit``
    (the per-turn sink, so guard events also reach the turn-flow buffer)."""
    outcomes: dict[str, GuardOutcome] = {}
    reinforcement_parts: list[str] = []
    wants_retry = False
    for guard in guards:
        # `or repr(guard)` is lazy — repr (expensive for guards holding
        # compiled-pattern lists) only runs if a guard has no `.name`.
        name = getattr(guard, "name", None) or repr(guard)
        try:
            outcome = guard.inspect(response_text=text, context=(user_message,), final=final)
        except Exception as exc:  # noqa: BLE001 - a guard is a safety NET, not a
            # single point of failure: if it raises (e.g. a malformed regex),
            # log + skip it and keep the backend's valid text rather than
            # crashing the whole turn.
            emit("guard_error", {"guard": name, "error": str(exc)})
            outcomes[name] = GuardOutcome(metadata={"guard_failed": True, "error": str(exc)})
            continue
        outcomes[name] = outcome
        if outcome.metadata.get("critical") is True or outcome.metadata.get("level") == "CRITICAL":
            # A guaranteed safety signal (e.g. triage escalating a suicide
            # plan) must SURFACE as telemetry so a consumer can alert/escalate,
            # even for an observational guard that never edits the text.
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
        if outcome.text_override is not None:
            text = outcome.text_override
        if outcome.retry:
            wants_retry = True
            if outcome.reinforcement:
                reinforcement_parts.append(outcome.reinforcement)
    return text, outcomes, wants_retry, "\n\n".join(reinforcement_parts)


def guard_level(metadata: dict) -> str:
    """A single representative level for a guard outcome, for telemetry."""
    if metadata.get("guard_failed"):
        return "error"
    return metadata.get("level") or metadata.get("severity") or "ok"


__all__ = ["run_guards", "guard_level"]
