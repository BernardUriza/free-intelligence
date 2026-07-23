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

import os
import time

import discord
import structlog
from discord.ext import tasks

from demux_ai.host_loop import HostDispatchLoop
from khimeras_shared.stt import (
    DEFAULT_AUDIO_CONTENT_TYPE,
    SusurroSttClient,
    build_susurro_stt_client,
    is_audio_attachment,
    transcribe_voice_message,
)
from shared.personas.registry import persona_id_by_bot_user_id, persona_id_by_role_name

log = structlog.get_logger()

HOST_TOKEN_ENV = "HOST_DISCORD_TOKEN"  # noqa: S105 # nosec B105 — env-var NAME, not a secret
TICK_SECONDS = 1.0


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
        parts: list[str] = []
        for attachment in message.attachments:
            if not is_audio_attachment(
                content_type=getattr(attachment, "content_type", None),
                filename=getattr(attachment, "filename", None),
                voice_message=bool(getattr(message.flags, "voice", False)),
            ):
                continue
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

    async def on_ready(self) -> None:
        log.info("host_ready", bot_id=self.user.id if self.user else None)
        if not self._tick.is_running():
            self._tick.start()

    async def on_message(self, message: discord.Message) -> None:
        voice_text = "" if message.author.bot else await self.transcribe_voice(message)
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
    return HostClient(
        HostDispatchLoop(
            router=router,
            mention_targets=persona_id_by_bot_user_id(),
            role_resolver=persona_id_by_role_name,
        ),
        intents=intents,
        stt_client=stt_client,
    )


def run_host(router: object, token: str | None = None) -> None:
    """Start the host bot. Refuses (logs + returns) without a token — the shell is
    dormant until the cutover atom is provided, so it never becomes a second
    omnipresent bot fighting Insult for reception."""
    token = token or os.environ.get(HOST_TOKEN_ENV, "")
    if not token:
        log.error("host_no_token", env=HOST_TOKEN_ENV)
        return
    build_host(router).run(token)
