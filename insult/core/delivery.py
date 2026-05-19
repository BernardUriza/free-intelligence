"""Response delivery — splitting, chunking, and sending with human-like delays.

Handles the [SEND] multi-message system and Discord's 2000-char limit:
- split_response(): split on [SEND] delimiters into parts
- chunk_text(): break long text into Discord-safe chunks
- send_response(): orchestrate multi-part delivery with typing delays and version tag
"""

import asyncio
import time

import discord
import structlog

from shared.text import (
    DISCORD_MAX_CHARS,
    MESSAGE_DELIMITER,
    chunk_hard,
    split_response,
)

log = structlog.get_logger()

TYPING_CHARS_PER_SECOND = 50  # ~250 CPM, fast mobile typing speed
MIN_TYPING_DELAY = 0.8
MAX_TYPING_DELAY = 5.0
VERSION_TAG = "ᵛ³·⁹·⁶⁵"  # superscript unicode — visible but unobtrusive


# Preserve the legacy module-level name so existing Insult callers and
# tests that import `from insult.core.delivery import chunk_text` keep
# working. `chunk_hard` is the shared canonical name.
chunk_text = chunk_hard

# Re-export DISCORD_MAX_CHARS, MESSAGE_DELIMITER, split_response for the
# same reason. New code should import from `shared.text` directly.
__all__ = [
    "DISCORD_MAX_CHARS",
    "MAX_TYPING_DELAY",
    "MESSAGE_DELIMITER",
    "MIN_TYPING_DELAY",
    "TYPING_CHARS_PER_SECOND",
    "VERSION_TAG",
    "chunk_text",
    "send_response",
    "split_response",
]


async def send_response(
    channel: discord.abc.Messageable,
    response: str,
    *,
    has_side_effects: bool = False,
) -> None:
    """Send a response with [SEND] splitting, chunking, typing delays, and version tag.

    Args:
        channel: Discord channel to send to.
        response: Full response text (may contain [SEND] delimiters).
        has_side_effects: If True and response is empty, don't send fallback "...".
    """
    start = time.monotonic()
    parts = split_response(response)
    if not parts:
        if has_side_effects:
            log.debug(
                "delivery_skipped",
                reason="side_effects_only",
                response_len=len(response),
            )
            return  # Reaction-only or tool-only response
        parts = [response.strip() or "..."]

    total_chars = sum(len(p) for p in parts)
    log.info(
        "delivery_start",
        parts=len(parts),
        total_chars=total_chars,
        response_len=len(response),
        channel_type=type(channel).__name__,
    )

    chunks_sent = 0
    for i, part in enumerate(parts):
        is_last_part = i == len(parts) - 1
        chunks = chunk_text(part)

        for ci, chunk in enumerate(chunks):
            if is_last_part and ci == len(chunks) - 1:
                chunk += f"\n-# {VERSION_TAG}"
            try:
                await channel.send(chunk)
                chunks_sent += 1
            except discord.HTTPException:
                log.exception(
                    "delivery_chunk_failed",
                    part_index=i,
                    chunk_index=ci,
                    chunk_len=len(chunk),
                    chunks_sent=chunks_sent,
                )
                raise

        # Typing delay between parts (not after the last one)
        if not is_last_part:
            next_part = parts[i + 1]
            delay = max(MIN_TYPING_DELAY, min(len(next_part) / TYPING_CHARS_PER_SECOND, MAX_TYPING_DELAY))
            async with channel.typing():
                await asyncio.sleep(delay)

    log.info(
        "delivery_complete",
        parts=len(parts),
        chunks_sent=chunks_sent,
        total_chars=total_chars,
        elapsed_ms=int((time.monotonic() - start) * 1000),
    )
