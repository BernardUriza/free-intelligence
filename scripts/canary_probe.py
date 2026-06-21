"""Canary probe runner — the Azure Container Apps Job that proves Insult is live.

Brutally simple liveness contract, end to end:

    CANARY insult <uuid>  posted in #canary by the reused poster bot (Vultur)
      → Insult echoes  CANARY_OK <uuid>  in the same channel
      → this runner observes that reply FROM the Insult bot's user id
      → exit 0

Any step that fails (no reply, wrong author, wrong nonce, timeout) → exit non-zero
+ a structured log + an optional ops webhook. This is what /debug/health could not
prove: health returned is_ready:true while the bot was a zombie answering no one.

REST-ONLY by design (no Discord Gateway, no IDENTIFY, no second session): the
poster token is REUSED from an existing bot (Vultur), whose live gateway runs in
its own Container App. Opening a SECOND gateway session with that token every 5
minutes would risk flapping the very bot we borrow. So this runner only touches
the Discord REST API — POST one message, poll for the reply — which never
competes with the poster's live gateway session. (REST GET also returns message
content WITHOUT the privileged Message Content Intent, unlike gateway events.)

Env (all IDs are Discord snowflakes, never names):
  CANARY_BOT_TOKEN       token of the reused POSTER bot (Vultur) — REST only
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

import aiohttp
import structlog

from personas.insult.cogs.chat.canary import parse_canary_ok

log = structlog.get_logger()

DISCORD_API = "https://discord.com/api/v10"
_POLL_INTERVAL_SECONDS = 2.0

EXIT_OK = 0
EXIT_TIMEOUT = 2
EXIT_CONFIG = 3
EXIT_SEND_FAILED = 4
EXIT_POLL_FAILED = 5
EXIT_CRASH = 6

_FAILURE_LABELS = {
    EXIT_TIMEOUT: "timeout — Insult no respondió CANARY_OK a tiempo",
    EXIT_CONFIG: "config/secrets faltantes (token/channel/insult-id)",
    EXIT_SEND_FAILED: "Discord send falló (POST del probe rechazado)",
    EXIT_POLL_FAILED: "Discord poll falló (GET de mensajes rechazado)",
    EXIT_CRASH: "crash inesperado del probe",
}


def failure_label(code: int) -> str:
    """Human-readable name of the failure mode behind a non-OK exit code.

    The ops alert names WHICH mode failed (timeout vs send vs poll vs config vs
    crash), not just the bare exit number — so a Discord notification is
    actionable without reading Log Analytics.
    """
    return _FAILURE_LABELS.get(code, f"fallo desconocido (exit {code})")


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
    """Best-effort failure alert to a private ops channel; never raises.

    Raw REST POST to the webhook (a webhook is just a URL that accepts a JSON
    body) — no Gateway, consistent with the rest of this runner.
    """
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(webhook_url, json={"content": text})
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
    """POST the probe via REST, poll for the Insult echo via REST. No Gateway.

    Returns the process exit code. Does NOT send the ops alert (the caller owns
    that so the alert text can name the failure mode).
    """
    nonce = uuid.uuid4().hex[:12]
    headers = {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json",
        "User-Agent": "InsultCanary (https://discord.com, 1.0)",
    }
    async with aiohttp.ClientSession(headers=headers) as session:
        # 1. POST the probe message.
        async with session.post(
            f"{DISCORD_API}/channels/{channel_id}/messages",
            json={"content": f"CANARY insult {nonce}"},
        ) as resp:
            if resp.status not in (200, 201):
                body = (await resp.text())[:200]
                log.error("canary_probe_post_failed", status=resp.status, body=body, channel_id=channel_id)
                return EXIT_SEND_FAILED
            after_id = (await resp.json())["id"]
        log.info("canary_probe_sent", nonce=nonce, channel_id=channel_id, after_id=after_id)

        # 2. Poll for Insult's CANARY_OK reply (messages AFTER our probe).
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout_seconds
        while loop.time() < deadline:
            async with session.get(
                f"{DISCORD_API}/channels/{channel_id}/messages",
                params={"after": after_id, "limit": "50"},
            ) as r:
                if r.status == 429:
                    retry_after = float((await r.json()).get("retry_after", _POLL_INTERVAL_SECONDS))
                    log.warning("canary_probe_rate_limited", retry_after=retry_after)
                    await asyncio.sleep(retry_after)
                    continue
                if r.status != 200:
                    body = (await r.text())[:200]
                    log.error("canary_probe_poll_failed", status=r.status, body=body)
                    return EXIT_POLL_FAILED
                for msg in await r.json():
                    if reply_matches(
                        author_id=int(msg["author"]["id"]),
                        channel_id=int(msg["channel_id"]),
                        content=msg.get("content", ""),
                        expected_nonce=nonce,
                        insult_bot_user_id=insult_bot_user_id,
                        canary_channel_id=channel_id,
                    ):
                        log.info("canary_probe_ok", nonce=nonce)
                        # Self-clean: delete our own probe message now that the
                        # match is confirmed (no race — verification already
                        # happened). Best-effort; the OK exit must not depend on
                        # cleanup. Insult deletes its own echo on its side.
                        with contextlib.suppress(Exception):
                            async with session.delete(f"{DISCORD_API}/channels/{channel_id}/messages/{after_id}"):
                                pass
                        return EXIT_OK
            await asyncio.sleep(_POLL_INTERVAL_SECONDS)

        log.error("canary_probe_timeout", nonce=nonce, timeout_seconds=timeout_seconds)
        return EXIT_TIMEOUT


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
        code = EXIT_CRASH

    if code != EXIT_OK and webhook_url:
        asyncio.run(_send_ops_alert(webhook_url, f"🚨 Insult canary FAILED — {failure_label(code)} (exit {code})"))
    return code


if __name__ == "__main__":
    sys.exit(main())
