"""The turn's in-band framing — what the model reads around the ask.

The brain reads ONE user message. Everything a turn knows besides the ask has to
ride inside it as labeled blocks, in a fixed order:

1. ``<current_time>`` — first and never cached, because it changes every minute.
2. ``<relevant_memory>`` — older retrievals and ask-relevant facts.
3. ``<other_people_in_channel>`` — facts about the people being talked about.
4. ``<recent_conversation>`` — the live thread, closest to the ask.

This lived inside the gateway's HTTP client (``AgentRunnerClient.chat``) until
2026-09-28, so only Discord turns were framed. It moved here with F3 so the
runner's own pipeline frames og118 turns with the same code — one framing, every
surface.
"""

from __future__ import annotations

import structlog

from shared.time_context import _get_current_time_context

log = structlog.get_logger()

# How much of the prior channel conversation to replay. The brain keeps only
# its own session, so it is blind to what OTHER participants just said.
# Concrete failure (2026-06-05, #general): Bernard names the film "Creep" in his
# own message; seconds later Alex says "me dio ptsd la peli" WITHOUT naming it;
# her turn never saw Bernard's line, so the bot answered "¿cuál peli?".
RECENT_CONTEXT_MAX_MESSAGES = 25
RECENT_CONTEXT_MAX_CHARS = 3500

# What the model reads when a turn carries only attachments.
ATTACHMENT_ONLY_ASK = "[adjuntó solo imagen]"


def format_recent_context(messages: list[dict]) -> str:
    """Render the messages BEFORE the current one as a transcript.

    `messages` is the turn's context list with the current message LAST; each
    prior entry's `content` is already speaker-prefixed ("Bernard: ya
    terminamos"). Returns "" when there is nothing prior to replay.
    """
    if not messages or len(messages) <= 1:
        return ""
    tail = messages[:-1][-RECENT_CONTEXT_MAX_MESSAGES:]
    lines: list[str] = []
    for m in tail:
        content = m.get("content", "")
        if isinstance(content, list):
            content = "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
        if isinstance(content, str) and content.strip():
            lines.append(content.strip())
    if not lines:
        return ""
    transcript = "\n".join(lines)
    if len(transcript) > RECENT_CONTEXT_MAX_CHARS:
        # Keep the freshest tail — truncate from the front.
        transcript = "…\n" + transcript[-RECENT_CONTEXT_MAX_CHARS:]
    return transcript


def compose_user_text(
    ask: str,
    messages: list[dict],
    *,
    relevant_memory: str | None = None,
    other_people: str | None = None,
) -> str:
    """The single user message the brain reads: framing blocks, then the ask.

    `messages` is the same context list `format_recent_context` takes (current
    message last). An empty `ask` means the turn carries only attachments.
    """
    blocks = [f"<current_time>\n{_get_current_time_context()} — America/Mexico_City\n</current_time>"]
    if relevant_memory:
        blocks.append(f"<relevant_memory>\n{relevant_memory}\n</relevant_memory>")
    if other_people:
        blocks.append(f"<other_people_in_channel>\n{other_people}\n</other_people_in_channel>")
    recent_context = format_recent_context(messages)
    if recent_context:
        blocks.append(
            "<recent_conversation>\n"
            "Lo que se acaba de decir en este canal (incluye a otras personas). "
            'Úsalo para resolver referencias como "la peli", "eso", "el de antes" — '
            "NO vuelvas a preguntar qué es algo que ya se nombró aquí.\n"
            f"{recent_context}\n</recent_conversation>"
        )
        log.info("turn_recent_context_framed", context_chars=len(recent_context))
    return "\n\n".join([*blocks, ask or ATTACHMENT_ONLY_ASK])
