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
- reply delivery (chunk + tag + send) → `persona_gateway.delivery`
- durable markers (research/agenda/remind/remember) → `persona_gateway.markers`
- the three drain loops → `persona_gateway.workers`
- background fact extraction → `persona_gateway.facts`
- per-persona TTS → `persona_gateway.voice`
- operator-tunable cadences/timeouts → `persona_gateway.config`
Reactions (`[REACT:]`) stay in `_run_and_deliver` (they need the live message and
`add_reactions`). Bootstrap (`_build_shared` … `_main`) lives at the bottom.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import time

import discord
import structlog
from discord.ext import tasks

from khimeras_shared.attachments import process_attachments
from khimeras_shared.guidance import guidance_for_turn
from khimeras_shared.memory import MemoryStore
from khimeras_shared.persona import PersonaRuntimeConfig
from khimeras_shared.prompts import PromptCache
from khimeras_shared.reactions import add_reactions, parse_reactions, strip_reactions
from khimeras_shared.runner.agent_client import AgentRunnerClient
from khimeras_shared.runner.judge_client import RunnerJudgeClient
from khimeras_shared.tts import build_susurro_tts_client
from persona_gateway.boot import GatewayBootState
from persona_gateway.config import CONFIG
from persona_gateway.delivery import DISCORD_LIMIT, chunk, send_chunked
from persona_gateway.facts import FactExtractor
from persona_gateway.markers import MarkerRouter
from persona_gateway.routing import clean_mention, edit_summons, format_context, should_respond
from persona_gateway.voice import VoiceService
from persona_gateway.workers import AgendaWorker, ReminderWorker, ResearchWorker
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
        self.auto_tts_min_chars = auto_tts_min_chars
        # Strong refs to fire-and-forget tasks so the loop doesn't GC them (RUF006).
        self._bg_tasks: set[asyncio.Task[None]] = set()

        # Injected services — the logic lives here, the client just delegates.
        self._markers = MarkerRouter(persona, memory)
        self._voice = VoiceService(persona, tts_client)
        self._facts = FactExtractor(persona, memory, self._bg_tasks)
        self._research = ResearchWorker(persona, memory, agent_client)
        self._agenda = AgendaWorker(persona, memory, agent_client)
        self._reminders = ReminderWorker(persona, memory, agent_client, _PROMPT_CACHE)

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
        for loop in (self._research_drain, self._agenda_check, self._reminder_drain):
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

    # --- reception -----------------------------------------------------------

    async def on_message(self, message: discord.Message) -> None:
        if not should_respond(message, self.user, self.persona.aliases):
            return
        await self._dispatch(message)

    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        """An edit that ADDS an address to this persona summons it (P0 2026-07-06):
        Alex sent his pantry list clean and edited in "@frugi" — `on_message` had
        already run on the clean content, so the mention summoned nobody. Fires
        ONLY on the not-addressed → addressed transition, so an edit to a message
        this persona already answered never re-triggers it."""
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
        attachment_blocks = await self._process_attachments(message)
        if not ask and not attachment_blocks:
            return  # bare @mention with no text and no readable attachment

        # Recent context BEFORE storing the current turn, so it isn't duplicated.
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
        context = format_context(recent)
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
        await self._run_and_deliver(
            channel=message.channel,
            channel_id=channel_id,
            user_id=user_id,
            guild_id=guild_id,
            channel_name=channel_name,
            messages=messages,
            react_to=message,
            behavioral_guidance=guidance,
        )
        # A mention carries a REAL user ask — the only turn worth mining for facts.
        # Runs AFTER delivery, in the background, so the extraction's LLM round-trip
        # never sits between the user and their reply.
        self._spawn_fact_extraction(
            user_id,
            message.author.display_name,
            [*recent[-CONFIG.facts_recent_window :], {"user_name": message.author.display_name, "content": ask}],
        )

    def _spawn_fact_extraction(self, user_id: str, user_name: str, recent: list[dict]) -> None:
        """Delegates to the fact backstop (kept as a method: tests call it).
        Reads `self.judge_client` LIVE so a toggle to None disables it next turn."""
        self._facts.spawn(self.judge_client, user_id, user_name, recent)

    async def _process_attachments(self, message: discord.Message) -> list[dict]:
        """Image/document attachments of the summoning message → Anthropic blocks.

        Reuses Insult's shared processor (5MB cap with image compression,
        png/jpg/gif/webp + text/pdf, in-character rejection notices). The blocks
        ride the final user message; `AgentRunnerClient` extracts them and the
        runner builds the multimodal SDK input — same E2E path Insult uses, so
        siblings finally SEE images (P0 2026-07-07). Invite turns have no source
        message, so they carry none.
        """
        if not message.attachments or message.flags.voice:
            return []
        blocks, errors = await process_attachments(message.attachments)
        for err in errors:
            with contextlib.suppress(discord.HTTPException):
                await message.channel.send(err)
        log.info(
            "persona_gateway_attachments_processed",
            persona_id=self.persona.persona_id,
            blocks=len(blocks),
            errors=len(errors),
        )
        return blocks

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
        channel = self.get_channel(int(channel_id))
        if channel is None:
            with contextlib.suppress(discord.HTTPException):
                channel = await self.fetch_channel(int(channel_id))
        if not isinstance(channel, discord.abc.Messageable):
            log.warning(
                "persona_gateway_invite_channel_not_found",
                persona_id=self.persona.persona_id,
                channel_id=channel_id,
            )
            return

        recent = await self.memory.get_recent(channel_id, CONFIG.recent_limit)
        if invited_by == "host_router":
            instruction = (
                f"[El turno es tuyo: la conversación del canal es la que tú traías. Contexto: {reason}] "
                "Lee el hilo de arriba y responde directo al último mensaje, en tu voz."
            )
        else:
            instruction = (
                f"[Insult te invitó a este turno. Razón: {reason}] "
                "Lee el hilo de arriba y responde con la mirada que esa razón pide."
            )
        messages = [*format_context(recent), {"role": "user", "content": instruction}]
        log.info(
            "persona_gateway_invite_accepted",
            persona_id=self.persona.persona_id,
            channel_id=channel_id,
            invited_by=invited_by,
            reason_preview=reason[:100],
        )
        # The summoner's wire carries the Discord message that triggered this turn
        # so the persona's [REACT:] markers land on it. Without a resolved target,
        # _run_and_deliver strips the markers and the reactions die (2026-07-14
        # bug). Best-effort: an unfetchable message degrades to text-only.
        react_to: discord.Message | None = None
        if trigger_message_id:
            try:
                react_to = await channel.fetch_message(int(trigger_message_id))
            except (discord.HTTPException, ValueError):
                log.warning(
                    "persona_gateway_invite_trigger_fetch_failed",
                    persona_id=self.persona.persona_id,
                    channel_id=channel_id,
                    trigger_message_id=trigger_message_id,
                )
        await self._run_and_deliver(
            channel=channel,
            channel_id=channel_id,
            user_id=str(self.user.id) if self.user else "",
            guild_id=guild_id,
            channel_name=channel_name,
            messages=messages,
            turn_kind="invite",
            react_to=react_to,
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
    ) -> None:
        """Shared tail for mention + invite: runner call → react → markers → send.

        Typing keepalive is a fire-and-forget background task so the user sees
        "[persona] is typing…" during the long runner call. Deliberately NOT
        `async with channel.typing()` (blocks on __aenter__, vulnerable to 429
        killing the turn before the runner runs — anti-pattern #1): a short task
        that re-triggers typing every ~9s until the stop_event is set.
        """
        _typing_stop = asyncio.Event()

        async def _typing_keepalive() -> None:
            while not _typing_stop.is_set():
                with contextlib.suppress(discord.HTTPException):
                    async with channel.typing():
                        with contextlib.suppress(TimeoutError):
                            await asyncio.wait_for(_typing_stop.wait(), timeout=9.0)
                    if _typing_stop.is_set():
                        break

        _typing_task = asyncio.create_task(_typing_keepalive())
        try:
            resp = await self.agent_client.chat(
                "",  # system_prompt ignored by the runner
                messages,
                channel_id=channel_id,
                user_id=user_id,
                persona_id=self.persona.persona_id,
                behavioral_guidance=behavioral_guidance,
            )
        finally:
            _typing_stop.set()
            _typing_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await _typing_task

        text = (resp.text or "").strip()

        # Reactions FIRST (they need the live `react_to` message and the
        # module-level `add_reactions` the tests monkeypatch).
        reactions = parse_reactions(text)
        if reactions:
            text = strip_reactions(text)
            if react_to is not None:
                task = asyncio.create_task(add_reactions(react_to, reactions))
                self._bg_tasks.add(task)
                task.add_done_callback(self._bg_tasks.discard)
                log.info(
                    "persona_gateway_reactions_fired",
                    persona_id=self.persona.persona_id,
                    emojis=reactions,
                    turn_kind=turn_kind,
                )
            else:
                log.warning(
                    "persona_gateway_reactions_dropped_no_target",
                    persona_id=self.persona.persona_id,
                    emojis=reactions,
                    turn_kind=turn_kind,
                )

        # Durable markers (research/agenda/remind/remember): persist the side
        # effects and strip them so only the in-character ack reaches Discord.
        text = await self._markers.route(text, channel_id=channel_id, guild_id=guild_id, user_id=user_id)
        if not text:
            return

        await send_chunked(channel, text)
        await self.memory.store(
            channel_id,
            str(self.user.id) if self.user else "0",
            self.persona.display_name,
            "assistant",
            text,
            for_user_id=user_id,
            guild_id=guild_id,
            channel_name=channel_name,
            model_used=getattr(resp, "model_used", None),
        )
        log.info(
            "persona_gateway_turn_complete",
            persona_id=self.persona.persona_id,
            channel_id=channel_id,
            chars=len(text),
            turn_kind=turn_kind,
        )

        # Auto-TTS: a long reply ships a voice clip of the FULL text so you can
        # listen instead of reading a wall (gated by auto_tts_min_chars; 0=off).
        if self._voice.should_auto_speak(text, self.auto_tts_min_chars):
            await self._voice.speak(channel, text, reason="auto")


# --- bootstrap: shared deps, the /invite server, and the process lifecycle ----
# Kept in this module (not a separate app.py) because the boot-resilience test
# monkeypatches these names on `persona_gateway.gateway` and drives `_main` —
# moving them would break that regression guard for no structural gain.


def _build_shared() -> tuple[MemoryStore, AgentRunnerClient, object | None, int, str, RunnerJudgeClient]:
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
    log.info(
        "persona_gateway_tts_configured",
        enabled=tts_client is not None,
        auto_tts_min_chars=CONFIG.auto_tts_min_chars,
    )
    invite_token = config.insult_to_alice_token.get_secret_value()
    return memory, agent_client, tts_client, CONFIG.auto_tts_min_chars, invite_token, judge_client


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
    memory, agent_client, tts_client, auto_tts_min_chars, invite_token, judge_client = _build_shared()

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
