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

log = structlog.get_logger()

MESSAGE_DELIMITER = "[SEND]"
DISCORD_MAX_CHARS = 1990  # Leave room for version tag
TYPING_CHARS_PER_SECOND = 50  # ~250 CPM, fast mobile typing speed
MIN_TYPING_DELAY = 0.8
MAX_TYPING_DELAY = 5.0
VERSION_TAG = "ᵛ³·⁷·⁶⁹"  # superscript unicode — visible but unobtrusive


def split_response(response: str) -> list[str]:
    """Split response on [SEND] delimiters, stripping empty parts."""
    return [p.strip() for p in response.split(MESSAGE_DELIMITER) if p.strip()]


def chunk_text(text: str, max_chars: int = DISCORD_MAX_CHARS) -> list[str]:
    """Break long text into Discord-safe chunks."""
    return [text[j : j + max_chars] for j in range(0, len(text), max_chars)]


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
