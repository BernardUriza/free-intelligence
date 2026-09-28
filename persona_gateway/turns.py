"""Turn delivery — the shared tail every turn kind runs through.

Runner call → `[REACT:]` reactions → durable markers → chunked send → persist →
auto-TTS. One `TurnRunner` per persona-bot, injected into `PersonaClient` like
its sibling services; the client's `_run_and_deliver` is a thin delegate kept
for the tests that drive it directly.
"""

from __future__ import annotations

import asyncio
import contextlib
import uuid

import discord
import structlog

from persona_core.gifs import resolve_gifs, strip_gif_markers
from persona_core.memory import MemoryStore
from persona_core.reactions import add_reactions, parse_reactions, strip_reactions
from persona_core.runner.agent_client import AgentRunnerClient
from persona_core.tickets import LedgerRow
from persona_core.turn.markers import MarkerRouter
from persona_gateway.delivery import send_chunked
from persona_gateway.voice import VoiceService
from shared.personas import Persona
from shared.text import split_response

log = structlog.get_logger()

TYPING_REFRESH_SECONDS = 9.0


class TurnRunner:
    """Owns the runner round-trip and everything that happens to its reply."""

    def __init__(
        self,
        persona: Persona,
        memory: MemoryStore,
        agent_client: AgentRunnerClient,
        markers: MarkerRouter,
        voice: VoiceService,
        bg_tasks: set[asyncio.Task],
        *,
        auto_tts_min_chars: int = 0,
    ) -> None:
        self.persona = persona
        self.memory = memory
        self.agent_client = agent_client
        self._markers = markers
        self._voice = voice
        self._bg_tasks = bg_tasks
        self.auto_tts_min_chars = auto_tts_min_chars

    async def run_and_deliver(
        self,
        *,
        channel: discord.abc.Messageable,
        channel_id: str,
        user_id: str,
        guild_id: str | None,
        channel_name: str | None,
        messages: list[dict],
        bot_user_id: str,
        turn_kind: str = "mention",
        react_to: discord.Message | None = None,
        behavioral_guidance: str | None = None,
        other_people: str | None = None,
        relevant_memory: str | None = None,
        turn_id: str | None = None,
        resume_from: LedgerRow | None = None,
    ) -> bool:
        """Shared tail for mention + invite: runner call → react → markers → send.

        Returns True only if the user SAW something — text, a GIF or a reaction.
        The caller stamps `last_turn_delivered` off this, so a turn that dies
        with empty text can no longer pass for "answered recently" in /health
        (issue #40: a turn died in silence and /health called it delivered).

        Typing keepalive is a fire-and-forget background task so the user sees
        "[persona] is typing…" during the long runner call. Deliberately NOT
        `async with channel.typing()` (blocks on __aenter__, vulnerable to 429
        killing the turn before the runner runs — anti-pattern #1): a short task
        that re-triggers typing every ~9s until the stop_event is set.

        Con `turn_id` cada etapa queda en la fila del boleto (`invite_turns`):
        `runner_done` (la respuesta), `markers_done` (el texto tras los
        marcadores), `sending`, `delivered` (los ids de Discord). Con
        `resume_from` la réplica que reanuda ENTRA en la etapa registrada, nunca
        antes: un turno que ya pasó por el runner no lo vuelve a llamar, uno que
        ya enrutó marcadores no los repite. La etapa `sending` no se reanuda aquí
        (`dispatch_invite` la declara `uncertain`): nadie sabe si el primer chunk
        aterrizó, y reenviar es la única forma de dar dos respuestas.
        """
        # The runner's `job_id` is born HERE, not inside the client, so the
        # gateway's own turn lines carry the same id the runner logs — the only
        # way to cross one turn between the two processes in KQL. On the
        # invite path it is the host's `turn_id` (the ledger key); a mention
        # turn has no ledger and gets a fresh one. (Rescued from PR #97.)
        job_id = turn_id or uuid.uuid4().hex
        stage = (resume_from.extra.get("stage") if resume_from is not None else None) or "accepted"
        tail: dict = (resume_from.extra.get("tail") if resume_from is not None else None) or {}
        if stage in ("runner_done", "markers_done"):
            text = (resume_from.extra.get("stage_text") or "").strip()  # type: ignore[union-attr]
            model_used = tail.get("model_used")
            log.warning(
                "persona_gateway_turn_resumed",
                persona_id=self.persona.persona_id,
                channel_id=channel_id,
                turn_id=turn_id,
                stage=stage,
                attempt=resume_from.attempts if resume_from is not None else None,
            )
        else:
            _typing_stop = asyncio.Event()

            async def _typing_keepalive() -> None:
                while not _typing_stop.is_set():
                    with contextlib.suppress(discord.HTTPException):
                        async with channel.typing():
                            with contextlib.suppress(TimeoutError):
                                await asyncio.wait_for(_typing_stop.wait(), timeout=TYPING_REFRESH_SECONDS)
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
                    other_people=other_people,
                    relevant_memory=relevant_memory,
                    job_id=job_id,
                )
            finally:
                _typing_stop.set()
                _typing_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await _typing_task

            text = (resp.text or "").strip()
            model_used = getattr(resp, "model_used", None)
            await self._advance(turn_id, "runner_done", text=text, tail={"model_used": model_used, "user_id": user_id})

        raw_had_text = bool(text)
        reacted = False

        if stage != "markers_done":
            # Reactions FIRST (they need the live `react_to` message and the
            # module-level `add_reactions` the tests monkeypatch).
            reactions = parse_reactions(text)
            if reactions:
                text = strip_reactions(text)
                if react_to is not None:
                    task = asyncio.create_task(add_reactions(react_to, reactions))
                    self._bg_tasks.add(task)
                    task.add_done_callback(self._bg_tasks.discard)
                    reacted = True
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
            text = await self._markers.route(
                text, channel_id=channel_id, guild_id=guild_id, user_id=user_id, bot_user_id=bot_user_id
            )
            await self._advance(turn_id, "markers_done", text=text)
        # `[GIF: tag]` resolves against the persona's OWN catalog. Parsed BEFORE
        # the empty-text return so a reply that is only a GIF still posts it.
        gif_urls = resolve_gifs(self.persona.persona_id, text)
        text = strip_gif_markers(text)
        if not text and not gif_urls:
            # The turn ends with nothing to send. Name the reason instead of
            # returning in silence — an orphan turn has to be findable in KQL,
            # not deduced from a missing `persona_gateway_turn_complete`.
            reason = "reactions_only" if reacted else ("markers_only" if raw_had_text else "runner_empty")
            log.info(
                "persona_gateway_turn_empty",
                persona_id=self.persona.persona_id,
                channel_id=channel_id,
                job_id=job_id,
                turn_kind=turn_kind,
                reason=reason,
                delivered=reacted,
            )
            return reacted

        await self._advance(turn_id, "sending")
        sent: list[discord.Message] = []
        if text:
            sent = await send_chunked(channel, text)
        await self._send_gifs(channel, gif_urls, turn_kind=turn_kind)
        # La entrega queda en la fila ANTES del store: una réplica que reanude
        # después de esto lee `delivered` y no vuelve a enviar.
        await self._record_delivered(turn_id, sent)
        if not text:
            return True

        # What was actually said in Discord is the delimiter-free text — memory
        # and voice never see the `[SEND]` pacing marker.
        delivered = "\n".join(split_response(text))
        first_id = getattr(sent[0], "id", None) if sent else None
        # Everything past this line happens AFTER the user saw the reply. A fault
        # here is not a failed turn — reporting it as one makes the host retry a
        # turn that already landed (a second answer to the same ask) and, before
        # the host owned the fallback, made the persona mumble "…" right under
        # its own delivered text. Logged, never raised.
        try:
            await self.memory.store(
                channel_id,
                bot_user_id,
                self.persona.display_name,
                "assistant",
                delivered,
                for_user_id=user_id,
                guild_id=guild_id,
                channel_name=channel_name,
                model_used=model_used,
                # El id del primer chunk hace la fila idempotente: una reanudación
                # que ya no envía nada tampoco duplica el assistant en `messages`.
                discord_message_id=str(first_id) if isinstance(first_id, int) else None,
            )
        except Exception:
            log.exception(
                "persona_gateway_turn_store_failed",
                persona_id=self.persona.persona_id,
                channel_id=channel_id,
                turn_kind=turn_kind,
            )
        log.info(
            "persona_gateway_turn_complete",
            persona_id=self.persona.persona_id,
            channel_id=channel_id,
            job_id=job_id,
            chars=len(delivered),
            turn_kind=turn_kind,
        )

        # Auto-TTS: a long reply ships a voice clip of the FULL text so you can
        # listen instead of reading a wall (gated by auto_tts_min_chars; 0=off).
        if self._voice.should_auto_speak(delivered, self.auto_tts_min_chars):
            try:
                await self._voice.speak(channel, delivered, reason="auto")
            except Exception:
                log.exception(
                    "persona_gateway_auto_tts_failed",
                    persona_id=self.persona.persona_id,
                    channel_id=channel_id,
                )

        return True

    async def _advance(
        self, turn_id: str | None, stage: str, *, text: str | None = None, tail: dict | None = None
    ) -> None:
        if turn_id is None:
            return
        try:
            await self.memory.advance_invite_turn(turn_id, stage, text=text, tail=tail)
        except Exception:
            log.warning("persona_gateway_turn_stage_failed", turn_id=turn_id, stage=stage, exc_info=True)

    async def _record_delivered(self, turn_id: str | None, sent: list[discord.Message]) -> None:
        if turn_id is None:
            return
        ids = [m.id for m in sent if isinstance(getattr(m, "id", None), int)]
        partial = bool(getattr(sent, "partial", False))
        try:
            await self.memory.mark_invite_turn_delivered(turn_id, ids, partial=partial)
            log.info("persona_gateway_turn_delivered_recorded", turn_id=turn_id, messages=len(ids), partial=partial)
        except Exception:
            log.warning("persona_gateway_turn_delivery_record_failed", turn_id=turn_id, exc_info=True)

    async def _send_gifs(self, channel, urls: list[str], *, turn_kind: str) -> None:
        """Post each GIF as its OWN bare message — no version tag, no chunking.

        A GIF is a sidecar, like the host's transcript echo: Discord only unfurls
        it cleanly when the URL stands alone, and the `-# ᵛ…` suffix
        `send_chunked` appends would hang text off the embed. Failure is silent
        by design — a GIF that will not post must never cost the reply that
        already landed.
        """
        for url in urls:
            try:
                await channel.send(url)
            except Exception:
                log.warning(
                    "persona_gateway_gif_send_failed",
                    persona_id=self.persona.persona_id,
                    turn_kind=turn_kind,
                    exc_info=True,
                )
                continue
            log.info(
                "persona_gateway_gif_sent",
                persona_id=self.persona.persona_id,
                turn_kind=turn_kind,
            )
