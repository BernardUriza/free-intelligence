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
import signal
from contextlib import suppress

import structlog

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
    @container.bot.event
    async def on_ready() -> None:
        log.info(
            "alice_gateway_ready",
            bot_id=str(container.bot.user.id) if container.bot.user else None,
            bot_name=str(container.bot.user) if container.bot.user else None,
            guilds=len(container.bot.guilds),
            cogs=list(container.bot.cogs.keys()),
        )

    try:
        await container.bot.start(container.settings.alice_discord_token)
    finally:
        invite_task.cancel()
        with suppress(asyncio.CancelledError):
            await invite_task
        await container.memory.close()


def run() -> None:
    """CLI entrypoint: `python -m alice run`."""
    asyncio.run(_main())
