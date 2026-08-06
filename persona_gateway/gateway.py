"""Khimeras persona gateway — one Discord bot user per sibling persona.

Each registered persona (Vultur, Insult, ALICE, Frugívoro…) runs as its OWN
Discord bot user (its own token) but they ALL share ONE brain: the persona-runner,
called with a `persona_id`. This module is deliberately thin — it does NOT run a
preset/flow pipeline. The persona's `<id>.md` (loaded by the runner) defines
behavior; the gateway only:

  1. listens on each persona-bot's gateway,
  2. responds ONLY when that bot is addressed — @mention, its own role mention,
     or a vocative text alias ("frugi, qué opinas"),
  3. replays recent channel context + the cleaned message to the runner,
  4. posts the reply as that bot user (native name/avatar — no webhook),
  5. persists both turns to the shared Postgres so the personas see one another.

**Structure (post-modularization 2026-07-20).** `PersonaClient` is the thin
Discord adapter: event handlers + the two turn entry points, each delegating to
an injected service —
- reception predicates → `persona_gateway.routing`
- attachment blocks (audio is the host's lane, not this one) → `persona_gateway.ingest`
- context/guidance/other-people assembly → `persona_gateway.turn_context`
- the turn tail (runner → react → markers → send → store → TTS) → `persona_gateway.turns`
- invite helpers (channel resolve, instruction, trigger fetch) → `persona_gateway.invites`
- reply delivery (chunk + tag + send) → `persona_gateway.delivery`
- durable markers (research/agenda/remind/remember) → `persona_gateway.markers`
- the drain loops → `persona_gateway.workers`
- background fact extraction → `persona_gateway.facts`
- per-persona TTS → `persona_gateway.voice`
- operator-tunable cadences/timeouts → `persona_gateway.config`
- process bootstrap (deps, /invite server, lifecycle) → `persona_gateway.app`
"""

from __future__ import annotations

import asyncio
import contextlib
import time

import discord
import structlog
from discord.ext import tasks

from khimeras_shared.memory import MemoryStore
from khimeras_shared.prompts import PromptCache
from khimeras_shared.runner.agent_client import AgentRunnerClient
from khimeras_shared.runner.judge_client import RunnerJudgeClient
from persona_gateway.config import CONFIG
from persona_gateway.delivery import DISCORD_LIMIT, chunk, full_text_for, strip_version_tag
from persona_gateway.facts import FactExtractor
from persona_gateway.ingest import MessageIngest
from persona_gateway.invites import fetch_trigger, invite_instruction, resolve_messageable
from persona_gateway.markers import MarkerRouter
from persona_gateway.routing import clean_mention, edit_summons, should_respond
from persona_gateway.turn_context import TurnContextBuilder
from persona_gateway.turns import TurnRunner
from persona_gateway.vision import ImageTranscriber
from persona_gateway.voice import VoiceService
from persona_gateway.workers import AgendaWorker, ReflectionWorker, ReminderWorker, ResearchWorker
from shared.personas import Persona

# Re-exports: the tests import these from `persona_gateway.gateway` — keep the
# names resolvable on THIS module's namespace so they keep working after the split.
__all__ = [
    "DISCORD_LIMIT",
    "PersonaClient",
    "chunk",
    "clean_mention",
    "edit_summons",
    "should_respond",
]

SPEAK_EMOJI = "🔊"

log = structlog.get_logger()

# Engine-side prompt cache (mtime hot-reload) shared by this process's personas.
_PROMPT_CACHE: PromptCache = {}


class PersonaClient(discord.Client):
    """A single persona's Discord bot user, delegating turns to the runner."""

    def __init__(
        self,
        persona: Persona,
        memory: MemoryStore,
        agent_client: AgentRunnerClient,
        *,
        intents: discord.Intents,
        tts_client=None,
        stt_client=None,
        auto_tts_min_chars: int = 0,
        judge_client: RunnerJudgeClient | None = None,
    ) -> None:
        super().__init__(intents=intents)
        self.persona = persona
        self.memory = memory
        self.agent_client = agent_client
        # Exposed so tests/ops can inspect or toggle it; the None-check reads it
        # LIVE at spawn time (see FactExtractor), so setting it None disables
        # extraction on the next turn.
        self.judge_client = judge_client
        # Strong refs to fire-and-forget tasks so the loop doesn't GC them (RUF006).
        self._bg_tasks: set[asyncio.Task[None]] = set()

        # Liveness signal for the "alive but mute" failure (#14). A persona can be
        # logged in (serving:true) yet answer no one — the 2026-06-13 boot-zombie
        # class. `serving` alone can't tell that apart; these two timestamps can:
        # if a message was SEEN more recently than a turn was DELIVERED (past a
        # grace window), the persona took an addressed message and produced no
        # reply — mute. Both old = just no traffic (normal at low scale), NOT mute.
        self.last_message_seen: float | None = None
        self.last_turn_delivered: float | None = None

        # Injected services — the logic lives here, the client just delegates.
        self._markers = MarkerRouter(persona, memory)
        self._voice = VoiceService(persona, tts_client)
        self._ingest = MessageIngest(persona, stt_client)
        self._context = TurnContextBuilder(persona, memory)
        self._turns = TurnRunner(
            persona,
            memory,
            agent_client,
            self._markers,
            self._voice,
            self._bg_tasks,
            auto_tts_min_chars=auto_tts_min_chars,
        )
        self._facts = FactExtractor(persona, memory, self._bg_tasks)
        self._vision = ImageTranscriber(memory, self._bg_tasks)
        self._research = ResearchWorker(persona, memory, agent_client)
        self._agenda = AgendaWorker(persona, memory, agent_client)
        self._reminders = ReminderWorker(persona, memory, agent_client, _PROMPT_CACHE)
        self._reflection = ReflectionWorker(persona, memory)

    # --- lifecycle -----------------------------------------------------------

    async def on_ready(self) -> None:
        log.info(
            "persona_gateway_ready",
            persona_id=self.persona.persona_id,
            bot_id=str(self.user.id) if self.user else None,
            bot_name=str(self.user) if self.user else None,
            guilds=len(self.guilds),
        )
        # Start the drain loops idempotently (on_ready fires again after a resume).
        for loop in (self._research_drain, self._agenda_check, self._reminder_drain, self._reflection_check):
            if not loop.is_running():
                loop.start()

    # --- drain loops: thin shells over the injected workers ------------------

    @tasks.loop(seconds=CONFIG.research_drain_seconds)
    async def _research_drain(self) -> None:
        await self._research.drain(self)

    @tasks.loop(seconds=CONFIG.agenda_check_seconds)
    async def _agenda_check(self) -> None:
        await self._agenda.drain(self)

    @tasks.loop(seconds=CONFIG.reminder_check_seconds)
    async def _reminder_drain(self) -> None:
        await self._reminders.drain(self)

    @tasks.loop(seconds=CONFIG.reflection_check_seconds)
    async def _reflection_check(self) -> None:
        await self._reflection.drain(self.judge_client)

    @_reflection_check.before_loop
    async def _reflection_boot_warmup(self) -> None:
        """Hold the first tick past the deploy window (gateway + runner ship in
        the same CD wave; a tick at boot stampedes a runner still cycling —
        the 2026-07-16 first-pass 503s). The weekly gate makes 15 min free."""
        await asyncio.sleep(CONFIG.reflection_boot_warmup_s)

    # --- reception -----------------------------------------------------------

    async def on_message(self, message: discord.Message) -> None:
        if not should_respond(
            message,
            self.user,
            self.persona.aliases,
            host_owns_reception=CONFIG.host_owns_reception,
        ):
            return
        await self._dispatch(message)

    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        """An edit that ADDS an address to this persona summons it (P0 2026-07-06):
        Alex sent his pantry list clean and edited in "@frugi" — `on_message` had
        already run on the clean content, so the mention summoned nobody. Fires
        ONLY on the not-addressed → addressed transition, so an edit to a message
        this persona already answered never re-triggers it."""
        if CONFIG.host_owns_reception:
            return
        if not edit_summons(before, after, self.user, self.persona.aliases):
            return
        log.info(
            "persona_gateway_edit_summon",
            persona_id=self.persona.persona_id,
            message_id=after.id,
            channel_id=str(after.channel.id),
        )
        await self._dispatch(after)

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        """🔊 on one of THIS persona's own messages → speak it in the persona's own
        voice. Guards: only 🔊, never our own reaction, and ONLY our own messages
        (a 🔊 on an Insult/human message belongs to Insult's VoiceCog). Voice off →
        no-op."""
        if str(payload.emoji) != SPEAK_EMOJI:
            return
        if self.user is None or payload.user_id == self.user.id:
            return
        if not self._voice.enabled:
            return
        channel = self.get_channel(payload.channel_id)
        if channel is None:
            with contextlib.suppress(discord.HTTPException):
                channel = await self.fetch_channel(payload.channel_id)
        if channel is None:
            return
        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.HTTPException:
            return
        if message.author.id != self.user.id:
            return  # not this persona's message — Insult owns its own 🔊
        text = full_text_for(message.id) or strip_version_tag(message.content.strip())
        await self._voice.speak(channel, text, reason="manual")

    async def _dispatch(self, message: discord.Message) -> None:
        """Shared guarded entry for message + edit summons."""
        try:
            await self._handle(message)
        except Exception:
            log.exception("persona_gateway_turn_failed", persona_id=self.persona.persona_id)
            # Never expose internals. The recovery send gets its own guard; if the
            # channel is rate-limited a reaction (different bucket) survives.
            try:
                await message.channel.send("…")
            except discord.HTTPException:
                with contextlib.suppress(discord.HTTPException):
                    await message.add_reaction("🦅")

    # --- turn entry points ----------------------------------------------------

    async def _handle(self, message: discord.Message) -> None:
        channel_id = str(message.channel.id)
        user_id = str(message.author.id)
        guild_id = str(message.guild.id) if message.guild else None
        channel_name = getattr(message.channel, "name", None)
        bot_id = self.user.id if self.user else 0
        ask = clean_mention(message.content, bot_id)
        attachment_blocks = await self._ingest.attachment_blocks(message)
        # A DM voice note carries NO text and no readable attachment, so it used
        # to hit the return below and die in total silence — and the host that
        # owns transcription cannot see a DM at all (Discord isolates DM channels
        # per bot user). Transcribing here is scoped to DMs only; in a guild this
        # returns "" and the host stays the sole transcriber.
        spoken = await self._ingest.dm_voice_transcript(message)
        if spoken:
            ask = f"{ask}\n{spoken}" if ask else spoken
        if not ask and not attachment_blocks:
            return  # bare @mention with no text and no readable attachment

        # Recent context BEFORE storing the current turn, so it isn't duplicated.
        # An addressed message we're about to answer — mark it SEEN. If a reply
        # never follows (mark_turn_delivered below), /health surfaces the mute.
        self.last_message_seen = time.time()

        recent = await self.memory.get_recent(channel_id, CONFIG.recent_limit)

        # Persist the user's turn (shared Postgres → every persona sees it).
        await self.memory.store(
            channel_id,
            user_id,
            message.author.display_name,
            "user",
            ask,
            guild_id=guild_id,
            channel_name=channel_name,
            discord_message_id=str(message.id),
        )

        user_content: str | list[dict] = ask
        if attachment_blocks:
            text_blocks = [{"type": "text", "text": ask}] if ask else []
            user_content = [*text_blocks, *attachment_blocks]

        turn = await self._context.build(
            channel_id=channel_id,
            recent=recent,
            relevant_query=ask,
            guidance_user_id=user_id,
            guidance_message=ask,
            corpus_query=ask,
            exclude_user_id=user_id,
        )
        messages = [*turn.context, {"role": "user", "content": user_content}]
        await self._run_and_deliver(
            channel=message.channel,
            channel_id=channel_id,
            user_id=user_id,
            guild_id=guild_id,
            channel_name=channel_name,
            messages=messages,
            react_to=message,
            behavioral_guidance=turn.guidance,
            other_people=turn.other_people,
            relevant_memory=turn.relevant_memory,
        )
        # Reply delivered — the persona is not mute. Stamp it so /health can tell
        # "answered recently" from "took a message and went silent".
        self.last_turn_delivered = time.time()
        # A mention carries a REAL user ask — the only turn worth mining for facts.
        # Runs AFTER delivery, in the background, so the extraction's LLM round-trip
        # never sits between the user and their reply.
        self._spawn_fact_extraction(
            user_id,
            message.author.display_name,
            [*recent[-CONFIG.facts_recent_window :], {"user_name": message.author.display_name, "content": ask}],
        )
        # An image lives inside ONE turn and then evaporates — the stored row keeps
        # the words and nothing else. Transcribe it into that row so the persona is
        # not blind to it tomorrow. Also AFTER delivery: a vision round-trip must
        # never sit between the user and their reply.
        self._vision.spawn(self.judge_client, str(message.id), attachment_blocks)

    def bind_siblings(self, personas: dict[str, PersonaClient]) -> None:
        """Hand this client the live persona registry, once every client exists.

        Late-bound because `[INVITE:]` summons a sibling that does not exist yet
        when this one is constructed. The gateway runs every persona in ONE
        process, so the summon is a direct call to the sibling's guarded
        `dispatch_invite` — no HTTP hop back through `/invite`, no second token.
        """
        self._markers.bind_siblings(personas)

    async def dispatch_invite(
        self,
        *,
        channel_id: str,
        guild_id: str | None,
        channel_name: str | None,
        reason: str,
        invited_by: str = "insult_rest",
        trigger_message_id: str | None = None,
        trigger_transcript: str = "",
    ) -> None:
        """Guarded entry for the invite path — what `/invite` schedules.

        `_dispatch` has protected the @mention path since day one, but the
        invite path — which the host cutover made THE path — ran as a bare
        `create_task`, so any fault died as "Task exception was never
        retrieved" and the user got NOTHING. Found 2026-07-23: a runner 422
        left a voice note unanswered with the failure visible only in the
        logs. Same contract as `_dispatch`: log, then a neutral "…" so the
        persona is never silently mute.
        """
        try:
            await self.respond_to_invite(
                channel_id=channel_id,
                guild_id=guild_id,
                channel_name=channel_name,
                reason=reason,
                invited_by=invited_by,
                trigger_message_id=trigger_message_id,
                trigger_transcript=trigger_transcript,
            )
        except Exception:
            log.exception(
                "persona_gateway_invite_failed",
                persona_id=self.persona.persona_id,
                channel_id=channel_id,
                invited_by=invited_by,
            )
            channel = await resolve_messageable(self, channel_id)
            if channel is not None:
                with contextlib.suppress(discord.HTTPException):
                    await channel.send("…")

    async def respond_to_invite(
        self,
        *,
        channel_id: str,
        guild_id: str | None,
        channel_name: str | None,
        reason: str,
        invited_by: str = "insult_rest",
        trigger_transcript: str = "",
        trigger_message_id: str | None = None,
    ) -> None:
        """Entry point for the gateway's ported /invite handler.

        Routes through the persona-runner (this persona's brain). The ``reason``
        is injected as the FRESHEST turn — instruction context, not a visible
        user message — so the persona reads the thread and responds with the
        lens the reason asks for. When the trigger is a real human message
        (every host-routed turn post-cutover), that user turn IS stored —
        idempotently by discord_message_id — so the longitudinal memory keeps
        both halves of the conversation.
        """
        channel = await resolve_messageable(self, channel_id)
        if channel is None:
            log.warning(
                "persona_gateway_invite_channel_not_found",
                persona_id=self.persona.persona_id,
                channel_id=channel_id,
            )
            return

        # Un turno aceptado es un turno VISTO. `/health` detecta la mudez
        # comparando este sello contra `last_turn_delivered`, y hasta hoy sólo se
        # estampaba en el camino de @mención — o sea en NINGUNO de los turnos que
        # el sistema realmente sirve, porque post-cutover el host es dueño de la
        # recepción y todo entra por aquí. Una persona que tomaba un invite y no
        # contestaba se veía idéntica a una sin tráfico: la señal anti-boot-zombie
        # del 2026-06-13 llevaba apagada justo donde pasa todo.
        self.last_message_seen = time.time()

        recent = await self.memory.get_recent(channel_id, CONFIG.recent_limit)
        instruction = invite_instruction(invited_by, reason)
        log.info(
            "persona_gateway_invite_accepted",
            persona_id=self.persona.persona_id,
            channel_id=channel_id,
            invited_by=invited_by,
            reason_preview=reason[:100],
        )
        react_to = await fetch_trigger(
            channel,
            trigger_message_id,
            persona_id=self.persona.persona_id,
            channel_id=channel_id,
        )
        # The trigger message may carry images/documents — a host-routed turn
        # about an image is blind without them (2026-07-16 bug: Insult reacted
        # to a photo it never saw). Best-effort: a processing fault degrades to
        # a text-only turn, never a dead invite.
        attachment_blocks: list[dict] = []
        if react_to is not None:
            try:
                attachment_blocks = await self._ingest.attachment_blocks(react_to)
            except Exception:
                log.warning(
                    "persona_gateway_invite_attachments_failed",
                    persona_id=self.persona.persona_id,
                    channel_id=channel_id,
                    trigger_message_id=trigger_message_id,
                    exc_info=True,
                )
        # What the voice note SAID arrives transcribed on the wire. The gateway
        # never calls susurro for STT: the host owns reception, so it owns
        # transcription (2026-07-23 decision) and the persona reads its words
        # instead of a filename.
        spoken = trigger_transcript.strip()

        # The invite path is the MAIN path post-cutover (the host routes every
        # unaddressed turn here), so it gets the SAME turn assembly as `_handle`
        # — guardian, reminders, corpus, relevant, other-people, real user_id.
        # Before 2026-07-19 only the corpus rode along: the vulnerable-user
        # overlay, relevant memory and third-party facts were wired exclusively
        # into the @mention path, which the cutover had just demoted to
        # near-zero traffic — the celebrated-but-disconnected class, again.
        subject = None
        if react_to is not None and not getattr(react_to.author, "bot", False):
            subject = react_to.author
        subject_user_id = str(subject.id) if subject is not None else None
        subject_ask = (react_to.content or "").strip() if react_to is not None else ""
        if spoken:
            subject_ask = "\n".join(part for part in [subject_ask, spoken] if part)
            speaker = subject.display_name if subject is not None else "quien habló"
            instruction = f"{instruction}\n[Nota de voz de {speaker}, transcrita: «{spoken}»]"

        instruction_content: str | list[dict] = instruction
        if attachment_blocks:
            instruction_content = [{"type": "text", "text": instruction}, *attachment_blocks]

        # Persist the HUMAN trigger turn. The original /invite was Insult-initiated
        # (no user message existed), but post-cutover the invite IS the main path
        # and the trigger is a real human message — without this store the
        # longitudinal memory records only the personas' half of every #general
        # conversation (found 2026-07-19: zero user rows since the cutover), and
        # vision's append_content_by_discord_id has no row to land on. The repo's
        # ON CONFLICT (discord_message_id) DO NOTHING makes this idempotent
        # against any path that already stored the same message.
        if subject is not None and subject_user_id is not None and (subject_ask or attachment_blocks):
            try:
                await self.memory.store(
                    channel_id,
                    subject_user_id,
                    subject.display_name,
                    "user",
                    subject_ask,
                    guild_id=guild_id,
                    channel_name=channel_name,
                    discord_message_id=str(react_to.id) if react_to is not None else None,
                )
            except Exception:
                log.exception(
                    "persona_gateway_invite_user_store_failed",
                    persona_id=self.persona.persona_id,
                    channel_id=channel_id,
                )

        turn = await self._context.build(
            channel_id=channel_id,
            recent=recent,
            relevant_query=subject_ask or reason,
            guidance_user_id=subject_user_id,
            guidance_message=subject_ask or reason,
            corpus_query=reason,
            exclude_user_id=subject_user_id or (str(self.user.id) if self.user else ""),
        )
        messages = [*turn.context, {"role": "user", "content": instruction_content}]
        await self._run_and_deliver(
            channel=channel,
            channel_id=channel_id,
            user_id=subject_user_id or (str(self.user.id) if self.user else ""),
            guild_id=guild_id,
            channel_name=channel_name,
            messages=messages,
            turn_kind="invite",
            react_to=react_to,
            behavioral_guidance=turn.guidance,
            other_people=turn.other_people,
            relevant_memory=turn.relevant_memory,
        )
        self.last_turn_delivered = time.time()
        if subject is not None and subject_ask:
            self._spawn_fact_extraction(
                str(subject.id),
                subject.display_name,
                [
                    *recent[-CONFIG.facts_recent_window :],
                    {"user_name": subject.display_name, "content": subject_ask},
                ],
            )
        if react_to is not None and attachment_blocks:
            self._vision.spawn(self.judge_client, str(react_to.id), attachment_blocks)

    # --- delegates -------------------------------------------------------------

    def _spawn_fact_extraction(self, user_id: str, user_name: str, recent: list[dict]) -> None:
        """Delegates to the fact backstop (kept as a method: tests call it).
        Reads `self.judge_client` LIVE so a toggle to None disables it next turn."""
        self._facts.spawn(self.judge_client, user_id, user_name, recent)

    async def _run_and_deliver(
        self,
        *,
        channel: discord.abc.Messageable,
        channel_id: str,
        user_id: str,
        guild_id: str | None,
        channel_name: str | None,
        messages: list[dict],
        turn_kind: str = "mention",
        react_to: discord.Message | None = None,
        behavioral_guidance: str | None = None,
        other_people: str | None = None,
        relevant_memory: str | None = None,
    ) -> None:
        """Thin delegate to the injected TurnRunner (tests drive this directly)."""
        await self._turns.run_and_deliver(
            channel=channel,
            channel_id=channel_id,
            user_id=user_id,
            guild_id=guild_id,
            channel_name=channel_name,
            messages=messages,
            bot_user_id=str(self.user.id) if self.user else "0",
            turn_kind=turn_kind,
            react_to=react_to,
            behavioral_guidance=behavioral_guidance,
            other_people=other_people,
            relevant_memory=relevant_memory,
        )
