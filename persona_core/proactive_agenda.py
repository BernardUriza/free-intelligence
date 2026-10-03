"""Proactive-agenda logic — frame a standing goal for the runner, gate the spam.

The autonomy trigger's brain: given a durable standing agenda (see
`persona_core/memory/repositories/agendas.py`), the proactive drain loop
frames the goal into a runner prompt and decides whether the persona's answer is
worth posting. Both functions here are PURE (no I/O) so the whole
should-it-speak decision is unit-testable without a live runner or DB.

Design intent (why the `NADA` protocol exists): a self-triggering loop that
posts on every wake would flood the channel with filler. The persona is told to
answer with the exact word `NADA` when there is nothing genuinely new — and the
loop reads that as "stay silent this cycle" (`is_nothing_new`). Novelty gates
the post; silence is the default.
"""

from __future__ import annotations

from datetime import datetime

__all__ = ["frame_agenda_prompt", "is_daytime", "is_nothing_new"]

_NOTHING_SENTINEL = "nada"


def is_daytime(moment: datetime, start_hour: int, end_hour: int) -> bool:
    """True when `moment` falls inside the waking window `[start_hour, end_hour)`.

    An agenda speaks UNPROMPTED, so its cadence alone is not enough: a 24h
    cadence that first came due at 03:00 keeps firing at 03:00 forever. Vultur's
    own agenda asked for "horario diurno razonable, no en madrugada" and then
    posted at 02:39 and 02:57 CDMX on consecutive days — the goal said it, no
    code enforced it. Blocked cycles do NOT mark the agenda as run, so it simply
    fires when the window opens.
    """
    return start_hour <= moment.hour < end_hour


def frame_agenda_prompt(goal: str, last_result: str | None = None) -> str:
    """Build the runner prompt that drives one proactive pursuit of `goal`.

    The prompt instructs the persona to (1) investigate/observe novelty NOW via
    web search, (2) speak in its own voice, SHORT, only if there is genuine new
    novelty worth sharing since last time, and (3) answer the exact word `NADA`
    (and nothing else) when there is nothing new — so `is_nothing_new` can gate
    the post and avoid spam. `last_result`, when given, anchors "since last time"
    so the persona doesn't re-report what it already shared.
    """
    lines = [
        f"Esta es tu agenda permanente: {goal}.",
        "Investiga/observa novedades AHORA (WebSearch).",
    ]
    if last_result:
        lines.append(f"La última vez ya compartiste esto (NO lo repitas): {last_result}")
    lines.append(
        "Si hay algo genuinamente NUEVO y digno de compartir desde la última vez, "
        "escríbelo en tu voz, corto. "
        "Si NO hay nada nuevo, responde EXACTAMENTE la palabra `NADA` y nada más "
        "— no inventes para llenar."
    )
    return "\n".join(lines)


def is_nothing_new(text: str) -> bool:
    """True when the persona's answer signals "nothing new" — the loop must NOT
    post. Matches an empty/whitespace answer or the exact `NADA` sentinel
    (case-insensitive, trailing punctuation/quotes tolerated so `nada.`,
    `NADA`, `"nada"` all count). Any real content returns False.
    """
    if not text:
        return True
    stripped = text.strip().strip("`\"'.!¡¿? \t\n").lower()
    return stripped == "" or stripped == _NOTHING_SENTINEL
