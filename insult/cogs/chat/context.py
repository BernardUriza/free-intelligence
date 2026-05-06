"""Conversation-context and user-facts loading for a single turn.

Pure async helpers. No state of their own — everything comes from the
`memory` store and `settings` passed in. `cog.py` owns the MemoryStore and
hands it to `turn.run_turn` which forwards it here.

Each helper owns its own try/except + structured log so `run_turn` reads
as a sequence of awaits without the inline boilerplate it used to carry.
Failures degrade to safe defaults (empty list, empty dict, None) so a
single broken read never aborts the turn — the bot still responds, just
with reduced context.
"""

from __future__ import annotations

import time

import discord
import structlog

from insult.core.image_summary import summarize_images
from insult.core.summaries import build_server_pulse, filter_by_permissions

log = structlog.get_logger()


async def build_context(
    memory,
    settings,
    channel_id: str,
    text: str,
    attachment_blocks: list,
) -> tuple[list[dict] | None, list[dict]]:
    """Return (context, recent) or (None, []) on memory failure.

    `recent` is the raw last-N messages used for flow analysis + shape
    selection. `context` is the merged recent+relevant list formatted as
    Anthropic MessageParam dicts, with the user's current attachments
    spliced into the last user message when present.
    """
    try:
        recent = await memory.get_recent(channel_id, settings.memory_recent_limit)
        relevant = await memory.search(channel_id, text, settings.memory_relevant_limit)
        context = memory.build_context(recent, relevant)
    except Exception:
        log.exception("chat_context_failed", channel_id=channel_id)
        return None, []

    if attachment_blocks and context:
        last_msg = context[-1]
        if last_msg["role"] == "user":
            text_block = {"type": "text", "text": last_msg["content"]}
            context[-1] = {"role": "user", "content": [text_block, *attachment_blocks]}

    return context, recent


async def load_facts(memory, user_id: str) -> list[dict]:
    """Return all user facts, or [] on failure."""
    try:
        return await memory.get_facts(user_id)
    except Exception:
        log.exception("chat_facts_load_failed", user_id=user_id)
        return []


async def load_facts_smart(memory, user_id: str, query: str) -> list[dict]:
    """Like `load_facts` but uses semantic search when the user has 6+ facts.

    Below 6 facts the full list is cheap to inject; above that we filter
    by relevance to the current query to keep the system prompt lean and
    improve preset/flow routing signal.
    """
    try:
        all_facts = await memory.get_facts(user_id)
    except Exception:
        log.exception("chat_facts_load_failed", user_id=user_id)
        return []

    if len(all_facts) > 5:
        try:
            return await memory.search_facts_semantic(user_id, query, limit=10)
        except Exception:
            log.exception("chat_facts_semantic_failed", user_id=user_id)
            return all_facts

    return all_facts


async def store_user_message(
    memory,
    channel_id: str,
    user_id: str,
    user_name: str,
    text_for_memory: str,
    guild_id: str | None,
    channel_name: str | None,
) -> None:
    """Persist the user's message. Logs and swallows on failure."""
    try:
        await memory.store(
            channel_id,
            user_id,
            user_name,
            "user",
            text_for_memory,
            guild_id=guild_id,
            channel_name=channel_name,
        )
    except Exception:
        log.exception("chat_store_user_failed", channel_id=channel_id)


async def store_assistant_message(
    memory,
    channel_id: str,
    bot_user_id: str,
    bot_user_name: str,
    clean_response: str,
    *,
    for_user_id: str,
    guild_id: str | None,
    channel_name: str | None,
    model_used: str | None,
) -> None:
    """Persist the bot's response. Logs and swallows on failure."""
    try:
        await memory.store(
            channel_id,
            bot_user_id,
            bot_user_name,
            "assistant",
            clean_response,
            for_user_id=for_user_id,
            guild_id=guild_id,
            channel_name=channel_name,
            model_used=model_used,
        )
    except Exception:
        log.exception("chat_store_response_failed", channel_id=channel_id)


async def summarize_user_images_into_text(
    image_blocks: list,
    llm,
    summary_model: str,
    base_text: str,
) -> str:
    """Run image summarization and return the augmented text-for-memory.

    On success returns ``base_text + [Imagen: <summary>]`` (or just the
    image suffix when ``base_text`` is empty). On failure returns
    ``base_text`` unchanged so the turn keeps moving — image-summary is
    best-effort context, not load-bearing.
    """
    if not image_blocks:
        return base_text
    started = time.monotonic()
    try:
        summary = await summarize_images(image_blocks, llm=llm, model=summary_model)
        log.info(
            "image_summary_ok",
            duration_ms=int((time.monotonic() - started) * 1000),
            image_count=len(image_blocks),
            summary_len=len(summary or ""),
            summary_preview=(summary or "")[:120],
        )
        if summary:
            return f"{base_text}\n[Imagen: {summary}]" if base_text else f"[Imagen: {summary}]"
        return base_text
    except Exception:
        log.exception(
            "image_summary_wrapper_failed",
            duration_ms=int((time.monotonic() - started) * 1000),
            image_count=len(image_blocks),
        )
        return base_text


async def update_style_profile(memory, user_id: str, text: str):
    """Update the user's style profile. Returns profile or None on failure."""
    try:
        return await memory.update_profile(user_id, text)
    except Exception:
        log.exception("chat_profile_update_failed", user_id=user_id)
        return None


async def load_other_participants_facts(
    memory,
    channel_id: str,
    user_id: str,
) -> dict[str, list[dict]]:
    """Top-3 facts for up to 9 other recent participants in the channel.

    Powers the "Other People in This Channel" prompt block. Returns {} on
    failure so missing context never breaks the turn.
    """
    out: dict[str, list[dict]] = {}
    try:
        participants = await memory.get_channel_participants(channel_id, limit=10)
        for p in participants:
            if p["user_id"] != user_id:
                facts = await memory.get_facts(p["user_id"])
                if facts:
                    out[p["user_name"]] = facts[:5]
    except Exception:
        log.exception("chat_participants_facts_failed")
    return out


async def load_server_pulse(
    memory,
    message: discord.Message,
    channel_id: str,
    text: str,
) -> str:
    """Cross-channel awareness blurb, filtered by the author's read perms.

    Returns "" when there's no guild, no other-channel summaries, or on
    error. Keeps the read-permission filter local so the caller doesn't
    need to know which channels the user can see.
    """
    if not message.guild:
        return ""
    try:
        summaries = await memory.get_channel_summaries(
            str(message.guild.id),
            exclude_channel_id=channel_id,
        )
        if not summaries:
            return ""
        accessible = {
            str(ch.id) for ch in message.guild.text_channels if ch.permissions_for(message.author).read_messages
        }
        summaries = filter_by_permissions(summaries, accessible)
        return build_server_pulse(summaries, text)
    except Exception:
        log.exception("chat_server_pulse_failed", guild_id=str(message.guild.id))
        return ""
