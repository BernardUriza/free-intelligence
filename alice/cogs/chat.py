"""ALICE's chat cog — passive listener, fires only when invited.

Two activation paths:

1. **Discord @mention**: any user types `@ALICE` (Discord native mention).
   The cog listens to `on_message`, ignores messages that don't tag ALICE,
   and responds when she IS tagged.

2. **Insult REST invite**: the FastAPI `/invite` endpoint (see
   `alice/api/server.py`) calls `respond_to_invite()` directly. That
   path bypasses Discord's event loop because it's already in an
   asyncio context.

ALICE deliberately does NOT respond to every channel message the way
Insult does. The whole point of her existence is that she's a presence
you ask for — not a voice that talks over the conversation.
"""

from __future__ import annotations

import asyncio

import discord
import structlog
from discord.ext import commands

from alice.core.llm import AliceLLMClient
from alice.core.memory import AliceMemory
from alice.core.persona_loader import PersonaLoader
from shared.text import chunk_paragraph_aware

log = structlog.get_logger()


class AliceChatCog(commands.Cog):
    """Discord listener + invite handler."""

    def __init__(
        self,
        bot: commands.Bot,
        memory: AliceMemory,
        llm: AliceLLMClient,
        persona: PersonaLoader,
    ):
        self.bot = bot
        self.memory = memory
        self.llm = llm
        self.persona = persona

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Respond only when ALICE is mentioned by name or @-tag."""
        # Every inbound message gets a debug breadcrumb so we can prove
        # the listener is firing even when the decision is "ignore". Without
        # this, "no response" is indistinguishable from "listener never
        # ran" in production logs.
        log.info(
            "alice_on_message",
            author_bot=message.author.bot if message.author else None,
            content_len=len(message.content or ""),
            content_preview=(message.content or "")[:60],
            mention_count=len(message.mentions),
            bot_user_id=str(self.bot.user.id) if self.bot.user else None,
            mentions_ids=[str(u.id) for u in message.mentions],
            guild_id=str(message.guild.id) if message.guild else None,
            channel_id=str(message.channel.id),
        )

        if message.author == self.bot.user:
            log.debug("alice_skip_self")
            return

        # In a guild channel: respond ONLY when canonically @mentioned (so
        # ALICE doesn't talk over conversations she wasn't invited to).
        # In a DM: respond to every message — the user is literally already
        # talking to her one-on-one, no opt-in needed. "Su app individual"
        # in the user's words.
        is_dm = message.guild is None
        if not is_dm:
            mentioned_as_user = self.bot.user in message.mentions if self.bot.user else False
            mentioned_as_text = "@ALICE" in message.content or "@alice" in message.content
            if not (mentioned_as_user or mentioned_as_text):
                log.debug(
                    "alice_skip_no_mention",
                    mentioned_as_user=mentioned_as_user,
                    mentioned_as_text=mentioned_as_text,
                )
                return

        invited_by = "dm" if is_dm else "user_mention"
        log.info(
            "alice_responding",
            is_dm=is_dm,
            invited_by=invited_by,
            channel_id=str(message.channel.id),
        )

        # Persist the inbound message in DMs. In server channels Insult
        # already wrote the row, so we skip there to avoid duplicates.
        if is_dm and message.content:
            try:
                await self.memory.store_user_message(
                    channel_id=str(message.channel.id),
                    user_id=str(message.author.id),
                    user_name=message.author.display_name or message.author.name,
                    content=message.content,
                    guild_id=None,
                    channel_name=None,
                )
            except Exception as e:
                log.warning("alice_persist_user_failed", error=str(e))

        # Show typing while we think — Discord drops the indicator after ~10s
        # so we wrap the entire respond cycle in it (Insult uses the same
        # pattern in cogs/chat.py).
        async with message.channel.typing():
            await self._respond(
                channel=message.channel,
                channel_id=str(message.channel.id),
                guild_id=str(message.guild.id) if message.guild else None,
                channel_name=getattr(message.channel, "name", None),
                user_msg=message.content,
                invited_by=invited_by,
            )

    async def respond_to_invite(
        self,
        *,
        channel_id: str,
        guild_id: str | None,
        channel_name: str | None,
        reason: str,
        invited_by: str = "insult_rest",
    ) -> str:
        """Entry point for the FastAPI /invite handler.

        Insult passes `reason` (free-text reason why ALICE was called)
        so ALICE can decide where to focus. The reason is treated as
        instruction context, not as user input — it doesn't go into
        the visible conversation thread.
        """
        channel = self.bot.get_channel(int(channel_id))
        if channel is None:
            log.warning("alice_invite_channel_not_found", channel_id=channel_id)
            return f"Channel {channel_id} not reachable from ALICE."

        return await self._respond(
            channel=channel,
            channel_id=channel_id,
            guild_id=guild_id,
            channel_name=channel_name,
            user_msg=None,
            invite_reason=reason,
            invited_by=invited_by,
        )

    async def _respond(
        self,
        *,
        channel: discord.abc.Messageable,
        channel_id: str,
        guild_id: str | None,
        channel_name: str | None,
        user_msg: str | None,
        invite_reason: str | None = None,
        invited_by: str = "user_mention",
    ) -> str:
        """Shared response builder for both entry points.

        Steps:
        1. Pull recent messages (Insult + everyone's history) from PG.
        2. Optionally append the `invite_reason` from Insult as a
           system-level hint at the END of the messages list, so it's
           the freshest context the model sees.
        3. Send to GPT-4.1.
        4. Post the reply in Discord.
        5. Persist the reply into the shared messages table.
        """
        recent = await self.memory.get_recent_messages(channel_id)

        if invite_reason:
            recent.append(
                {
                    "role": "system",
                    "content": (
                        f"[Insult te invitó a este turno. Razón: {invite_reason}] "
                        "Lee el hilo arriba y responde con la mirada que esa razón pide."
                    ),
                }
            )
        elif user_msg:
            # @mention path: the user's current message IS the last item
            # already because we just read it from PG (Insult writes it).
            # But to be safe in case PG hasn't flushed yet, ensure it's there.
            already_present = any(m["role"] == "user" and m["content"].endswith(user_msg[-50:]) for m in recent[-3:])
            if not already_present:
                recent.append({"role": "user", "content": user_msg})

        system_prompt = self.persona.load()

        try:
            response = await self.llm.chat(system_prompt, recent)
        except Exception as e:
            log.exception("alice_response_failed", invited_by=invited_by, error=str(e))
            await channel.send("Tuve un problema procesando esto. Vuelve a llamarme en un momento.")
            return ""

        text = response.text.strip()
        if not text:
            log.warning("alice_empty_response", model=response.model)
            await channel.send("…")
            return ""

        # Chunk to Discord's 2000-char limit (we leave buffer for safety).
        for chunk in chunk_paragraph_aware(text, max_chars=1900):
            try:
                await channel.send(chunk)
            except discord.HTTPException as e:
                log.exception("alice_send_failed", error=str(e))
                break
            await asyncio.sleep(0.2)  # human-like pacing between chunks

        # Persist (best-effort — log on failure, don't crash the turn).
        try:
            await self.memory.store_response(
                channel_id=channel_id,
                content=text,
                guild_id=guild_id,
                channel_name=channel_name,
            )
        except Exception as e:
            log.warning("alice_persist_failed", error=str(e))

        log.info(
            "alice_turn_complete",
            invited_by=invited_by,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            latency_ms=response.latency_ms,
            chars=len(text),
        )
        return text
