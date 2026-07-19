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

A single process hosts all persona-bots via `asyncio.gather`, sharing one
MemoryStore + one AgentRunnerClient.

**Structure (post-modularization).** `PersonaClient` is the thin Discord adapter:
event handlers + the turn orchestration, each delegating to an injected service —
- reception predicates → `persona_gateway.routing`
- attachment blocks + STT transcripts → `persona_gateway.ingest`
- the turn tail (runner → react → markers → send → store → TTS) → `persona_gateway.turns`
- invite helpers (channel resolve, instruction, trigger fetch) → `persona_gateway.invites`
- reply delivery (chunk + tag + send) → `persona_gateway.delivery`
- durable markers (research/agenda/remind/remember) → `persona_gateway.markers`
- the three drain loops → `persona_gateway.workers`
- background fact extraction → `persona_gateway.facts`
- per-persona TTS → `persona_gateway.voice`
- operator-tunable cadences/timeouts → `persona_gateway.config`
Bootstrap (`_build_shared` … `_main`) lives at the bottom.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import time

import discord
import structlog
from discord.ext import tasks

from khimeras_shared.guidance import MAX_GUIDANCE_CHARS, guidance_for_turn
from khimeras_shared.memory import MemoryStore
from khimeras_shared.other_people import other_people_block_for_turn
from khimeras_shared.persona import PersonaRuntimeConfig
from khimeras_shared.prompts import PromptCache
from khimeras_shared.runner.agent_client import AgentRunnerClient
from khimeras_shared.runner.judge_client import RunnerJudgeClient
from khimeras_shared.stt import SusurroSttClient, build_susurro_stt_client
from khimeras_shared.tts import build_susurro_tts_client
from persona_gateway.boot import GatewayBootState
from persona_gateway.config import CONFIG
from persona_gateway.delivery import DISCORD_LIMIT, chunk
from persona_gateway.facts import FactExtractor
from persona_gateway.ingest import MessageIngest
from persona_gateway.invites import fetch_trigger, invite_instruction, resolve_messageable
from persona_gateway.markers import MarkerRouter
from persona_gateway.routing import clean_mention, edit_summons, format_context, should_respond
from persona_gateway.turns import TurnRunner
from persona_gateway.voice import VoiceService
from persona_gateway.workers import AgendaWorker, ReflectionWorker, ReminderWorker, ResearchWorker
from shared.corpus.persona_corpus import build_persona_corpus_block
from shared.personas import Persona, gateway_personas

# Re-exports: the tests import these from `persona_gateway.gateway`, and the
# reactions test monkeypatches `persona_gateway.gateway.add_reactions` — keep the
# names resolvable on THIS module's namespace so both keep working after the split.
__all__ = [
    "DISCORD_LIMIT",
    "PersonaClient",
    "chunk",
    "clean_mention",
    "edit_summons",
    "format_context",
    "run",
    "should_respond",
]

SPEAK_EMOJI = "🔊"

log = structlog.get_logger()

# Engine-side prompt cache (mtime hot-reload) shared by this process's personas.
_PROMPT_CACHE: PromptCache = {}

# Bind timing for the /invite HTTP server (external protocol contract, not a knob).
BIND_TIMEOUT_SECONDS = 15.0  # well under the ACA StartUp probe's failure budget
BIND_POLL_SECONDS = 0.05


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
        stt_client: SusurroSttClient | None = None,
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
        await self._voice.speak(channel, message.content.strip(), reason="manual")

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

    async def _handle(self, message: discord.Message) -> None:
        channel_id = str(message.channel.id)
        user_id = str(message.author.id)
        guild_id = str(message.guild.id) if message.guild else None
        channel_name = getattr(message.channel, "name", None)
        bot_id = self.user.id if self.user else 0
        ask = clean_mention(message.content, bot_id)
        voice_transcripts = await self._ingest.voice_transcripts(message)
        if voice_transcripts:
            ask = "\n".join(part for part in [ask, *voice_transcripts] if part)
        attachment_blocks = await self._ingest.attachment_blocks(message)
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
        # Recent alone is a 30-message window: anything older is invisible, so a
        # persona forgets what was said last week even though it is in Postgres.
        # `search` pulls the keyword-relevant older turns and `build_context`
        # merges them in chronological order — the "recent + relevant" retrieval
        # that died with the purge. Best-effort: a search fault degrades to
        # recent-only, never to a mute turn.
        relevant = await self._load_relevant(channel_id, ask)
        context = format_context(self.memory.build_context(recent, relevant))
        messages = [*context, {"role": "user", "content": user_content}]
        # The guardian: classify THIS turn against the user's accumulated facts and
        # send the persona's guidance on the wire. Without it the vulnerable-user
        # overlay never reaches the model — a user with a clinical cluster gets the
        # raw abrasive register. Every fault inside returns None: a turn without
        # guidance is a normal turn.
        guidance = await guidance_for_turn(
            memory=self.memory,
            user_id=user_id,
            current_message=ask,
            recent_messages=context,
            persona_id=self.persona.persona_id,
        )
        # This persona's shared topic corpus (RAG): retrieve the chunks relevant to
        # THIS message and append them to the guidance so the model argues from its
        # own library, in its own voice. Best-effort — a corpus fault (no PG, empty
        # namespace, no persona corpus) returns None and the turn ships unchanged.
        guidance = await self._append_corpus_block(guidance, ask)
        # Facts about the OTHER participants. The runner rebuilds the AUTHOR's
        # facts from the user_id, but is blind to the people being talked ABOUT
        # unless we forward them — the "recuerda a Alex cuando Alex escribe, la
        # niega cuando preguntan por ella" hole (2026-06-03).
        other_people = await other_people_block_for_turn(self.memory, channel_id, exclude_user_id=user_id)
        await self._run_and_deliver(
            channel=message.channel,
            channel_id=channel_id,
            user_id=user_id,
            guild_id=guild_id,
            channel_name=channel_name,
            messages=messages,
            react_to=message,
            behavioral_guidance=guidance,
            other_people=other_people,
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

    async def _load_relevant(self, channel_id: str, ask: str) -> list[dict]:
        """Keyword-relevant OLDER turns for this ask, or [] on any fault.

        Degrading to recent-only is a poorer answer; raising here would be a
        mute turn. Always the former.
        """
        if not ask:
            return []
        try:
            return await self.memory.search(channel_id, ask, CONFIG.relevant_limit)
        except Exception:
            log.exception("relevant_search_failed", channel_id=channel_id)
            return []

    async def _append_corpus_block(self, guidance: str | None, ask: str) -> str | None:
        """Merge this persona's corpus references into the turn guidance.

        ORDER IS SAFETY: corpus FIRST, guardian guidance LAST — the vulnerable-user
        overlay must be the freshest thing in the block, never buried under 2,200
        chars of erudition (cruel-critic 2026-07-16, finding #2).

        CAP IS SAFETY TOO: the runner rejects `behavioral_guidance` > 16000 with a
        422 (a mute bot). `guidance_for_turn` already truncates to that cap; this
        merge would re-inflate it past the cap by prepending the corpus, so we
        RE-CAP here — trimming the CORPUS end, never the guidance. The safety
        overlay always survives intact; erudition yields. If guidance alone
        already fills the cap, the corpus is dropped entirely (cruel-critic
        2026-07-16, finding #1: a near-cap vulnerable-user overlay + a corpus hit
        used to 422 and mute the bot for the most fragile person).

        Fail-safe: any fault returns the guidance untouched. A persona with no
        `corpus_namespace` (or no relevant hit) simply gets its guidance back.
        """
        try:
            block = await build_persona_corpus_block(persona_id=self.persona.persona_id, query=ask)
        except Exception:
            log.exception("gateway_corpus_block_failed", persona_id=self.persona.persona_id)
            return guidance
        if not block:
            return guidance
        if not guidance:
            return block[:MAX_GUIDANCE_CHARS]
        # Reserve the full guidance (safety-critical); the corpus gets whatever
        # budget is left. sep is "\n\n". A non-positive budget → drop the corpus.
        sep = "\n\n"
        corpus_budget = MAX_GUIDANCE_CHARS - len(guidance) - len(sep)
        if corpus_budget <= 0:
            log.warning(
                "gateway_corpus_dropped_guidance_full",
                persona_id=self.persona.persona_id,
                guidance_chars=len(guidance),
            )
            return guidance
        if len(block) > corpus_budget:
            log.info(
                "gateway_corpus_trimmed_to_cap",
                persona_id=self.persona.persona_id,
                block_chars=len(block),
                corpus_budget=corpus_budget,
            )
            block = block[:corpus_budget]
        return f"{block}{sep}{guidance}"

    def _spawn_fact_extraction(self, user_id: str, user_name: str, recent: list[dict]) -> None:
        """Delegates to the fact backstop (kept as a method: tests call it).
        Reads `self.judge_client` LIVE so a toggle to None disables it next turn."""
        self._facts.spawn(self.judge_client, user_id, user_name, recent)

    async def respond_to_invite(
        self,
        *,
        channel_id: str,
        guild_id: str | None,
        channel_name: str | None,
        reason: str,
        invited_by: str = "insult_rest",
        trigger_message_id: str | None = None,
    ) -> None:
        """Entry point for the gateway's ported /invite handler.

        Routes through the persona-runner (this persona's brain). Insult's
        ``reason`` is injected as the FRESHEST turn — instruction context, not a
        visible user message — so the persona reads the thread and responds with
        the lens the reason asks for. No user turn is stored (there is none; Insult
        already wrote the message that triggered it).
        """
        channel = await resolve_messageable(self, channel_id)
        if channel is None:
            log.warning(
                "persona_gateway_invite_channel_not_found",
                persona_id=self.persona.persona_id,
                channel_id=channel_id,
            )
            return

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
        instruction_content: str | list[dict] = instruction
        if attachment_blocks:
            instruction_content = [{"type": "text", "text": instruction}, *attachment_blocks]
        messages = [*format_context(recent), {"role": "user", "content": instruction_content}]
        # The invite path is the MAIN path post-purga (the host routes unaddressed
        # turns here) — it gets the persona's corpus too, keyed off the routing
        # reason (cruel-critic 2026-07-16, finding #1: Vultur dictaminaba cine sin
        # su biblioteca en el path con más tráfico).
        corpus_guidance = await self._append_corpus_block(None, reason)
        await self._run_and_deliver(
            channel=channel,
            channel_id=channel_id,
            user_id=str(self.user.id) if self.user else "",
            guild_id=guild_id,
            channel_name=channel_name,
            messages=messages,
            turn_kind="invite",
            react_to=react_to,
            behavioral_guidance=corpus_guidance,
        )

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
        )


# --- bootstrap: shared deps, the /invite server, and the process lifecycle ----
# Kept in this module (not a separate app.py) because the boot-resilience test
# monkeypatches these names on `persona_gateway.gateway` and drives `_main` —
# moving them would break that regression guard for no structural gain.


def _build_shared() -> tuple[
    MemoryStore,
    AgentRunnerClient,
    object | None,
    SusurroSttClient | None,
    int,
    str,
    RunnerJudgeClient,
]:
    """Construct the deps shared by all persona-bots (same wiring as Insult).

    Also builds the susurro TTS client so each persona can speak its own 🔊 audio.
    TTS is OPTIONAL — when SUSURRO_KEY is unset the client is None and voice is
    simply off. The `/invite` bearer token (INSULT_TO_ALICE_TOKEN) is the same
    secret the legacy alice-bot endpoint used. The last element is the one-shot
    judge client (runner /v1/judge) that drives the automatic fact-extraction
    backstop — same runner URL + token as the turn client, a different endpoint.
    """
    config = PersonaRuntimeConfig.from_env()

    memory = MemoryStore(config.postgres_url.get_secret_value())
    runner_url = config.persona_runner_url
    runner_token = config.persona_runner_token.get_secret_value()
    if not (runner_url and runner_token):
        raise RuntimeError("persona gateway requires PERSONA_RUNNER_URL + token")
    # first_turn_timeout_s=240 (vs the 120 default): a sibling's FIRST turn — cold
    # session + curated facts + guidance — measured 134.5s in prod. The 120s
    # default read-timeout hung up 14s before the runner finished; the user got
    # the "…" fallback while a complete reply died unread.
    agent_client = AgentRunnerClient(
        runner_url=runner_url, runner_token=runner_token, timeout_s=CONFIG.first_turn_timeout_s
    )
    judge_client = RunnerJudgeClient(runner_url=runner_url, token=runner_token)

    tts_client = build_susurro_tts_client(base_url=CONFIG.susurro_url, api_key=CONFIG.susurro_key)
    stt_client = build_susurro_stt_client(base_url=CONFIG.susurro_url, api_key=CONFIG.susurro_key)
    log.info(
        "persona_gateway_tts_configured",
        enabled=tts_client is not None,
        auto_tts_min_chars=CONFIG.auto_tts_min_chars,
    )
    log.info("persona_gateway_stt_configured", enabled=stt_client is not None)
    invite_token = config.insult_to_alice_token.get_secret_value()
    return memory, agent_client, tts_client, stt_client, CONFIG.auto_tts_min_chars, invite_token, judge_client


def _serve_invite_api(personas: dict[str, PersonaClient], invite_token: str, boot: GatewayBootState):
    """Return `(server, serve_coro)` for the ported /invite endpoint.

    Port 8788 mirrors the legacy alice-bot so the Container App ingress targetPort
    is unchanged. Always served (even with no token) so the /health probe answers;
    /invite itself fail-closes (503) when the token is unset.
    """
    import uvicorn

    from persona_gateway.invite_server import build_invite_app

    app = build_invite_app(personas, invite_token, boot)
    server = uvicorn.Server(uvicorn.Config(app, host="0.0.0.0", port=8788, log_level="warning"))  # noqa: S104  # nosec B104 — Container App ingress requires bind-all; restrict via firewall/CIDR upstream
    log.info("persona_gateway_invite_api_starting", port=8788, token_configured=bool(invite_token))
    return server, server.serve()


async def _wait_until_bound(server, timeout: float = BIND_TIMEOUT_SECONDS) -> bool:
    """Block until uvicorn is actually listening, not merely scheduled.

    `asyncio.create_task(server.serve())` yields a task, not a bound socket. Every
    subsequent await — Postgres, Discord login — could otherwise run first and hang
    with port 8788 still closed, which is precisely what the ACA StartUp probe
    punishes. `server.started` flips only after the socket accepts.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if getattr(server, "started", False):
            return True
        await asyncio.sleep(BIND_POLL_SECONDS)
    log.error("persona_gateway_bind_timeout", port=8788, timeout_s=timeout)
    return False


async def _check_corpus_embed(personas: dict[str, PersonaClient]) -> None:
    """Boot-time liveness probe for the per-persona RAG corpus (finding #2).

    A corpus retrieval embeds the query at runtime via Azure OpenAI. When those
    creds are absent / rotated / point at a dead deployment, `embed_text` swallows
    the failure and returns None — indistinguishable from "no relevant hit", so a
    corpus-wide outage looks exactly like an off-topic turn and NOBODY notices the
    persona lost its library (the 2026-07-16 incident: the gateway shipped with no
    AZURE_OPENAI_* creds and every corpus turn silently degraded to bare model
    knowledge). This probe makes the outage LOUD at boot instead of invisible.

    Off the port-bind critical path (mirrors `_connect_memory`): a probe failure
    logs ERROR but never kills the process — the personas still serve, just
    without their corpus. Skipped entirely when no live persona has a corpus.
    """
    has_corpus = any(getattr(getattr(p, "persona", None), "corpus_namespace", None) for p in personas.values())
    if not has_corpus:
        return
    try:
        from khimeras_shared.corpus.pg_rag import embed_text

        vec = await embed_text("corpus embed boot healthcheck")
    except Exception:
        log.exception("persona_gateway_corpus_embed_check_crashed")
        return
    if vec is None:
        log.error(
            "persona_gateway_corpus_embed_unavailable",
            note="RAG corpus retrieval is DEAD — embed_text returned None; check AZURE_OPENAI_ENDPOINT/KEY + deployment",
        )
    else:
        log.info("persona_gateway_corpus_embed_ok", dim=len(vec))


async def _connect_memory(memory, boot: GatewayBootState) -> None:
    """Connect Postgres off the probe's critical path.

    A cold Postgres must never keep port 8788 from binding: the ACA StartUp probe
    kills the replica, the restart burns another Discord IDENTIFY, and the
    crashloop feeds itself. `MemoryStore._ensure_connection` reconnects before
    every operation, so a boot-time failure degrades rather than kills.
    """
    try:
        await memory.connect()
    except Exception as exc:
        log.exception("persona_gateway_db_connect_failed", error=type(exc).__name__)
        return
    boot.mark_db_connected()


async def _supervise_persona(persona_id: str, coro, boot: GatewayBootState) -> None:
    """Await one persona's Discord session, isolating its death from its siblings.

    `Client.start` only returns when the session ends. Whatever it raises — a
    throttled IDENTIFY, a revoked token, a gateway hang — belongs to THIS persona
    and must not tear down the process: the other bots keep serving, `/invite`
    keeps answering, and `/health` reports the loss.
    """
    try:
        await coro
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        log.exception("persona_gateway_persona_failed", persona_id=persona_id, error=type(exc).__name__)
    else:
        log.error("persona_gateway_persona_exited", persona_id=persona_id)
    boot.mark_persona_down(persona_id)


async def _main() -> None:
    shared = _build_shared()
    if len(shared) == 6:
        memory, agent_client, tts_client, auto_tts_min_chars, invite_token, judge_client = shared
        stt_client = None
    else:
        memory, agent_client, tts_client, stt_client, auto_tts_min_chars, invite_token, judge_client = shared

    intents = discord.Intents.default()
    intents.message_content = True

    personas: dict[str, PersonaClient] = {}
    tokens: dict[str, str] = {}
    for persona in gateway_personas():
        token = os.environ.get(persona.token_env, "").strip()
        if not token:
            log.warning("persona_gateway_no_token", persona_id=persona.persona_id, env=persona.token_env)
            continue
        personas[persona.persona_id] = PersonaClient(
            persona,
            memory,
            agent_client,
            intents=intents,
            tts_client=tts_client,
            stt_client=stt_client,
            auto_tts_min_chars=auto_tts_min_chars,
            judge_client=judge_client,
        )
        tokens[persona.persona_id] = token

    if not personas:
        log.error("persona_gateway_nothing_to_start", note="no persona token configured")
        return

    boot = GatewayBootState()

    # The HTTP server binds BEFORE Postgres and before any Discord login, so the
    # StartUp probe answers as soon as the process is alive. Until a persona
    # finishes on_ready, /health reports serving=false — honestly.
    server, serve_coro = _serve_invite_api(personas, invite_token, boot)
    api_task = asyncio.create_task(serve_coro, name="invite-api")
    if await _wait_until_bound(server):
        log.info("persona_gateway_api_bound", port=8788)

    await _connect_memory(memory, boot)
    await _check_corpus_embed(personas)

    persona_tasks = [
        asyncio.create_task(
            _supervise_persona(persona_id, client.start(tokens[persona_id]), boot),
            name=f"persona:{persona_id}",
        )
        for persona_id, client in personas.items()
    ]
    for persona_id in personas:
        log.info("persona_gateway_starting", persona_id=persona_id)

    try:
        await asyncio.gather(*persona_tasks)
        log.error("persona_gateway_all_personas_down", personas=sorted(personas))
    finally:
        api_task.cancel()
        await asyncio.gather(api_task, return_exceptions=True)
        await memory.close()


def run() -> None:
    """CLI entrypoint: `python -m persona_gateway run`."""
    asyncio.run(_main())
