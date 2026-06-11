"""ChatCog — Discord listener + !chat command.

Thin orchestration layer: the listener delegates to `BatchManager` for
dedup/cooldown/batching, and `_respond` binds structlog contextvars +
emits the terminal `chat_turn_end` log around `turn.run_turn`. All turn
pipeline work lives in sibling modules under `insult.cogs.chat.*`.

State ownership:
  - `BatchManager` owns batch buffers, dedup set, and cooldown timestamps
  - `_background_tasks` set is handed to `spawn_tracked_task` so every
    fire-and-forget task gets automatic cleanup + terminal log
  - `_expression_history` and `_opus_budget` are shared per-bot runtime
    singletons constructed at the composition root (`app.Container`); the
    cog holds the handles and forwards them in the per-turn `TurnRuntimeDeps`
"""

from __future__ import annotations

import asyncio
import secrets
import time
from typing import TYPE_CHECKING

import discord
import structlog
from discord.ext import commands

from insult.cogs.chat.batch import BatchManager
from insult.cogs.chat.pipeline import TurnRuntimeDeps
from insult.cogs.chat.tasks import spawn_tracked_task
from insult.cogs.chat.tools import ALL_TOOLS
from insult.cogs.chat.turn import run_turn
from insult.cogs.chat.voice import transcribe_voice
from insult.composition import (
    build_preset_engine_port,
    build_s1b_policy_port,
    default_arc_port,
    default_facts_port,
    default_retrieval_port,
    default_stance_port,
)

if TYPE_CHECKING:
    from insult.app import Container

log = structlog.get_logger()


class ChatCog(commands.Cog):
    def __init__(self, container: Container):
        self.memory = container.memory
        self.agent_client = container.agent_client
        self.judge_client = container.judge_client
        self.settings = container.settings
        self.bot = container.bot
        self.siesta = container.siesta
        self._background_tasks: set[asyncio.Task] = set()
        # Shared runtime singletons now born at the composition root
        # (app.Container); the cog just holds the handles it forwards.
        self._expression_history = container.expression_history
        self._batches = BatchManager()
        self._opus_budget = container.opus_budget
        # Preset Engine adapter: built once with its runtime deps (judge
        # client + settings) — unlike the stateless default_* ports below.
        self._preset_engine = build_preset_engine_port(self.judge_client, self.settings)
        # S1b Policy adapter: built once with the anti-repetition ledger
        # (host-owned state; the capability only consults it).
        self._s1b_policy = build_s1b_policy_port(self._expression_history)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Respond to every message — no !chat prefix needed.

        The BatchManager accumulates rapid-fire messages from the same
        user and fires `flush_callback` (our `_respond`) with the combined
        text after BATCH_WAIT_SECONDS of silence, like a human waiting for
        someone to finish typing.
        """
        await self._batches.handle_incoming(
            message,
            settings=self.settings,
            memory=self.memory,
            bot=self.bot,
            flush_callback=self._respond,
            transcribe_voice=transcribe_voice,
        )

    @commands.command(name="chat")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def chat(self, ctx: commands.Context, *, message: str) -> None:
        """Fallback: !chat still works for explicit invocation."""
        await self._respond(ctx.message, message)

    def _spawn_task(self, coro, *, name: str | None = None) -> None:
        """Create a tracked background task (auto-cleanup + terminal log)."""
        spawn_tracked_task(coro, self._background_tasks, name=name)

    async def _respond(self, message: discord.Message, text: str) -> None:
        """Bind request_id/channel_id/user_id to structlog contextvars and
        run one turn, emitting a terminal `chat_turn_end` with outcome.

        Every log in this task inherits the bound vars — including llm.py,
        delivery.py, and any background tasks spawned inside `run_turn`.
        `grep request_id=<id>` then reconstructs the whole turn.
        """
        request_id = secrets.token_hex(4)
        channel_id = str(message.channel.id)
        user_id = str(message.author.id)
        turn_start = time.monotonic()

        self._batches.record_response(message.author.id)

        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            channel_id=channel_id,
            user_id=user_id,
        )
        outcome = "unknown"
        try:
            if self.siesta.is_active():
                outcome = await self._handle_siesta_turn(message, text)
                return
            outcome = await run_turn(
                message,
                text,
                turn_start=turn_start,
                deps=TurnRuntimeDeps(
                    memory=self.memory,
                    settings=self.settings,
                    bot=self.bot,
                    expression_history=self._expression_history,
                    opus_budget=self._opus_budget,
                    spawn_task=self._spawn_task,
                    all_tools=ALL_TOOLS,
                    facts=default_facts_port(),
                    stance=default_stance_port(),
                    arc=default_arc_port(),
                    retrieval=default_retrieval_port(),
                    preset_engine=self._preset_engine,
                    policy=self._s1b_policy,
                    agent_client=self.agent_client,
                    judge_client=self.judge_client,
                ),
            )
        except BaseException as e:
            outcome = f"unhandled:{type(e).__name__}"
            log.exception("chat_turn_unhandled_exception", error_type=type(e).__name__)
            raise
        finally:
            log.info(
                "chat_turn_end",
                outcome=outcome,
                total_ms=int((time.monotonic() - turn_start) * 1000),
            )
            # Mark the turn boundary for /debug/health and the synthetic
            # KQL alert. Recorded under all outcomes (ok, llm_failed,
            # trivial_skipped, etc.) — what matters for liveness is that
            # on_message reached the end of the pipeline at all.
            from insult.core.health_state import get_state as _get_health_state

            _get_health_state().record_turn_end(outcome)
            structlog.contextvars.unbind_contextvars("request_id", "channel_id", "user_id")

    async def _handle_siesta_turn(self, message: discord.Message, text: str) -> str:
        """Persist the user's message + react 🛌 + skip the LLM.

        Called when ``siesta.is_active()`` — i.e. the consolidator job is
        currently writing to the shared blob. Responding here would race
        the consolidator's upload AND burn tokens against state that's
        about to be replaced. We acknowledge with a reaction so the user
        knows the message was seen, and let the upload-side fix in
        :mod:`insult.core.backup` keep the data path safe.
        """
        snapshot = self.siesta.get()
        try:
            await self.memory.store(
                str(message.channel.id),
                str(message.author.id),
                message.author.display_name,
                "user",
                text,
            )
        except Exception:
            log.exception("siesta_skipped_store_failed")
        try:
            await message.add_reaction("🛌")
        except Exception:
            log.debug("siesta_skipped_reaction_failed")
        log.info(
            "siesta_skipped_turn",
            phase=snapshot.phase.value,
            progress_pct=snapshot.progress_pct,
            current_user=snapshot.current_user_id,
        )
        return f"siesta:{snapshot.phase.value}"
