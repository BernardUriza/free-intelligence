"""Canary probe runner — the Azure Container Apps Job that proves Insult is live.

Brutally simple liveness contract, end to end:

    CANARY insult <uuid>  posted by the canary bot in #canary
      → Insult echoes  CANARY_OK <uuid>  in the same channel
      → this runner observes that reply FROM the Insult bot's user id
      → exit 0

Any step that fails (no reply, wrong author, wrong nonce, timeout) → exit non-zero
+ a structured log + an optional ops webhook. This is what /debug/health could not
prove: health returned is_ready:true while the bot was a zombie answering no one.

Env (all IDs are Discord snowflakes, never names):
  CANARY_BOT_TOKEN       token of the DEDICATED canary bot (its own user)
  CANARY_CHANNEL_ID      the #canary channel id
  INSULT_BOT_USER_ID     the Insult bot user id whose reply we require
  CANARY_TIMEOUT_SECONDS optional, default 45
  CANARY_OPS_WEBHOOK_URL optional Discord webhook for failure alerts

Run as a one-shot:  python -m scripts.canary_probe   (exits 0 / non-zero)
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import sys
import uuid

import discord
import structlog

from personas.insult.cogs.chat.canary import parse_canary_ok

log = structlog.get_logger()

EXIT_OK = 0
EXIT_TIMEOUT = 2
EXIT_CONFIG = 3
EXIT_ERROR = 4


def reply_matches(
    *,
    author_id: int,
    channel_id: int,
    content: str,
    expected_nonce: str,
    insult_bot_user_id: str,
    canary_channel_id: str,
) -> bool:
    """True iff this message is the Insult bot's CANARY_OK for our exact nonce.

    Author verified by ID (not content), channel matched by ID, nonce matched
    against the one we posted. All three required.
    """
    if str(author_id) != str(insult_bot_user_id):
        return False
    if str(channel_id) != str(canary_channel_id):
        return False
    return parse_canary_ok(content) == expected_nonce


async def _send_ops_alert(webhook_url: str, text: str) -> None:
    """Best-effort failure alert to a private ops channel; never raises."""
    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(webhook_url, session=session)
            await webhook.send(content=text)
    except Exception:
        # alerting must not mask the real exit code
        log.warning("canary_ops_alert_failed")


async def run_probe(
    *,
    token: str,
    channel_id: str,
    insult_bot_user_id: str,
    timeout_seconds: float,
) -> int:
    """Connect as the canary bot, post the probe, await the Insult echo.

    Returns the process exit code. Does NOT send the ops alert (the caller owns
    that so the alert text can name the failure mode).
    """
    nonce = uuid.uuid4().hex[:12]
    got_ok = asyncio.Event()
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready() -> None:
        channel = client.get_channel(int(channel_id)) or await client.fetch_channel(int(channel_id))
        if not isinstance(channel, discord.abc.Messageable):
            log.error("canary_probe_bad_channel", channel_id=channel_id, kind=type(channel).__name__)
            await client.close()
            return
        await channel.send(f"CANARY insult {nonce}")
        log.info("canary_probe_sent", nonce=nonce, channel_id=channel_id)

    @client.event
    async def on_message(message: discord.Message) -> None:
        if reply_matches(
            author_id=message.author.id,
            channel_id=message.channel.id,
            content=message.content,
            expected_nonce=nonce,
            insult_bot_user_id=insult_bot_user_id,
            canary_channel_id=channel_id,
        ):
            log.info("canary_probe_ok", nonce=nonce)
            got_ok.set()

    async def _runner() -> None:
        with contextlib.suppress(asyncio.CancelledError):
            await client.start(token)

    task = asyncio.create_task(_runner())
    try:
        await asyncio.wait_for(got_ok.wait(), timeout=timeout_seconds)
        return EXIT_OK
    except TimeoutError:
        log.error("canary_probe_timeout", nonce=nonce, timeout_seconds=timeout_seconds)
        return EXIT_TIMEOUT
    finally:
        await client.close()
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


def main() -> int:
    token = os.environ.get("CANARY_BOT_TOKEN", "").strip()
    channel_id = os.environ.get("CANARY_CHANNEL_ID", "").strip()
    insult_bot_user_id = os.environ.get("INSULT_BOT_USER_ID", "").strip()
    timeout_seconds = float(os.environ.get("CANARY_TIMEOUT_SECONDS", "45"))
    webhook_url = os.environ.get("CANARY_OPS_WEBHOOK_URL", "").strip()

    if not (token and channel_id and insult_bot_user_id):
        log.error(
            "canary_probe_misconfigured",
            has_token=bool(token),
            has_channel=bool(channel_id),
            has_insult_id=bool(insult_bot_user_id),
        )
        return EXIT_CONFIG

    try:
        code = asyncio.run(
            run_probe(
                token=token,
                channel_id=channel_id,
                insult_bot_user_id=insult_bot_user_id,
                timeout_seconds=timeout_seconds,
            )
        )
    except Exception:
        # any unexpected failure is a non-zero exit
        log.exception("canary_probe_crashed")
        code = EXIT_ERROR

    if code != EXIT_OK and webhook_url:
        asyncio.run(_send_ops_alert(webhook_url, f"🚨 Insult canary FAILED (exit {code})"))
    return code


if __name__ == "__main__":
    sys.exit(main())
