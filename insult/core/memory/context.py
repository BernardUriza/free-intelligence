"""Pure functions for rendering conversation context into LLM-ready blocks.

These belong in their own module because they have zero DB dependency — the
repositories hand them `list[dict]` rows and they produce `list[dict]`
message blocks. Extracted from the monolithic MemoryStore so that prompt-
building code can import just the formatter without dragging in SQLite.
"""

from __future__ import annotations

import time


def format_relative_time(timestamp: float) -> str:
    """Convert a Unix timestamp into a human-readable relative-time phrase.

    Spanish-first because the persona speaks Spanish. The boundaries
    ("justo ahora", "hace 2h", "ayer", "hace 3 días") are deliberately
    chosen so the LLM can feel time passing without needing exact clocks —
    which are deprioritized by the persona rules ("don't announce timestamps").
    """
    now = time.time()
    diff = now - timestamp

    if diff < 60:
        return "justo ahora"
    if diff < 3600:
        mins = int(diff / 60)
        return f"hace {mins}min"
    if diff < 86400:
        hours = int(diff / 3600)
        return f"hace {hours}h"
    days = int(diff / 86400)
    if days == 1:
        return "ayer"
    if days < 7:
        return f"hace {days} días"
    if days < 30:
        weeks = int(days / 7)
        return f"hace {weeks} sem"
    return f"hace {int(days / 30)} meses"


def build_context(recent: list[dict], relevant: list[dict] | None = None) -> list[dict]:
    """Assemble the LLM context: recent turns + relevant retrievals.

    Output is the list the messages API expects (`role` + `content`).
    The "relevant" block is prepended as ONE synthetic user message with a
    header marker so the model knows these are older excerpts, not the live
    thread.

    Recent messages from the LAST HOUR get NO timestamp prefix — just
    `Name: content`. Older recent messages and all relevant retrievals keep
    the `[hace Xmin] Name: content` prefix.

    Why: the previous unconditional prefix `[hace 6min] Alex: ...` made
    Sonnet 4.6 hallucinate that recent thread messages were "quotes from
    another session". Verbatim from 2026-05-12 incident: the bot wrote
    "si ya pasaste el CV en otra sesión, esa info no viajó a esta" about
    a message that was 6 minutes old in the SAME thread. The `[time]`
    bracket + "hace Xmin" format looks too much like log/citation
    snippets the model saw during training. Dropping the prefix for the
    fresh window collapses the cue and the model reads them as the live
    thread they actually are.
    """
    context: list[dict] = []

    # 1 hour window: anything fresher than this gets no temporal prefix
    # because it IS the live conversation. Older recent messages keep the
    # prefix so the model can still tell them apart from now.
    fresh_window_seconds = 3600
    now = time.time()

    if relevant:
        seen_contents = {m["content"] for m in recent}
        unique_relevant = [m for m in relevant if m["content"] not in seen_contents]
        if unique_relevant:
            context.append(
                {
                    "role": "user",
                    "content": "[Contexto relevante de conversaciones anteriores]\n"
                    + "\n".join(
                        f"[{format_relative_time(m['timestamp'])}] {m['user_name']}: {m['content']}"
                        for m in unique_relevant
                    ),
                }
            )

    for msg in recent:
        is_fresh = (now - msg["timestamp"]) < fresh_window_seconds
        if is_fresh:
            # No bracketed prefix — these are the live thread, treat them
            # as the active conversation, not as quoted snippets.
            content = f"{msg['user_name']}: {msg['content']}"
        else:
            ts = f"[{format_relative_time(msg['timestamp'])}] "
            content = f"{ts}{msg['user_name']}: {msg['content']}"
        # Both user and assistant messages get name prefix for clear speaker
        # attribution — downstream character.strip_metadata() removes these
        # before the text reaches Discord.
        context.append({"role": msg["role"], "content": content})

    return context
