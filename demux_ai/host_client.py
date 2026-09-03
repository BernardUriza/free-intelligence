"""The Discord shell of the omnipresent host (#6, slice 4 — code-complete).

Thin glue over the tested `HostDispatchLoop`: `on_message` ingests every message
into the loop's batcher, a 1s `tasks.loop` flushes due batches and dispatches them.
The host is the ONLY omnipresent listener once it's live (Insult demotes to a
routed persona at cutover) — so it reads all message content and routes each burst
to whoever the router picks.

Split on purpose: the field-mapping (`_ingest`) is pure and unit-tested; the
`discord.Client` lifecycle (`start(token)`, the loop scheduler) is declared glue
whose only untestable part is the literal network connection — which needs the
host's Discord token, Bernard's cutover atom. `run_host` refuses to start without
one, so the shell is dormant (no double-omnipresent conflict) until he flips it on.
"""

from __future__ import annotations

import asyncio
import os
import time

import discord
import structlog
from discord.ext import tasks

from demux_ai.fallback import deliver_or_fallback
from demux_ai.host_loop import HostDispatchLoop
from khimeras_shared.stt import (
    DEFAULT_AUDIO_CONTENT_TYPE,
    WAKE_ETA_SECONDS,
    SusurroSttClient,
    build_susurro_stt_client,
    is_audio_attachment,
    susurro_is_awake,
    transcribe_voice_message,
    wake_susurro,
)
from shared.personas.registry import get_persona, persona_id_by_bot_user_id, persona_id_by_role_name

log = structlog.get_logger()

HOST_TOKEN_ENV = "HOST_DISCORD_TOKEN"  # noqa: S105 # nosec B105 — env-var NAME, not a secret
TICK_SECONDS = 1.0
ECHO_LIMIT = 1990


class HostClient(discord.Client):
    """Omnipresent receiver: every message → the dispatch loop's batcher."""

    def __init__(
        self,
        dispatch_loop: HostDispatchLoop,
        *,
        intents: discord.Intents,
        stt_client: SusurroSttClient | None = None,
    ) -> None:
        super().__init__(intents=intents)
        self.dispatch_loop = dispatch_loop
        self._stt_client = stt_client
        self._bg_tasks: set[asyncio.Task] = set()

    async def dispatch_with_fallback(self, tool_input: dict, **summon_kwargs) -> bool:
        """The host's dispatcher: summon WITH wait in the background and own the
        outcome — one retry, then a notice in the host's voice (`demux_ai.fallback`).

        Same signature as `summon_persona` so `route_and_dispatch` cannot tell
        them apart. Returns True the moment the turn is SCHEDULED (that is what
        `host_dispatched.accepted` has always meant); the real per-turn receipt
        is the `host_turn_*` event the background task emits. Background on
        purpose: a turn takes up to ~4 min and the tick loop is serial over
        channels — awaiting it here would stall every other conversation.
        """
        task = asyncio.create_task(deliver_or_fallback(tool_input, say=self.say_in_channel, **summon_kwargs))
        self._bg_tasks.add(task)
        task.add_done_callback(self._bg_tasks.discard)
        return True

    async def say_in_channel(self, channel_id: str, text: str) -> None:
        """Raw sidecar send by channel id — no version tag, no chunking. The
        fallback's voice: the HOUSE says the persona could not answer, instead
        of the persona mumbling "…" in its own name."""
        channel = self.get_channel(int(channel_id)) or await self.fetch_channel(int(channel_id))
        await channel.send(text)  # type: ignore[union-attr]

    def _ingest(self, message: discord.Message, now: float, voice_text: str = "") -> bool:
        """Map a Discord message onto the loop and batch it. Pure over the loop —
        returns whether it was accepted (a human, non-command message)."""
        mentioned_ids = [str(user.id) for user in getattr(message, "mentions", [])]
        mentioned_role_names = [role.name for role in getattr(message, "role_mentions", [])]
        attachment_names = [a.filename for a in getattr(message, "attachments", []) if getattr(a, "filename", None)]
        return self.dispatch_loop.handle_message(
            channel_id=str(message.channel.id),
            author_id=str(message.author.id),
            author_is_bot=bool(message.author.bot),
            text=message.content or "",
            now=now,
            author_name=getattr(message.author, "display_name", ""),
            message_id=str(message.id),
            mentioned_ids=mentioned_ids,
            mentioned_role_names=mentioned_role_names,
            attachment_names=attachment_names,
            voice_text=voice_text,
        )

    async def transcribe_voice(self, message: discord.Message) -> str:
        """Voice-message audio → text, or "" when STT is off or fails.

        The router used to decide WHO answers a voice note from the filename
        alone ("[adjuntó: voice-message.ogg]") — routing blind to what was
        actually said (2026-07-23). Fail-soft on purpose: a dead susurro must
        degrade routing to the old filename note, never drop the turn.
        """
        if self._stt_client is None or not getattr(message, "attachments", None):
            return ""
        audio_attachments = [
            attachment
            for attachment in message.attachments
            if is_audio_attachment(
                content_type=getattr(attachment, "content_type", None),
                filename=getattr(attachment, "filename", None),
                voice_message=bool(getattr(message.flags, "voice", False)),
            )
        ]
        if not audio_attachments:
            return ""
        await self._ensure_susurro_awake(message)
        parts: list[str] = []
        for attachment in audio_attachments:
            try:
                audio = await attachment.read()
                transcript = await transcribe_voice_message(
                    audio,
                    base_url=self._stt_client.base_url,
                    api_key=self._stt_client.api_key,
                    content_type=getattr(attachment, "content_type", None) or DEFAULT_AUDIO_CONTENT_TYPE,
                )
            except Exception as exc:
                log.error("host_stt_failed", error=str(exc), error_type=type(exc).__name__)
                continue
            if transcript:
                parts.append(str(transcript))
        if parts:
            log.info("host_stt_transcribed", parts=len(parts), length=sum(len(p) for p in parts))
        return "\n".join(parts)

    async def _ensure_susurro_awake(self, message: discord.Message) -> None:
        """Wake susurro before transcribing, and SAY SO while it boots.

        Susurro is kept scale-to-zero on purpose (it costs nothing asleep), so a
        voice note is routinely the request that boots it — roughly 30 seconds
        during which the user has no idea anything is happening. Before this, the
        wait ended in "el audio no me entra" and the note was simply lost.

        The honest UX Bernard asked for: probe first (a warm susurro announces
        nothing at all), and when it IS asleep tell him it is asleep, give him
        the estimate, boot it, prove the pipeline with a hello-world clip, and
        only then transcribe his audio. Fail-soft throughout — a failed
        announcement or a wake that never lands must not stop the attempt, since
        the transcription itself may still succeed.
        """
        if self._stt_client is None:
            return
        if await susurro_is_awake(base_url=self._stt_client.base_url):
            return
        await self._say_sidecar(
            message,
            f"🔊 El servidor de transcripción está dormido. Dame ~{WAKE_ETA_SECONDS} s "
            f"para despertarlo y te entrego tu audio.",
        )
        woke = await wake_susurro(base_url=self._stt_client.base_url, api_key=self._stt_client.api_key)
        if not woke:
            await self._say_sidecar(
                message,
                "🔊 No logré despertar el servidor de transcripción. Voy a intentar tu audio de todos modos.",
            )

    async def _say_sidecar(self, message: discord.Message, text: str) -> None:
        """Post an operational note to the channel: raw send, no version tag, no
        chunking — same sidecar shape as the transcript echo, never a turn."""
        try:
            await message.channel.send(text)
        except Exception:
            log.exception("host_voice_notice_failed", channel_id=str(message.channel.id))

    async def on_ready(self) -> None:
        log.info("host_ready", bot_id=self.user.id if self.user else None)
        if not self._tick.is_running():
            self._tick.start()

    async def echo_transcript(self, message: discord.Message, text: str) -> None:
        """Publish what the voice note SAID, as a sidecar — not a turn.

        Restored from the pre-purga `insult/cogs/chat/batch.py`, which echoed
        every transcription and died with `personas/` in 2f8d9ad. A Discord
        voice message is opaque unless you hit play, so the echo is what makes
        it readable for whoever is not listening and for whoever reads the
        history later. Verbatim format, including the `>>>` block quote (the
        client draws a vertical bar, separating "what the user said" from the
        persona's reply that lands right after).

        Sent with a raw `channel.send`: no version tag, no chunking — it is a
        sidecar, so it truncates rather than spilling into a second message.
        """
        echo = f">>> 🔊 **{message.author.display_name} dijo:**\n{text}\n🎙️"
        if len(echo) > ECHO_LIMIT:
            echo = echo[: ECHO_LIMIT - 3] + "…"
        try:
            await message.channel.send(echo)
        except Exception:
            log.exception("host_voice_echo_failed", channel_id=str(message.channel.id))

    def _context_author(self, message: discord.Message) -> str:
        """The name this author gets in the routing brain's context block.

        For a persona it is the REGISTRY display name ("Frugívoro"), never
        `Member.display_name` — that returns the per-guild nickname ("frugi"), and
        `host_routing.md` maps only the canonical names. It is also exactly what
        `messages.user_name` holds in Postgres, so the context the brain reads in
        production is byte-identical to the one `scripts/router_eval.py` measures.
        """
        persona_id = self.dispatch_loop.mention_targets.get(str(message.author.id))
        if persona_id:
            persona = get_persona(persona_id)
            if persona and persona.display_name:
                return persona.display_name
        return getattr(message.author, "display_name", "") or "?"

    async def on_message(self, message: discord.Message) -> None:
        voice_text = "" if message.author.bot else await self.transcribe_voice(message)
        if voice_text:
            await self.echo_transcript(message, voice_text)
        if self.user is None or message.author.id != self.user.id:
            self.dispatch_loop.remember(
                channel_id=str(message.channel.id),
                author_name=self._context_author(message),
                text=f"{message.content or ''}\n{voice_text}".strip(),
            )
        self._ingest(message, time.time(), voice_text)

    @tasks.loop(seconds=TICK_SECONDS)
    async def _tick(self) -> None:
        try:
            await self.dispatch_loop.tick(time.time())
        except Exception:
            log.exception("host_tick_failed")


def build_host(router: object) -> HostClient:
    """Wire a HostClient with message-content intent (needed to read text).

    The susurro STT client comes from the same env pair the gateway uses
    (`SUSURRO_URL` / `SUSURRO_KEY`); absent either one it is None and the host
    routes voice notes by filename, exactly as before.
    """
    intents = discord.Intents.default()
    intents.message_content = True
    stt_client = build_susurro_stt_client(
        base_url=os.environ.get("SUSURRO_URL", ""),
        api_key=os.environ.get("SUSURRO_KEY", ""),
    )
    log.info("host_stt_configured", enabled=stt_client is not None)
    host = HostClient(
        HostDispatchLoop(
            router=router,
            mention_targets=persona_id_by_bot_user_id(),
            role_resolver=persona_id_by_role_name,
        ),
        intents=intents,
        stt_client=stt_client,
    )
    # The host owns the outcome of every turn it routes (2026-09-03): summon
    # with wait, retry once, speak for the house if the persona cannot.
    host.dispatch_loop.dispatcher = host.dispatch_with_fallback
    return host


def run_host(router: object, token: str | None = None) -> None:
    """Start the host bot. Refuses (logs + returns) without a token — the shell is
    dormant until the cutover atom is provided, so it never becomes a second
    omnipresent bot fighting Insult for reception."""
    token = token or os.environ.get(HOST_TOKEN_ENV, "")
    if not token:
        log.error("host_no_token", env=HOST_TOKEN_ENV)
        return
    build_host(router).run(token)
