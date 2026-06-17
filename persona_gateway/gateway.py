"""Khimeras persona gateway — one Discord bot user per sibling persona.

Each registered persona (Vultur, future ones) runs as its OWN Discord bot user
(its own token) but they ALL share ONE brain: the insult-runner, called with a
`persona_id`. This module is deliberately thin — it does NOT run Insult's preset/
flow pipeline. The persona's `<id>.md` (loaded by the runner) defines behavior;
the gateway only:

  1. listens on each persona-bot's gateway,
  2. responds ONLY when that bot is @mentioned (never on its own, never to
     another bot — mirrors the anti-self-invoke guard from Insult/ALICE),
  3. replays recent channel context + the cleaned message to the runner,
  4. posts the reply as that bot user (native name/avatar — no webhook),
  5. persists both turns to the shared Postgres so Insult and the siblings see
     one another's words.

A single process hosts all persona-bots via `asyncio.gather`, sharing one
MemoryStore + one AgentRunnerClient. Insult stays in its own process untouched.
"""

from __future__ import annotations

import asyncio
import contextlib
import io
import os
import re

import discord
import structlog

from khimeras_shared.memory import MemoryStore
from khimeras_shared.persona import PersonaRuntimeConfig
from khimeras_shared.runner.agent_client import AgentRunnerClient
from khimeras_shared.tts import build_azure_tts_client, synthesize_azure_tts
from shared.personas import Persona, all_personas

SPEAK_EMOJI = "🔊"

# Runtime infra (Postgres DSN + runner URL/token) comes from the neutral
# `PersonaRuntimeConfig` — env-backed, zero persona identity — so the gateway no
# longer reaches into `personas.insult.config`. All fields default to empty, so
# this import is safe at module top-level even when no `.env` is present (CI).

log = structlog.get_logger()

RECENT_LIMIT = 30  # how many prior channel messages to replay to the runner
DISCORD_LIMIT = 1990  # leave headroom under Discord's 2000-char message cap


def clean_mention(content: str, bot_id: int) -> str:
    """Strip this bot's @mention(s) from the message text, leaving the ask.

    Discord renders mentions as `<@id>` / `<@!id>`. We remove only THIS bot's
    mention so "@Vultur reséñame Creep" → "reséñame Creep". Other mentions are
    left intact (they may be meaningful context).
    """
    cleaned = re.sub(rf"<@!?{bot_id}>", "", content)
    return cleaned.strip()


def should_respond(message: discord.Message, bot_user: discord.abc.User | None) -> bool:
    """A persona-bot answers iff it was @mentioned by a NON-bot author.

    - `author.bot` guard: never auto-invoke, never answer another bot (prevents
      Insult ↔ Vultur loops — same fix as Insult/ALICE v4.20.19).
    - mention-gated: opt-in by design; the host (Insult) is the only omnipresent
      one. `bot_user in message.mentions` is a DIRECT user mention (not @everyone
      or a role), so it doesn't fire on mass pings.
    """
    if bot_user is None or message.author.bot:
        return False
    return bot_user in message.mentions


def format_context(recent: list[dict]) -> list[dict]:
    """Turn stored rows into speaker-prefixed message dicts for the runner.

    Mirrors how the Insult plumbing frames context: each line is
    "Name: text" so the runner can attribute who said what. Role is kept as a
    plain "user" turn — the runner reads it as channel context, not as its own
    history (the persona-bot's own past replies are stored as role='assistant'
    but here we only need the readable transcript)."""
    out: list[dict] = []
    for m in recent:
        name = m.get("user_name") or "?"
        content = (m.get("content") or "").strip()
        if content:
            out.append({"role": "user", "content": f"{name}: {content}"})
    return out


def chunk(text: str, limit: int = DISCORD_LIMIT) -> list[str]:
    """Split a reply into Discord-sized pieces on paragraph/space boundaries."""
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= limit:
        return [text]
    parts: list[str] = []
    remaining = text
    while len(remaining) > limit:
        cut = remaining.rfind("\n", 0, limit)
        if cut < limit // 2:
            cut = remaining.rfind(" ", 0, limit)
        if cut < limit // 2:
            cut = limit
        parts.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()
    if remaining:
        parts.append(remaining)
    return parts


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
        tts_deployment: str = "",
    ) -> None:
        super().__init__(intents=intents)
        self.persona = persona
        self.memory = memory
        self.agent_client = agent_client
        # TTS: this persona owns its OWN voice. None when Azure TTS env is unset
        # → 🔊 on its messages is silently skipped (voice off), never spoken by
        # Insult (Insult's VoiceCog skips sibling-authored messages).
        self.tts_client = tts_client
        self.tts_deployment = tts_deployment

    async def on_ready(self) -> None:
        log.info(
            "persona_gateway_ready",
            persona_id=self.persona.persona_id,
            bot_id=str(self.user.id) if self.user else None,
            bot_name=str(self.user) if self.user else None,
            guilds=len(self.guilds),
        )

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        """🔊 on one of THIS persona's own messages → speak it in the persona's
        own voice, posted by the persona bot with its own typing.

        Guards: only the 🔊 emoji, never our own reaction, and ONLY our own
        messages (a 🔊 on an Insult/human message belongs to Insult's VoiceCog —
        we skip it so the two don't double-speak). Voice is off (no-op) when no
        Azure TTS client was wired."""
        if str(payload.emoji) != SPEAK_EMOJI:
            return
        if self.user is None or payload.user_id == self.user.id:
            return
        if self.tts_client is None:
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
        text = message.content.strip()
        if not text:
            return
        try:
            async with channel.typing():
                audio = await synthesize_azure_tts(
                    self.tts_client,
                    text,
                    voice=self.persona.tts_voice,
                    deployment=self.tts_deployment,
                )
            await channel.send(file=discord.File(io.BytesIO(audio), filename=f"{self.persona.persona_id}.mp3"))
            log.info(
                "persona_gateway_tts_sent",
                persona_id=self.persona.persona_id,
                voice=self.persona.tts_voice,
                chars=len(text),
            )
        except Exception:
            log.exception("persona_gateway_tts_failed", persona_id=self.persona.persona_id)

    async def on_message(self, message: discord.Message) -> None:
        if not should_respond(message, self.user):
            return
        try:
            await self._handle(message)
        except Exception:
            log.exception("persona_gateway_turn_failed", persona_id=self.persona.persona_id)
            # Never expose internals. The recovery send gets its own guard; if
            # the channel is rate-limited a reaction (different bucket) survives.
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
        if not ask:
            return  # bare @mention with no text — nothing to review

        # Recent context BEFORE storing the current turn, so it isn't duplicated.
        recent = await self.memory.get_recent(channel_id, RECENT_LIMIT)

        # Persist the user's turn (shared Postgres → Insult & siblings see it).
        await self.memory.store(
            channel_id,
            user_id,
            message.author.display_name,
            "user",
            ask,
            guild_id=guild_id,
            channel_name=channel_name,
        )

        messages = [*format_context(recent), {"role": "user", "content": ask}]

        # Typing keepalive — fire-and-forget background task so the user sees
        # "[Vultur] is typing…" during the long runner call. Deliberately NOT
        # `async with channel.typing()` (blocks on __aenter__, vulnerable to 429
        # killing the turn before the runner runs — anti-pattern #1).
        # Instead: a short-lived task that triggers typing every 7s and stops
        # when a stop_event is set (after the runner responds).
        _typing_stop = asyncio.Event()

        async def _typing_keepalive() -> None:
            while not _typing_stop.is_set():
                with contextlib.suppress(discord.HTTPException):
                    # discord.py's Typing context manager sends a typing event
                    # and has a built-in 10s keepalive. We enter+exit every 9s
                    # in our own loop so the indicator stays alive for long turns.
                    async with message.channel.typing():
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
            )
        finally:
            _typing_stop.set()
            _typing_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await _typing_task

        text = (resp.text or "").strip()
        if not text:
            return

        for piece in chunk(text):
            await message.channel.send(piece)

        await self.memory.store(
            channel_id,
            str(bot_id),
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
        )


def _build_shared() -> tuple[MemoryStore, AgentRunnerClient, object | None, str]:
    """Construct the deps shared by all persona-bots (same wiring as Insult).

    Also builds the Azure TTS client so each persona can speak its own 🔊 audio.
    TTS is OPTIONAL — when the AZURE_OPENAI_* env is unset the client is None and
    voice is simply off (the gateway still runs); it is never delegated to Insult.
    """
    config = PersonaRuntimeConfig.from_env()

    memory = MemoryStore(config.postgres_url.get_secret_value())
    runner_url = config.insult_agent_runner_url
    runner_token = config.insult_agent_runner_token.get_secret_value()
    if not (runner_url and runner_token):
        raise RuntimeError("persona gateway requires INSULT_AGENT_RUNNER_URL + token")
    agent_client = AgentRunnerClient(runner_url=runner_url, runner_token=runner_token)

    tts_client = build_azure_tts_client(
        endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT", ""),
        api_key=os.environ.get("AZURE_OPENAI_KEY", ""),
    )
    tts_deployment = os.environ.get("AZURE_OPENAI_TTS_DEPLOYMENT", "tts")
    log.info("persona_gateway_tts_configured", enabled=tts_client is not None, deployment=tts_deployment)
    return memory, agent_client, tts_client, tts_deployment


async def _main() -> None:
    memory, agent_client, tts_client, tts_deployment = _build_shared()
    await memory.connect()

    intents = discord.Intents.default()
    intents.message_content = True

    starts = []
    for persona in all_personas():
        token = os.environ.get(persona.token_env, "").strip()
        if not token:
            log.warning("persona_gateway_no_token", persona_id=persona.persona_id, env=persona.token_env)
            continue
        client = PersonaClient(
            persona,
            memory,
            agent_client,
            intents=intents,
            tts_client=tts_client,
            tts_deployment=tts_deployment,
        )
        starts.append(client.start(token))
        log.info("persona_gateway_starting", persona_id=persona.persona_id)

    if not starts:
        log.error("persona_gateway_nothing_to_start", note="no persona token configured")
        return

    try:
        await asyncio.gather(*starts)
    finally:
        await memory.close()


def run() -> None:
    """CLI entrypoint: `python -m persona_gateway run`."""
    asyncio.run(_main())
