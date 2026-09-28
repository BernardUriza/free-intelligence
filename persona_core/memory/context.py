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


SELF_BOT_USER_NAME = "Insult"


def _body_with_reactions(msg: dict) -> str:
    """The row's words plus the gesture its speaker made on the turn.

    A reaction-only turn is stored with ``content=''`` and its emoji in
    ``reactions`` (v4.47.0): rendered as ``reaccionó 👀`` the model reads that it
    ANSWERED, instead of seeing the user's message followed by nothing. A turn
    with words and a reaction keeps both. Rows without reactions render exactly
    as before.
    """
    content = msg.get("content") or ""
    reactions = [str(r).strip() for r in (msg.get("reactions") or []) if str(r).strip()]
    if not reactions:
        return content
    gesture = f"reaccionó {' '.join(reactions)}"
    return f"{content} [{gesture}]" if content else gesture


def build_context(
    recent: list[dict],
    *,
    self_name: str = SELF_BOT_USER_NAME,
) -> list[dict]:
    """Frame the recent turns as the LLM context — the ONE canonical framer.

    Output is the list the messages API expects (`role` + `content`), each
    line speaker-prefixed (`Name: content`). Relevant OLDER retrievals do NOT
    ride here — they travel on the wire's dedicated `relevant_memory` seam
    (see `format_relevant_block`), so old excerpts are never mislabeled as
    the live thread.

    Recent messages from the LAST HOUR get NO timestamp prefix — just
    `Name: content`. Older recent messages keep the `[hace Xmin]` prefix.

    Why: the previous unconditional prefix `[hace 6min] Alex: ...` made
    Sonnet 4.6 hallucinate that recent thread messages were "quotes from
    another session". Verbatim from 2026-05-12 incident: the bot wrote
    "si ya pasaste el CV en otra sesión, esa info no viajó a esta" about
    a message that was 6 minutes old in the SAME thread. The `[time]`
    bracket + "hace Xmin" format looks too much like log/citation
    snippets the model saw during training. Dropping the prefix for the
    fresh window collapses the cue and the model reads them as the live
    thread they actually are.

    `self_name` is the persona reading this context. Its OWN prior turns are
    marked `Name (tú):` so the transcript carries authorship the roles lose
    downstream (the runner flattens the list into one replay block) — without
    the mark, a persona reads its own last reply as just another voice.
    """
    context: list[dict] = []

    # 1 hour window: anything fresher than this gets no temporal prefix
    # because it IS the live conversation. Older recent messages keep the
    # prefix so the model can still tell them apart from now.
    fresh_window_seconds = 3600
    now = time.time()

    for msg in recent:
        # Critical attribution fix: an `assistant` row written by ANOTHER
        # bot (e.g. ALICE) must NOT be passed to the LLM as `role=assistant`
        # — that role is reserved for the SELF bot's previous turns, and
        # the model treats it as "my own past output". When ALICE writes
        # `role=assistant, user_name=ALICE`, the model sees it in its own
        # context and either tries to claim authorship or denies the
        # presence of the sibling ("no soy Alice"). Reframe sibling-bot
        # assistant turns as `role=user` with an explicit speaker prefix
        # so the model reads them as another voice in the room, not as
        # its own history. Discovered v3.9.15 from the Misantla/Costa
        # Esmeralda thread where Insult kept replying "sigo sin ser
        # Alice" after ALICE had already answered.
        msg_role = msg["role"]
        is_self = msg_role == "assistant" and msg.get("user_name") == self_name
        if msg_role == "assistant" and not is_self:
            msg_role = "user"

        speaker = f"{msg['user_name']} (tú)" if is_self else f"{msg['user_name']}"
        body = _body_with_reactions(msg)
        is_fresh = (now - msg["timestamp"]) < fresh_window_seconds
        # Fresh rows get no bracketed prefix — they are the live thread, the
        # active conversation, not quoted snippets.
        content = f"{speaker}: {body}" if is_fresh else f"[{format_relative_time(msg['timestamp'])}] {speaker}: {body}"

        context.append({"role": msg_role, "content": content})

    return context


def format_relevant_block(relevant: list[dict] | None, recent: list[dict]) -> str | None:
    """Render keyword/semantic-retrieved OLDER turns as a labeled excerpt block.

    Travels on the wire's `relevant_memory` seam — NEVER inside the replayed
    live thread, where the runner's framing ("lo que se acaba de decir") would
    tell the model a week-old excerpt was just said. Rows already present in
    the recent window are deduped out; every line keeps its relative-time
    prefix because these are precisely the messages that are NOT now.
    """
    if not relevant:
        return None
    seen_contents = {m.get("content") for m in recent}
    unique = [m for m in relevant if m.get("content") and m.get("content") not in seen_contents]
    if not unique:
        return None
    lines = [
        f"[{format_relative_time(float(m.get('timestamp') or 0))}] {m.get('user_name', '?')}: {m['content']}"
        for m in unique
    ]
    return "Fragmentos más viejos de este canal, relevantes al mensaje actual:\n" + "\n".join(lines)
