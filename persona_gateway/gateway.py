"""Khimeras persona gateway — one Discord bot user per sibling persona.

Each registered persona (Vultur, future ones) runs as its OWN Discord bot user
(its own token) but they ALL share ONE brain: the persona-runner, called with a
`persona_id`. This module is deliberately thin — it does NOT run Insult's preset/
flow pipeline. The persona's `<id>.md` (loaded by the runner) defines behavior;
the gateway only:

  1. listens on each persona-bot's gateway,
  2. responds ONLY when that bot is addressed — @mention, its own role mention,
     or a vocative text alias ("frugi, qué opinas"), the complement of Insult's
     suppression gate (same shared predicate; never on its own, never to
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
from collections.abc import Iterable

import discord
import structlog

from khimeras_shared.attachments import process_attachments
from khimeras_shared.memory import MemoryStore
from khimeras_shared.persona import PersonaRuntimeConfig
from khimeras_shared.reactions import add_reactions, parse_reactions, strip_reactions
from khimeras_shared.runner.agent_client import AgentRunnerClient
from khimeras_shared.tts import (
    DEFAULT_SUSURRO_URL,
    build_susurro_tts_client,
    should_auto_tts,
    split_for_tts,
    synthesize_susurro_tts,
)
from khimeras_shared.version import VERSION_TAG
from shared.personas import Persona, gateway_personas
from shared.personas.addressing import any_alias_is_addressee, opens_addressing_insult

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


def should_respond(
    message: discord.Message,
    bot_user: discord.abc.User | None,
    aliases: Iterable[str] = (),
) -> bool:
    """A persona-bot answers iff a NON-bot author addressed it.

    - `author.bot` guard: never auto-invoke, never answer another bot (prevents
      Insult ↔ Vultur loops — same fix as Insult/ALICE v4.20.19).
    - mention-gated: opt-in by design; the host (Insult) is the only omnipresent
      one. A DIRECT user mention (`bot_user in message.mentions`) fires.
    - ROLE mention of the bot's OWN role also fires: pinging the bot's
      integration role (or a custom role assigned to the bot) is the classic "I
      pinged the bot's role expecting it to ping the bot" gotcha — `<@&roleid>`,
      not `<@userid>`, so it never landed in `message.mentions`. We honor it IFF
      the mentioned role is one THIS bot actually carries, and NEVER @everyone
      (its role id equals the guild id), so it stays mass-ping safe.
    - VOCATIVE text alias of THIS persona also fires ("frugi, qué opinas") — the
      complement of Insult's suppression gate. Both sides evaluate the SAME
      predicate (``shared.personas.addressing``): before this, Insult muted on
      any alias occurrence while the gateway needed a mention, so "dile a frugi
      que…" got NO answer from anyone for 5 minutes (P0 2026-07-06 17:24Z). A
      message that OPENS addressing Insult never alias-summons a sibling — the
      head of the message wins, same as Insult's gate.
    """
    if bot_user is None or message.author.bot:
        return False
    if bot_user in message.mentions:
        return True
    guild = getattr(message, "guild", None)
    if guild is not None:
        own_role_ids = {r.id for r in getattr(guild.me, "roles", [])}
        own_role_ids.discard(guild.id)  # @everyone — never a summon
        if any(role.id in own_role_ids for role in getattr(message, "role_mentions", [])):
            return True
    content = message.content or ""
    return not opens_addressing_insult(content) and any_alias_is_addressee(aliases, content)


def edit_summons(
    before: discord.Message,
    after: discord.Message,
    bot_user: discord.abc.User | None,
    aliases: Iterable[str] = (),
) -> bool:
    """True when an edit ADDS an address to this persona (not-addressed →
    addressed transition). An edit to a message the persona already answered
    (addressed before AND after) never re-triggers it."""
    return not should_respond(before, bot_user, aliases) and should_respond(after, bot_user, aliases)


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
        auto_tts_min_chars: int = 0,
    ) -> None:
        super().__init__(intents=intents)
        self.persona = persona
        self.memory = memory
        self.agent_client = agent_client
        # TTS: this persona owns its OWN voice. None when susurro TTS env is unset
        # → 🔊 on its messages is silently skipped (voice off), never spoken by
        # Insult (Insult's VoiceCog skips sibling-authored messages).
        self.tts_client = tts_client
        # Auto-speak replies at/above this length (0 = off, manual 🔊 only).
        self.auto_tts_min_chars = auto_tts_min_chars
        # Strong refs to fire-and-forget reaction tasks so the event loop
        # doesn't garbage-collect them mid-flight (RUF006).
        self._bg_tasks: set[asyncio.Task[None]] = set()

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
        susurro TTS client was wired."""
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
        await self._speak(channel, message.content.strip(), reason="manual")

    async def _speak(self, channel, text: str, *, reason: str) -> None:
        """Synthesize ``text`` in this persona's voice and post it as audio.

        The full text is split into ≤4096-char segments (the speech cap) so a long
        reply is spoken IN FULL across several clips, never truncated. No-op when
        TTS is off or the text is empty. ``reason`` ("manual" 🔊 / "auto" long
        reply) is logged so the two paths stay distinguishable."""
        if self.tts_client is None or not text:
            return
        segments = split_for_tts(text)
        try:
            async with channel.typing():
                for idx, segment in enumerate(segments):
                    audio = await synthesize_susurro_tts(
                        self.tts_client,
                        segment,
                        voice=self.persona.tts_voice,
                    )
                    fname = f"{self.persona.persona_id}{'' if len(segments) == 1 else f'-{idx + 1}'}.mp3"
                    await channel.send(file=discord.File(io.BytesIO(audio), filename=fname))
            log.info(
                "persona_gateway_tts_sent",
                persona_id=self.persona.persona_id,
                voice=self.persona.tts_voice,
                chars=len(text),
                segments=len(segments),
                reason=reason,
            )
        except Exception:
            log.exception("persona_gateway_tts_failed", persona_id=self.persona.persona_id, reason=reason)

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

    async def _dispatch(self, message: discord.Message) -> None:
        """Shared guarded entry for message + edit summons."""
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
        attachment_blocks = await self._process_attachments(message)
        if not ask and not attachment_blocks:
            return  # bare @mention with no text and no readable attachment

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
            discord_message_id=str(message.id),
        )

        user_content: str | list[dict] = ask
        if attachment_blocks:
            text_blocks = [{"type": "text", "text": ask}] if ask else []
            user_content = [*text_blocks, *attachment_blocks]
        messages = [*format_context(recent), {"role": "user", "content": user_content}]
        await self._run_and_deliver(
            channel=message.channel,
            channel_id=channel_id,
            user_id=user_id,
            guild_id=guild_id,
            channel_name=channel_name,
            messages=messages,
            react_to=message,
        )

    async def _process_attachments(self, message: discord.Message) -> list[dict]:
        """Image/document attachments of the summoning message → Anthropic blocks.

        Reuses Insult's shared processor (5MB cap with image compression,
        png/jpg/gif/webp + text/pdf, in-character rejection notices). The blocks
        ride the final user message; `AgentRunnerClient` extracts them and the
        runner builds the multimodal SDK input — same E2E path Insult uses, so
        siblings finally SEE images (P0 2026-07-07: "no llegó imagen a mi mesa
        de disección"). Invite turns have no source message, so they carry none.
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
    ) -> None:
        """Entry point for the gateway's ported /invite handler.

        Mirrors the legacy ``personas.alice.cogs.chat.respond_to_invite`` contract
        but routes through the persona-runner (this persona's brain) instead of a
        persona-local LLM. Insult's ``reason`` is injected as the FRESHEST turn —
        instruction context, not a visible user message — so the persona reads the
        thread and responds with the lens the reason asks for. No user turn is
        stored (there is none; Insult already wrote the message that triggered it).
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

        recent = await self.memory.get_recent(channel_id, RECENT_LIMIT)
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
        await self._run_and_deliver(
            channel=channel,
            channel_id=channel_id,
            user_id=str(self.user.id) if self.user else "",
            guild_id=guild_id,
            channel_name=channel_name,
            messages=messages,
            turn_kind="invite",
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
    ) -> None:
        """Shared tail for mention + invite: runner call → post → persist.

        Typing keepalive is a fire-and-forget background task so the user sees
        "[persona] is typing…" during the long runner call. Deliberately NOT
        `async with channel.typing()` (blocks on __aenter__, vulnerable to 429
        killing the turn before the runner runs — anti-pattern #1). Instead: a
        short-lived task that re-triggers typing every ~9s and stops when the
        stop_event is set (after the runner responds).
        """
        bot_id = self.user.id if self.user else 0
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
            )
        finally:
            _typing_stop.set()
            _typing_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await _typing_task

        text = (resp.text or "").strip()
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
        if not text:
            return

        pieces = chunk(text)
        tag = f"\n-# {VERSION_TAG}"
        if pieces and len(pieces[-1]) + len(tag) <= 2000:
            pieces[-1] += tag
        for piece in pieces:
            await channel.send(piece)

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
            turn_kind=turn_kind,
        )

        # Auto-TTS: a long reply ships a voice clip of the FULL text so you can
        # listen instead of reading a wall. Gateway-only (the persona gateway has
        # no Arbor path, so arbor_active=False); gated by auto_tts_min_chars (0=off).
        if should_auto_tts(text, min_chars=self.auto_tts_min_chars, arbor_active=False):
            await self._speak(channel, text, reason="auto")


def _build_shared() -> tuple[MemoryStore, AgentRunnerClient, object | None, int, str]:
    """Construct the deps shared by all persona-bots (same wiring as Insult).

    Also builds the susurro TTS client so each persona can speak its own 🔊 audio.
    TTS is OPTIONAL — when SUSURRO_KEY is unset the client is None and voice is
    simply off (the gateway still runs); it is never delegated to Insult.

    The last element is the `/invite` bearer token (INSULT_TO_ALICE_TOKEN) — the
    same secret the legacy alice-bot endpoint used, so repointing the caller is a
    no-op on the contract.
    """
    config = PersonaRuntimeConfig.from_env()

    memory = MemoryStore(config.postgres_url.get_secret_value())
    runner_url = config.persona_runner_url
    runner_token = config.persona_runner_token.get_secret_value()
    if not (runner_url and runner_token):
        raise RuntimeError("persona gateway requires PERSONA_RUNNER_URL + token")
    # timeout_s=240 (vs the 120 default): a sibling's FIRST turn — cold session +
    # curated facts + behavioral guidance — measured 134.5s in prod (2026-07-06,
    # frugivoro meal plan). The 120s default read-timeout hung up 14s before the
    # runner finished, so the user got the "…" fallback while a complete reply
    # died unread. Siblings are mention-gated with a typing keepalive running, so
    # a longer wait is honest UX; Insult's plumbing keeps its own 120s because
    # its timeout feeds the ALICE failover path.
    agent_client = AgentRunnerClient(runner_url=runner_url, runner_token=runner_token, timeout_s=240.0)

    tts_client = build_susurro_tts_client(
        base_url=os.environ.get("SUSURRO_URL", DEFAULT_SUSURRO_URL),
        api_key=os.environ.get("SUSURRO_KEY", ""),
    )
    try:
        auto_tts_min_chars = int(os.environ.get("AUTO_TTS_MIN_CHARS", "0"))
    except ValueError:
        auto_tts_min_chars = 0
    log.info(
        "persona_gateway_tts_configured",
        enabled=tts_client is not None,
        auto_tts_min_chars=auto_tts_min_chars,
    )
    invite_token = config.insult_to_alice_token.get_secret_value()
    return memory, agent_client, tts_client, auto_tts_min_chars, invite_token


def _serve_invite_api(personas: dict[str, PersonaClient], invite_token: str):
    """Return the uvicorn serve() coroutine for the ported /invite endpoint.

    Port 8788 mirrors the legacy alice-bot so the Container App ingress targetPort
    is unchanged. Bound to 0.0.0.0 for the ACA ingress. Always served (even with
    no token) so the /health probe answers; /invite itself fail-closes (503) when
    the token is unset.
    """
    import uvicorn

    from persona_gateway.invite_server import build_invite_app

    app = build_invite_app(personas, invite_token)
    server = uvicorn.Server(uvicorn.Config(app, host="0.0.0.0", port=8788, log_level="warning"))  # noqa: S104  # nosec B104 — Container App ingress requires bind-all; restrict via firewall/CIDR upstream
    log.info("persona_gateway_invite_api_starting", port=8788, token_configured=bool(invite_token))
    return server.serve()


async def _main() -> None:
    memory, agent_client, tts_client, auto_tts_min_chars, invite_token = _build_shared()
    await memory.connect()

    intents = discord.Intents.default()
    intents.message_content = True

    personas: dict[str, PersonaClient] = {}
    starts = []
    for persona in gateway_personas():
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
            auto_tts_min_chars=auto_tts_min_chars,
        )
        personas[persona.persona_id] = client
        starts.append(client.start(token))
        log.info("persona_gateway_starting", persona_id=persona.persona_id)

    if not starts:
        log.error("persona_gateway_nothing_to_start", note="no persona token configured")
        return

    # The /invite HTTP server runs in the same event loop as the bots, sharing the
    # live PersonaClient registry so an invite routes to the persona's own brain.
    starts.append(_serve_invite_api(personas, invite_token))

    try:
        await asyncio.gather(*starts)
    finally:
        await memory.close()


def run() -> None:
    """CLI entrypoint: `python -m persona_gateway run`."""
    asyncio.run(_main())
