"""Turn delivery — the shared tail every turn kind runs through.

Runner call → `[REACT:]` reactions → durable markers → chunked send → persist →
auto-TTS. One `TurnRunner` per persona-bot, injected into `PersonaClient` like
its sibling services; the client's `_run_and_deliver` is a thin delegate kept
for the tests that drive it directly.
"""

from __future__ import annotations

import asyncio
import contextlib

import discord
import structlog

from khimeras_shared.memory import MemoryStore
from khimeras_shared.reactions import add_reactions, parse_reactions, strip_reactions
from khimeras_shared.runner.agent_client import AgentRunnerClient
from persona_gateway.delivery import send_chunked
from persona_gateway.markers import MarkerRouter
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

        # What was actually said in Discord is the delimiter-free text — memory
        # and voice never see the `[SEND]` pacing marker.
        delivered = "\n".join(split_response(text))
        await self.memory.store(
            channel_id,
            bot_user_id,
            self.persona.display_name,
            "assistant",
            delivered,
            for_user_id=user_id,
            guild_id=guild_id,
            channel_name=channel_name,
            model_used=getattr(resp, "model_used", None),
        )
        log.info(
            "persona_gateway_turn_complete",
            persona_id=self.persona.persona_id,
            channel_id=channel_id,
            chars=len(delivered),
            turn_kind=turn_kind,
        )

        # Auto-TTS: a long reply ships a voice clip of the FULL text so you can
        # listen instead of reading a wall (gated by auto_tts_min_chars; 0=off).
        if self._voice.should_auto_speak(delivered, self.auto_tts_min_chars):
            await self._voice.speak(channel, delivered, reason="auto")
