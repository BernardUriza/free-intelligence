"""Persist a textual transcript of image attachments into longitudinal memory.

The agent runner has native vision INSIDE the live turn, but Postgres only
stores text — an image-only message lands as an empty row and every future
turn rebuilds context with zero trace of what the image contained. The
predecessor (`image_summary.py`, deleted v4.18.0) was deprecated on the
assumption that the runner's own reply describes the image well enough to
serve as the future-turn trace; 2026-07-05 disproved it — the in-character
reply carries commentary, not content, so a prescription/treatment schedule
sent "mil veces" was re-hallucinated every time.

This module is the durable trace: one best-effort /v1/judge vision call per
image-bearing message, appended to the already-stored row via its
discord_message_id. Failures never touch the turn — the row simply keeps
its raw text.
"""

from __future__ import annotations

import structlog

from personas.insult.core.prompts_loader import load_prompt

log = structlog.get_logger()

TRANSCRIPT_MAX_TOKENS = 1500
TRANSCRIPT_MAX_CHARS = 4000

_USER_TEXT = "Transcribe la(s) imagen(es) adjunta(s)."


async def transcribe_images(
    image_blocks: list[dict],
    *,
    judge_client,
    model: str | None = None,
) -> str | None:
    """Return a faithful transcript/description of the image(s), or None.

    Input: Anthropic-shape image content blocks (type="image"). Best-effort:
    any failure logs and returns None so the caller falls back to the plain
    stored text.
    """
    if not image_blocks:
        return None

    try:
        response = await judge_client.utility_call(
            load_prompt("image_transcription"),
            [{"role": "user", "content": [{"type": "text", "text": _USER_TEXT}, *image_blocks]}],
            model=model,
            max_tokens=TRANSCRIPT_MAX_TOKENS,
        )
    except Exception as e:
        log.warning("image_transcript_failed", error=str(e), error_type=type(e).__name__)
        return None

    text = (response.text or "").strip()
    if not text:
        log.warning("image_transcript_empty", count=len(image_blocks))
        return None
    if len(text) > TRANSCRIPT_MAX_CHARS:
        text = text[:TRANSCRIPT_MAX_CHARS]
    log.info("image_transcript_generated", count=len(image_blocks), length=len(text))
    return text


async def persist_image_transcript(
    judge_client,
    memory,
    discord_message_id: str,
    image_blocks: list[dict],
    *,
    model: str | None = None,
) -> None:
    """Background task: transcribe, then append to the stored message row.

    Keys the append on discord_message_id so it lands no matter which
    writer (Insult plumbing or a persona_gateway sibling) won the deduped
    insert for this message.
    """
    transcript = await transcribe_images(image_blocks, judge_client=judge_client, model=model)
    if not transcript:
        return

    try:
        appended = await memory.append_to_message(discord_message_id, f"[Imagen adjunta: {transcript}]")
    except Exception:
        log.exception("image_transcript_append_failed", discord_message_id=discord_message_id)
        return

    log.info(
        "image_transcript_persisted",
        discord_message_id=discord_message_id,
        appended=appended,
        length=len(transcript),
    )
