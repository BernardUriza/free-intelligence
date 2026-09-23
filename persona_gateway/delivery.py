"""Discord message delivery — split a reply to size, tag it, send the pieces.

The pure splitter (`chunk`) is Discord-free and unit-tested. `send_chunked` is
the one place that appends the version tag to the last piece and pushes the
pieces to a channel — it replaced the copy of that exact block that lived in
FOUR call sites (research drain, agenda check, reminder drain, the live turn).
It also records each sent message id → the full untagged reply, so a 🔊 on ANY
piece of a multi-part reply speaks the whole turn, never one chunk with the
version tag read aloud.

`[SEND]` (shared.text.MESSAGE_DELIMITER) splits the reply into separate Discord
messages with a human-pacing delay between them — the multi-message affordance
the persona DNA teaches. The delimiter itself never reaches the channel.
"""

from __future__ import annotations

import asyncio
import re
from collections import OrderedDict

import discord
import structlog

from khimeras_shared.version import VERSION_TAG
from shared.text import split_response

log = structlog.get_logger()

DISCORD_LIMIT = 1990  # leave headroom under Discord's 2000-char message cap
DISCORD_HARD_CAP = 2000  # Discord's absolute per-message limit

_VERSION_TAG_SUFFIX = f"\n-# {VERSION_TAG}"
_ANY_VERSION_TAG = re.compile(r"\n-# ᵛ\S*\s*$")

_FULL_TEXT_CAP = 512
_full_texts: OrderedDict[int, str] = OrderedDict()


def _remember_full_text(message_id: int, text: str) -> None:
    _full_texts[message_id] = text
    _full_texts.move_to_end(message_id)
    while len(_full_texts) > _FULL_TEXT_CAP:
        _full_texts.popitem(last=False)


def full_text_for(message_id: int) -> str | None:
    """The complete untagged reply a sent message belongs to, if still tracked."""
    return _full_texts.get(message_id)


def strip_version_tag(text: str) -> str:
    """Drop the trailing `-# ᵛ…` deploy tag — any version, not just the running
    one, because a 🔊 can land on a message delivered by an older deploy."""
    return _ANY_VERSION_TAG.sub("", text).strip()


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


_PACING_SECONDS_PER_CHAR = 0.02
_PACING_CAP_SECONDS = 2.5


def _pacing_delay(next_part: str) -> float:
    return min(len(next_part) * _PACING_SECONDS_PER_CHAR, _PACING_CAP_SECONDS)


async def send_chunked(channel: discord.abc.Messageable, text: str) -> list[discord.Message]:
    """Split `text` on `[SEND]` and size, tag the last piece, send every piece.

    The single delivery path for every persona reply — live turn, research
    report, agenda finding, reminder. `[SEND]` parts go out as separate messages
    with a typing-paced delay between them; the delimiter is never delivered.
    Empty text sends nothing. Every sent message id is mapped back to the full
    delimiter-free reply for the 🔊 path.
    """
    parts = split_response(text or "")
    if not parts:
        return Delivered()
    full = "\n".join(parts)
    groups = [chunk(part) for part in parts]
    groups[-1] = tag_pieces(groups[-1])
    sent = Delivered()
    for index, group in enumerate(groups):
        if index:
            await asyncio.sleep(_pacing_delay(group[0]))
        for piece in group:
            try:
                message = await channel.send(piece)
            except Exception:
                # Nunca levantar después del primer chunk enviado: el usuario YA
                # vio algo, y un "failed" aquí hacía que el host reintentara el
                # turno entero — la segunda respuesta debajo de la primera.
                if not sent:
                    raise
                sent.partial = True
                log.error("persona_gateway_send_partial", sent=len(sent), pending=len(piece), exc_info=True)
                return sent
            sent.append(message)
            message_id = getattr(message, "id", None)
            if isinstance(message_id, int):
                _remember_full_text(message_id, full)
    return sent


class Delivered(list):
    """Los mensajes que sí salieron. `partial` = el envío se cortó a medias."""

    partial: bool = False
