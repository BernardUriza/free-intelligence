"""Discord lifecycle for ALICE.

Mirrors the shape of `insult/bot.py` so the two bots can be reasoned
about together. ALICE runs as a SEPARATE Discord application
(`ALICE_DISCORD_TOKEN`) on her own connection — she's not a cog of
Insult, she's a peer bot in the same servers.

`run()` is the CLI entrypoint. Boot order:
1. Load settings + container.
2. Open Postgres pool (shared with Insult).
3. Register the chat cog.
4. Start the FastAPI `/invite` server in a background task.
5. Connect to Discord.
"""

from __future__ import annotations

import asyncio
import os
import signal
import time as _time
from collections import deque
from contextlib import suppress

import structlog
from discord.ext import tasks

from alice.app import Container, create_container

log = structlog.get_logger()


async def _start_invite_server(container: Container) -> None:
    """Boot the FastAPI invite server in the same event loop.

    Lives in a background task so Discord's connection isn't blocked.
    Uses uvicorn programmatically (not the CLI) so it shares our loop.
    """
    # Imported here so unit tests can build a Container without uvicorn.
    import uvicorn

    from alice.api.server import build_app

    app = build_app(container)
    config = uvicorn.Config(
        app,
        host=container.settings.invite_host,
        port=container.settings.invite_port,
        log_level="info",
        access_log=False,  # we have our own structlog
    )
    server = uvicorn.Server(config)
    await server.serve()


def _bind_signals(loop: asyncio.AbstractEventLoop, container: Container) -> None:
    """Graceful shutdown on SIGTERM / SIGINT."""

    async def _shutdown(signame: str) -> None:
        log.info("alice_shutdown_signal", signal=signame)
        with suppress(Exception):
            await container.bot.close()
        with suppress(Exception):
            await container.memory.close()
        log.info("alice_shutdown_complete")

    for signame in ("SIGINT", "SIGTERM"):
        loop.add_signal_handler(
            getattr(signal, signame),
            lambda s=signame: asyncio.create_task(_shutdown(s)),
        )


async def _main() -> None:
    container = create_container()

    # 1) Postgres
    await container.memory.connect()

    # 2) Cog (lazy import to avoid pulling discord.py at module-load time
    # when tests only need to construct the Container).
    from alice.cogs.chat import AliceChatCog

    chat_cog = AliceChatCog(
        bot=container.bot,
        memory=container.memory,
        llm=container.llm,
        persona=container.persona,
    )
    await container.bot.add_cog(chat_cog)

    # Wire the cog into the FastAPI app so /invite can reach it.
    # We attach via the container so build_app() reads it.
    container.bot._alice_chat_cog = chat_cog  # type: ignore[attr-defined]

    # 3) Signals
    loop = asyncio.get_running_loop()
    _bind_signals(loop, container)

    # 4) REST server in background
    invite_task = asyncio.create_task(_start_invite_server(container))

    # 5) Discord (blocking until disconnect). Register a one-shot on_ready
    # listener so we get a clear "connected to gateway" line in prod logs
    # — discord.py's own login info is at DEBUG level and gets filtered
    # out, leaving us blind to whether the bot actually attached.

    # Gateway zombie watchdog. Same pattern as insult/bot.py — same bug
    # observed on alice-bot 2026-05-17: gateway heartbeats fine but
    # MESSAGE_CREATE stops arriving after long uptime. Track raw socket
    # events; if MESSAGE_CREATE silence >2h while a recent on_resumed
    # happened, hard-exit so Container Apps recreates with fresh session.
    _last_socket_event_ts = _time.monotonic()
    _last_msg_create_ts = _time.monotonic()
    _resumed_ts_ring: deque[float] = deque(maxlen=20)

    @container.bot.event
    async def on_ready() -> None:
        log.info(
            "alice_gateway_ready",
            bot_id=str(container.bot.user.id) if container.bot.user else None,
            bot_name=str(container.bot.user) if container.bot.user else None,
            guilds=len(container.bot.guilds),
            cogs=list(container.bot.cogs.keys()),
        )
        _gateway_watchdog.start()

    @container.bot.event
    async def on_resumed() -> None:
        log.info("alice_bot_resumed")
        _resumed_ts_ring.append(_time.monotonic())

    @container.bot.event
    async def on_socket_event_type(event_type: str) -> None:
        nonlocal _last_socket_event_ts, _last_msg_create_ts
        _last_socket_event_ts = _time.monotonic()
        if event_type == "MESSAGE_CREATE":
            _last_msg_create_ts = _time.monotonic()

    @tasks.loop(minutes=5)
    async def _gateway_watchdog() -> None:
        now = _time.monotonic()
        while _resumed_ts_ring and now - _resumed_ts_ring[0] > 3600:
            _resumed_ts_ring.popleft()

        socket_age = now - _last_socket_event_ts
        msg_create_age = now - _last_msg_create_ts
        resumes_last_hour = len(_resumed_ts_ring)

        log.info(
            "alice_gateway_watchdog_tick",
            socket_age_s=int(socket_age),
            msg_create_age_s=int(msg_create_age),
            resumes_last_hour=resumes_last_hour,
        )

        if socket_age > 180:
            log.critical(
                "alice_gateway_watchdog_silent_too_long_restart",
                socket_age_s=int(socket_age),
            )
            await asyncio.sleep(0.5)
            os._exit(1)

        if msg_create_age > 7200 and resumes_last_hour > 0:
            log.critical(
                "alice_gateway_watchdog_zombie_detected_restart",
                socket_age_s=int(socket_age),
                msg_create_age_s=int(msg_create_age),
                resumes_last_hour=resumes_last_hour,
            )
            await asyncio.sleep(0.5)
            os._exit(1)

    try:
        await container.bot.start(container.settings.alice_discord_token)
    finally:
        if _gateway_watchdog.is_running():
            _gateway_watchdog.cancel()
        invite_task.cancel()
        with suppress(asyncio.CancelledError):
            await invite_task
        await container.memory.close()


def run() -> None:
    """CLI entrypoint: `python -m alice run`."""
    asyncio.run(_main())
