"""Discord bot wiring: build deps, register events, own task lifecycle.

This module is a thin orchestrator. All background-loop bodies live under
``insult.tasks.*`` (one module per domain); here we just create the loop
objects, wire the Discord events to them, and own start/cancel lifecycle.
"""

import asyncio
import os
import signal
import sys

import structlog
from discord.ext import commands

from personas.insult.app import Container, create_app
from personas.insult.cogs import ChatCog, UtilityCog
from personas.insult.cogs.voice import VoiceCog
from personas.insult.core.backup import is_azure_configured
from personas.insult.core.debug_server import start_debug_server, stop_debug_server
from personas.insult.core.errors import ErrorType, get_error_response
from personas.insult.core.siesta.presence.discord import SiestaPresenceUpdater
from personas.insult.tasks.health import build_health_check
from personas.insult.tasks.proactive import build_proactive_task
from personas.insult.tasks.reminders import build_reminder_tasks, handle_snooze_reaction
from personas.insult.tasks.state import ProactiveState
from personas.insult.tasks.summaries import build_summarize_channels_task
from personas.insult.tasks.watchdog import GatewayWatchdog

log = structlog.get_logger()


def _build(container: Container):
    """Register cogs + event handlers on the bot and wire background tasks."""
    bot = container.bot
    memory = container.memory
    _debug_runner = None  # type: ignore[var-annotated]

    # --- Background tasks (bodies in insult.tasks.*) ---
    proactive_state = ProactiveState()
    watchdog = GatewayWatchdog(bot)
    health_check = build_health_check(bot, memory)
    summarize_channels = build_summarize_channels_task(bot, container, memory)
    proactive = build_proactive_task(bot, container, memory, proactive_state)
    reminder_check, ack_overdue = build_reminder_tasks(bot, container, memory)

    # Start order is irrelevant (independent intervals); cancellation walks
    # the same list so shutdown can't miss a loop.
    background_loops = [
        health_check,
        watchdog.loop,
        reminder_check,
        ack_overdue,
        proactive,
        summarize_channels,
    ]

    # Expose the proactive backoff reset for ChatCog's batch manager.
    bot._reset_proactive_backoff = proactive_state.reset

    # --- Graceful Shutdown ---
    _shutdown_started = False

    async def graceful_shutdown(sig: signal.Signals):
        nonlocal _shutdown_started
        if _shutdown_started:
            return
        _shutdown_started = True
        log.info("shutdown_signal", signal=sig.name)
        for loop in background_loops:
            if loop.is_running():
                loop.cancel()
        await container.siesta.stop()
        if _debug_runner is not None:
            await stop_debug_server(_debug_runner)
        await memory.close()
        # No blob upload on shutdown — DB lives in managed Postgres since the
        # 2026-05-12 migration. Container shutdown is a no-op for data.
        await bot.close()
        log.info("shutdown_complete")

    def _bind_signals():
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(graceful_shutdown(s)))

    # --- Debug server: start before Discord connects so the startup probe
    # passes immediately regardless of Discord gateway latency.  setup_hook
    # is called by discord.py BEFORE the WebSocket IDENTIFY handshake, so
    # :8787 is open before the probe can fire its first check.
    #
    # Prior to this change the server started inside on_ready, which fires
    # only after Discord sends READY.  During congestion or rate-limiting,
    # READY could take 60-240 s; the probe (240 s threshold) killed the
    # replica, triggering a restart that burned another IDENTIFY token and
    # amplified the backlog — a self-reinforcing crash loop (ActivationFailed
    # pattern first seen on revs 0000101/0000102, 2026-06-11).
    #
    # Health semantics after this change:
    #   /debug/health before on_ready → 200, is_ready=null, pg.reachable=false
    #   /debug/health after  on_ready → 200, is_ready=true,  pg.reachable=true
    # The probe only needs the 200; monitoring/watchdog owns the is_ready check.
    async def _setup_hook() -> None:
        nonlocal _debug_runner
        debug_token = container.settings.debug_token.get_secret_value()
        if debug_token:
            try:
                _debug_runner = await start_debug_server(
                    memory=memory,
                    debug_token=debug_token,
                    host=container.settings.debug_host,
                    port=container.settings.debug_port,
                )
            except Exception:
                log.exception("debug_server_start_failed")
        else:
            log.info("debug_server_disabled", reason="DEBUG_TOKEN not set")

    bot.setup_hook = _setup_hook

    # --- Events ---
    _ready_fired = False

    @bot.event
    async def on_ready():
        nonlocal _ready_fired
        # Wire the health-state singleton with this bot reference so
        # /debug/health can answer is_ready / gateway_latency_ms. Called on
        # every on_ready (idempotent assign) so reconnects don't leave the
        # probe with a stale ref.
        from personas.insult.core.health_state import get_state as _get_health_state

        _get_health_state().set_bot(bot)

        # No DB download on startup. Postgres is external and persistent — the
        # new container's memory.connect() just opens a pool against the managed
        # PG server. Cero race condition on swap.
        #
        # Hard timeout + fail-fast: if connect() wedges (the 2026-06-13 boot
        # hang), DO NOT let on_ready stall forever — that produced a silent
        # zombie that /debug/health reported "ok". A half-booted replica must
        # die so the platform starts a fresh one (proven to boot clean), never
        # linger. (no gráficos chafos: down → clearly down.)
        boot_timeout = container.settings.boot_connect_timeout_s
        try:
            async with asyncio.timeout(boot_timeout):
                await memory.connect()
        except TimeoutError:
            log.error("boot_connect_timeout", timeout_s=boot_timeout)
            sys.stdout.flush()  # os._exit skips buffer flush — guarantee the diagnostic lands
            os._exit(1)
        except Exception as e:
            log.error("boot_connect_failed", error=str(e), error_type=type(e).__name__)
            sys.stdout.flush()  # os._exit skips buffer flush — guarantee the diagnostic lands
            os._exit(1)
        if not _ready_fired:
            _bind_signals()
            await bot.add_cog(ChatCog(container))
            await bot.add_cog(UtilityCog(container))
            await bot.add_cog(VoiceCog(container))
            for loop in background_loops:
                loop.start()
            if is_azure_configured():
                container.siesta.add_listener(SiestaPresenceUpdater(bot))
                container.siesta.start()
            _ready_fired = True
        log.info(
            "bot_ready",
            user=str(bot.user),
            guilds=len(bot.guilds),
            model=container.settings.llm_model,
            prefix=container.settings.command_prefix,
            memory_recent=container.settings.memory_recent_limit,
            memory_relevant=container.settings.memory_relevant_limit,
        )
        # End-to-end wiring complete (cogs/on_message attached, loops
        # started). Only now is /debug/health allowed to report serving=true
        # / healthy=true. If on_ready hangs above this line, the endpoint
        # stays serving=false even though is_ready/gateway_latency are green.
        _get_health_state().mark_serving()

    @bot.event
    async def on_socket_event_type(event_type: str):
        watchdog.on_socket_event(event_type)

    @bot.event
    async def on_raw_reaction_add(payload):
        """Snooze/ack handler — delegates to the reminders task module."""
        await handle_snooze_reaction(payload, bot, memory)

    @bot.event
    async def on_disconnect():
        log.warning("bot_disconnected")

    @bot.event
    async def on_resumed():
        log.info("bot_resumed")
        watchdog.note_resumed()

    @bot.event
    async def on_command_error(ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"Calmate, espera {error.retry_after:.0f}s. Cual es la urgencia?")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Y el resto del mensaje? Te falto `{error.param.name}`. Intenta otra vez, completo.")
        elif isinstance(error, commands.CommandNotFound):
            pass
        else:
            log.error("command_error", command=str(ctx.command), error=str(error), user=str(ctx.author))
            await ctx.send(get_error_response(ErrorType.GENERIC))

    return bot


def run():
    """Create app, build bot, and run."""
    container = create_app()
    bot = _build(container)
    bot.run(container.settings.discord_token.get_secret_value(), log_handler=None)
