"""ALICE's chat cog — listens for mentions, aliases, and intrusive triggers.

Activation paths:

1. **Discord @mention**: user types `@ALICE` (user-mention) OR the
   Discord client substitutes the bot's auto-created role mention
   `<@&role_id>` (autocomplete UX). Both count.

2. **Alias in text**: lowercase "amix" / "ali" / "alicia" anywhere in
   the message body — Bernard's pet names for ALICE.

3. **Intrusive clinical mode** (v3.9.41+): when the message contains a
   clinical-disclosure keyword (CPTSD, quetiapina, psiquiatra, etc.) AND
   the channel context suggests ALICE's register fits better, she enters
   without explicit invitation. High-precision keyword list — false
   positives mean ALICE talks over Insult's roast, so we keep it tight.

4. **Insult REST invite**: the FastAPI `/invite` endpoint calls
   `respond_to_invite()` directly.

Historical: pre-v3.9.41 ALICE was pure mention-only and the role-mention
fallback (`<@&...>` + literal "alice" in text) silently failed because
Discord's autocomplete REPLACES the literal "alice" with the raw role
mention. Bernard reported "Alex la mencionó y no respondió" — that's
the bug being fixed here. See plan
`.claude/plans/sibling_bot_coexistence.md` addendum 2026-05-18.
"""

from __future__ import annotations

import asyncio
import re

import discord
import structlog
from discord.ext import commands

from alice.config import settings as alice_settings
from alice.core.llm import AliceLLMClient
from alice.core.memory import AliceMemory
from alice.core.persona_loader import PersonaLoader
from shared.corpus import animal_liberation_guidance, animal_tactics_guidance
from shared.text import chunk_paragraph_aware

log = structlog.get_logger()


# Clinical-disclosure keywords that trigger intrusive mode (ALICE responds
# without explicit @mention). Tight, high-precision list — false positives
# = ALICE talking over Insult's roast. Mirror of triggers in Insult's
# persona.md ("Triggers OBLIGATORIOS para invocar invoke_alice").
_CLINICAL_KEYWORDS_PATTERN = re.compile(
    r"\b(cptsd|tept|tlp|borderline|"
    r"quetiapina|sertralina|fluoxetina|escitalopram|alprazolam|clonazepam|"
    r"psiquiatra|psicólog[oa]|terapeuta|"
    r"crisis\s+(de\s+ansiedad|aguda|psiqui)|"
    r"ataque\s+de\s+(pánico|panico)|"
    r"ideación|ideacion|"
    r"hospitalización\s+psiqui|hospitalizacion\s+psiqui|"
    r"internamiento\s+psiqui|"
    r"intent[oé]\s+suicid)",
    re.IGNORECASE,
)


def _detect_alias_mention(content: str, aliases: list[str]) -> str | None:
    """Return the matched alias if any appears as a word in `content`.

    Word-boundary match so "amix" matches but "amixaco" does not. Common
    Bernard usage: "holiii amix", "que opinas ali", "alicia, ven".
    """
    if not content:
        return None
    lowered = content.lower()
    for alias in aliases:
        if re.search(rf"\b{re.escape(alias.lower())}\b", lowered):
            return alias
    return None


def _detect_role_mention_for_bot(message: discord.Message, bot_user: discord.ClientUser | None) -> bool:
    """True if message contains a `<@&role_id>` that points to ALICE's auto-created role.

    Discord auto-creates a managed role for every bot the moment it joins
    a guild. When a user picks ALICE from @-autocomplete, Discord often
    inserts the role mention (`<@&role_id>`) instead of the user mention
    (`<@user_id>`). discord.py's `message.role_mentions` only populates
    if the bot has `members` intent (privileged) — we don't request that.

    Workaround: walk the guild's role list at runtime, find the managed
    role whose `bot_id` is OUR bot, and check its ID against the raw
    `<@&...>` IDs in the message content. Works without privileged
    intents.
    """
    if bot_user is None or message.guild is None:
        return False

    raw_role_ids = set(re.findall(r"<@&(\d+)>", message.content or ""))
    if not raw_role_ids:
        return False

    for role in message.guild.roles:
        # `role.tags` is populated for managed roles (bot, integration,
        # premium subscriber). `bot_id` matches the bot the role manages.
        tags = getattr(role, "tags", None)
        if tags is not None and getattr(tags, "bot_id", None) == bot_user.id and str(role.id) in raw_role_ids:
            return True
    return False


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

        # In a guild channel: respond on multiple signals (mention, alias,
        # clinical-intrusive). In a DM: respond to every message — the
        # user is literally already talking to her 1:1, no opt-in needed.
        is_dm = message.guild is None
        mentioned_as_user = False
        mentioned_as_text = False
        mentioned_as_role = False
        mentioned_as_alias = None
        intrusive_match = None
        invited_by = "dm" if is_dm else None

        if not is_dm:
            mentioned_as_user = self.bot.user in message.mentions if self.bot.user else False
            mentioned_as_text = "@ALICE" in message.content or "@alice" in message.content
            # Fix v3.9.41: detect ALICE's managed role via tags.bot_id ==
            # self.bot.user.id. Previous heuristic required literal "alice"
            # word in the same message, which Discord's autocomplete
            # silently removes — that's why Alex's role mention (verified
            # 2026-05-18) never triggered. See module docstring.
            mentioned_as_role = _detect_role_mention_for_bot(message, self.bot.user)
            mentioned_as_alias = _detect_alias_mention(message.content, alice_settings.alice_aliases)
            if alice_settings.intrusive_mode_enabled:
                intrusive_match_obj = _CLINICAL_KEYWORDS_PATTERN.search(message.content or "")
                intrusive_match = intrusive_match_obj.group(0) if intrusive_match_obj else None

            if mentioned_as_user:
                invited_by = "user_mention"
            elif mentioned_as_text:
                invited_by = "text_mention"
            elif mentioned_as_role:
                invited_by = "role_mention"
            elif mentioned_as_alias:
                invited_by = f"alias:{mentioned_as_alias}"
            elif intrusive_match:
                invited_by = f"intrusive:{intrusive_match.lower()[:40]}"
            else:
                log.debug(
                    "alice_skip_no_mention",
                    mentioned_as_user=mentioned_as_user,
                    mentioned_as_text=mentioned_as_text,
                    mentioned_as_role=mentioned_as_role,
                    mentioned_as_alias=mentioned_as_alias,
                    intrusive_mode_enabled=alice_settings.intrusive_mode_enabled,
                )
                return
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

        # Every branch above either assigned `invited_by` or returned early.
        # This assert documents the invariant for type checkers + readers
        # and surfaces a misroute as a loud crash instead of silent
        # behavior change.
        assert invited_by is not None, "invited_by must be set before _respond"

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

        # Universal values corpus (shared with Insult): the animal-liberation
        # frame activates by TOPIC, identical source for both bots — ALICE just
        # voices it with her own calm. Detect on the freshest user text: the
        # current message on the mention path, else the last user line in the
        # thread (invite / failover path, where user_msg is None). The corpus
        # itself yields to ALICE's existing acute-distress handling.
        topic_text = user_msg
        if not topic_text:
            topic_text = next(
                (m.get("content", "") for m in reversed(recent) if m.get("role") == "user"),
                "",
            )
        corpus = animal_liberation_guidance(topic_text)
        if corpus:
            system_prompt = f"{system_prompt}\n\n{corpus}"
            log.info("alice_animal_corpus_injected", corpus_chars=len(corpus))
            # Phase B: fine tactics via LEXICAL retrieval — ALICE runs at 1Gi
            # with no embedder wired, so we don't load sentence-transformers
            # here (would risk OOM). Same corpus as Insult, lexical fallback.
            tactics = animal_tactics_guidance(topic_text)
            if tactics:
                system_prompt = f"{system_prompt}\n\n{tactics}"
                log.info("alice_animal_tactics_injected", tactics_chars=len(tactics))

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
        # Append a small version tag to the LAST chunk so prod observers
        # can correlate the visible reply with the deployed image. Same
        # affordance Insult uses (`VERSION_TAG` in `core/delivery.py`).
        chunks = chunk_paragraph_aware(text, max_chars=1900)
        from alice import __version__ as _alice_version

        version_tag = f"\n-# ᵃ{_alice_version.replace('.', '·')}"
        for i, chunk in enumerate(chunks):
            payload = chunk + (version_tag if i == len(chunks) - 1 else "")
            try:
                await channel.send(payload)
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
