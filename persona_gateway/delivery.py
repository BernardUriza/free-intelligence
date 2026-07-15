"""Discord message delivery — split a reply to size, tag it, send the pieces.

The pure splitter (`chunk`) is Discord-free and unit-tested. `send_chunked` is
the one place that appends the version tag to the last piece and pushes the
pieces to a channel — it replaced the copy of that exact block that lived in
FOUR call sites (research drain, agenda check, reminder drain, the live turn).
"""

from __future__ import annotations

import discord

from khimeras_shared.version import VERSION_TAG

DISCORD_LIMIT = 1990  # leave headroom under Discord's 2000-char message cap
DISCORD_HARD_CAP = 2000  # Discord's absolute per-message limit

_VERSION_TAG_SUFFIX = f"\n-# {VERSION_TAG}"


def chunk(text: str, limit: int = DISCORD_LIMIT) -> list[str]:
    """Split a reply into Discord-sized pieces on paragraph/space boundaries."""
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= limit:
        return [text]
    parts: list[str] = []
    remaining = text
    while len(remaining) > limit:
        cut = remaining.rfind("\n", 0, limit)
        if cut < limit // 2:
            cut = remaining.rfind(" ", 0, limit)
        if cut < limit // 2:
            cut = limit
        parts.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()
    if remaining:
        parts.append(remaining)
    return parts


def tag_pieces(pieces: list[str]) -> list[str]:
    """Append the deploy version tag to the last piece iff it still fits the cap.

    The tag rides ONLY the final message (so a multi-part reply is tagged once)
    and only when it fits — a piece already at the hard cap is left untagged
    rather than overflowing.
    """
    if pieces and len(pieces[-1]) + len(_VERSION_TAG_SUFFIX) <= DISCORD_HARD_CAP:
        pieces[-1] += _VERSION_TAG_SUFFIX
    return pieces


async def send_chunked(channel: discord.abc.Messageable, text: str) -> None:
    """Split `text`, tag the last piece, and send every piece to `channel`.

    The single delivery path for every persona reply — live turn, research
    report, agenda finding, reminder. Empty text sends nothing.
    """
    pieces = tag_pieces(chunk(text))
    for piece in pieces:
        await channel.send(piece)
