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
from alice.core.clinical_reflection import ClinicalReflector
from alice.core.llm import AliceLLMClient
from alice.core.memory import AliceMemory
from alice.core.persona_loader import PersonaLoader
from shared.corpus import (
    animal_liberation_guidance,
    animal_tactics_guidance,
    detect_film_topic,
    film_criticism_guidance,
)
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
        clinical: ClinicalReflector | None = None,
        clinical_channel_id: str = "",
    ):
        self.bot = bot
        self.memory = memory
        self.llm = llm
        self.persona = persona
        # Clinical Reflection Layer (backend clínico). When both are set, after the
        # presence reply ALICE posts a metacognitive observation to the
        # clinician-only channel — NEVER to the patient.
        self.clinical = clinical
        self.clinical_channel_id = clinical_channel_id
        # Strong refs to fire-and-forget reflection tasks so the event loop
        # doesn't garbage-collect them mid-flight (RUF006).
        self._bg_tasks: set[asyncio.Task[None]] = set()

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

            # Guard (v4.20.19): a sibling bot (Insult) using "amix"/"ali" as a
            # casual vocative toward a user — or tripping a clinical keyword in
            # its own reply — must NOT auto-invoke ALICE. The legitimate
            # Insult→ALICE path is the REST /invite endpoint, not on_message.
            # KQL sample 2026-06-03: 8/8 "amix" messages in 8h were bot-authored,
            # which is why ALICE kept chasing Alex every time Insult said "Amix,".
            # Explicit @-mention of ALICE still works (a bot could deliberately
            # tag her); only the loose alias/intrusive heuristics are suppressed.
            if message.author and message.author.bot:
                mentioned_as_alias = None
                intrusive_match = None

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
            elif (
                not (message.author and message.author.bot)
                and (open_gate_reason := await self._should_open_gate(str(message.channel.id))) is not None
            ):
                # Self-governing failover (alice 0.1.21): ALICE covers the
                # channel only while Insult is down. `_should_open_gate` returns
                # the reason string when she should step in, or None to stand
                # back. Logged distinctly so KQL can measure failover coverage.
                invited_by = open_gate_reason
                log.warning(
                    "alice_open_gate_responding",
                    channel_id=str(message.channel.id),
                    user_id=str(message.author.id),
                    reason=open_gate_reason,
                )
            else:
                log.debug(
                    "alice_skip_no_mention",
                    mentioned_as_user=mentioned_as_user,
                    mentioned_as_text=mentioned_as_text,
                    mentioned_as_role=mentioned_as_role,
                    mentioned_as_alias=mentioned_as_alias,
                    intrusive_mode_enabled=alice_settings.intrusive_mode_enabled,
                    open_gate_mode=alice_settings.open_gate_mode,
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

    async def _should_open_gate(self, channel_id: str) -> str | None:
        """Decide whether ALICE should cover this channel via the failover gate.

        Returns a reason string when the gate is OPEN (ALICE responds), or None
        to stand back. Modes (``alice_settings.open_gate_mode``):

        - ``"on"``   — always open (manual override).
        - ``"off"``  — never (normal sibling coexistence). The deprecated
          ``open_gate_enabled=True`` flag is honored here as ``"on"`` for
          backward compat with the env already set in prod.
        - ``"auto"`` — open ONLY while Insult is down, judged by his silence in
          the shared ``messages`` table: no Insult assistant row for longer than
          ``open_gate_silence_threshold_s``. He recovers → his next row appears
          → ALICE stands back on the following turn. Self-governing, no restart.

        Fails OPEN if the health query errors: a silent channel is a worse
        failure than an occasional duplicate, and the query failing is rare.
        """
        mode = (alice_settings.open_gate_mode or "off").lower()
        if mode == "off" and alice_settings.open_gate_enabled:
            mode = "on"  # deprecated boolean → manual on

        if mode == "on":
            return "open_gate_on"
        if mode != "auto":
            return None

        try:
            silent_s = await self.memory.seconds_since_insult_reply(channel_id)
        except Exception as e:  # fail OPEN — cover rather than go silent
            log.warning("alice_open_gate_healthcheck_failed", error=str(e))
            return "open_gate_auto_healthcheck_failed"

        threshold = alice_settings.open_gate_silence_threshold_s
        if silent_s is None:
            return "open_gate_auto_insult_never_spoke"
        if silent_s > threshold:
            return f"open_gate_auto_insult_silent_{int(silent_s)}s"
        return None  # Insult answered recently — stand back

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

        # Film-criticism (Vultur) method frame — topic-gated, same shared/corpus
        # mechanism. ALICE runs it cold/forensic. The theory RAG (the 2 PDF
        # books) is queried via Azure ada-002 (remote HTTP embed — NOT MiniLM
        # local, so no OOM risk at 1Gi) and injected underneath the frame.
        film = film_criticism_guidance(topic_text)
        if film:
            system_prompt = f"{system_prompt}\n\n{film}"
            log.info("alice_film_corpus_injected", corpus_chars=len(film))
            if detect_film_topic(topic_text):
                try:
                    from personas.insult.core.deep_memory import build_film_references_block

                    refs = await build_film_references_block(topic_text)
                    if refs:
                        system_prompt = f"{system_prompt}\n\n{refs}"
                        log.info("alice_film_refs_injected", refs_chars=len(refs))
                except Exception as e:  # best-effort; never break the turn
                    log.warning("alice_film_refs_failed", error=str(e))

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

        # Clinical Reflection Layer (backend clínico): metacognitive, clinician-only.
        # Fire-and-forget so it never delays the patient's reply, and it posts ONLY
        # to the clinician channel — never to `channel` (the patient).
        if self.clinical and self.clinical_channel_id:
            convo = [m for m in recent if m.get("role") in ("user", "assistant")]
            reflection_msgs = [*convo, {"role": "assistant", "content": text}]
            task = asyncio.create_task(
                self._post_clinical_reflection(reflection_msgs, origin=channel_name or channel_id)
            )
            self._bg_tasks.add(task)
            task.add_done_callback(self._bg_tasks.discard)

        log.info(
            "alice_turn_complete",
            invited_by=invited_by,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            latency_ms=response.latency_ms,
            chars=len(text),
        )
        return text

    async def _post_clinical_reflection(self, messages: list[dict[str, str]], *, origin: str) -> None:
        """Run the clinical reflection and post it to the clinician-only channel.

        This is the metacognitive backend: the output is for the clinician, NEVER
        the patient. Fire-and-forget — failures are logged, never surfaced to the
        user, and we NEVER fall back to the patient's channel if the clinician
        channel is missing (a leak would break the whole design).
        """
        if self.clinical is None:
            return
        try:
            reflection = await self.clinical.reflect(messages)
        except Exception as e:  # broad on purpose: never let the backend layer crash a turn
            log.exception("alice_clinical_reflection_failed", error=str(e))
            return

        channel = self.bot.get_channel(int(self.clinical_channel_id))
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(int(self.clinical_channel_id))
            except (discord.HTTPException, ValueError) as e:
                log.error(
                    "alice_clinical_channel_unavailable",
                    channel_id=self.clinical_channel_id,
                    error=str(e),
                )
                return  # never leak the reflection to the patient
        if not isinstance(channel, discord.abc.Messageable):
            log.error("alice_clinical_channel_not_messageable", channel_id=self.clinical_channel_id)
            return

        triage = reflection.triage
        level = triage.level.value if triage else "n/a"
        header = f"**Reflexión clínica** · origen: `{origin}` · TRIAGE: **{level}**"
        if triage is not None and triage.level.value == "CRITICAL":
            header = f"**!!! RIESGO CRÍTICO !!!**\n{header}"
        body = f"{header}\n{reflection.text}"

        for chunk in chunk_paragraph_aware(body, max_chars=1900):
            try:
                await channel.send(chunk)
            except discord.HTTPException as e:
                log.exception("alice_clinical_post_failed", error=str(e))
                return
        log.info(
            "alice_clinical_posted",
            origin=origin,
            triage_level=level,
            input_tokens=reflection.input_tokens,
            output_tokens=reflection.output_tokens,
            latency_ms=reflection.latency_ms,
        )
