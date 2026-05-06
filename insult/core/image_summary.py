"""Generate short text descriptions of image attachments for long-term memory.

The main LLM turn already uses Claude vision directly and sees the raw image.
This module exists so that in future turns — when the conversation context is
rebuilt from SQLite, which only stores text — Claude still has a trace of what
images appeared earlier. Without it, a user who says "what about the second
image?" on a later turn hits a bot that has no record the image ever existed.

One Haiku call per message with images. Best-effort: on any failure we return
None and the caller falls back to storing the plain text.
"""

from __future__ import annotations

import structlog

log = structlog.get_logger()

SUMMARY_TIMEOUT = 15.0
SUMMARY_MAX_TOKENS = 200

_PROMPT = (
    "Describe each image in ONE short sentence (max 20 words). "
    "Be concrete: subject, obvious details, any visible text. "
    "No preamble, no commentary. One line per image, numbered like '1. ...'."
)


async def summarize_images(
    image_blocks: list[dict],
    *,
    llm,
    model: str,
) -> str | None:
    """Return a short textual description of the image(s), or None on failure.

    Input: list of Claude API image content blocks (type="image"). Packs
    them into a single Haiku call via LLMClient.utility_call and returns
    the combined description. Goes through the wrapper for retry policy
    and prompt caching — the system _PROMPT is identical across every
    call, so cache hit pays off after one image-bearing message.
    """
    if not image_blocks:
        return None

    try:
        response = await llm.utility_call(
            _PROMPT,
            [{"role": "user", "content": image_blocks}],
            model=model,
            max_tokens=SUMMARY_MAX_TOKENS,
        )
    except Exception as e:
        log.warning("image_summary_failed", error=str(e), error_type=type(e).__name__)
        return None

    text = response.text.strip()
    if text:
        log.info("image_summary_generated", count=len(image_blocks), length=len(text))
        return text

    log.warning("image_summary_empty", count=len(image_blocks))
    return None
