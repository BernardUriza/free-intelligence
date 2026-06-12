"""ALICE metrics export to Azure Blob — minimal version of insult/core/metrics.py.

Uploads `alice-bot/metrics.json` to the same `insultstorage` account that
discord-bot uses, in a separate container so the dashboard can fetch both
bots and render them side-by-side.

Why minimal: ALICE's role is narrow (mention or /invite handler), so the
counter set is small. We track what matters for ops:

- uptime, gateway latency, guild count
- turns_total: messages we actually answered
- failover_received: how often Insult invoked us in FAILOVER mode
- invite_received: how often Insult invoked us in cooperative mode
- llm_requests / llm_errors against Azure OpenAI
- gateway_watchdog_ticks / restarts (when v3.9.34+ alice watchdog runs)
"""

from __future__ import annotations

import contextlib
import json
import os
import time
from collections import deque

import structlog

log = structlog.get_logger()

CONTAINER_NAME = "alice-bot"
METRICS_BLOB = "metrics.json"
LOGS_BLOB = "logs.json"
MAX_LOG_ENTRIES = 200

_log_buffer: deque[dict] = deque(maxlen=MAX_LOG_ENTRIES)
_counters: dict[str, int] = {
    "turns_total": 0,
    "failover_received": 0,
    "invite_received": 0,
    "llm_requests": 0,
    "llm_errors": 0,
    "watchdog_restarts": 0,
}
_start_time: float = time.time()


def record_event(event: dict) -> None:
    """Record a structlog event to the ring buffer and update counters."""
    entry = {
        "ts": time.time(),
        "event": event.get("event", ""),
        **{k: v for k, v in event.items() if k != "event"},
    }
    _log_buffer.append(entry)

    evt = entry["event"]
    if evt == "alice_llm_response":
        _counters["llm_requests"] += 1
    elif evt in ("alice_llm_rate_limit_exhausted", "alice_llm_timeout_exhausted", "alice_llm_auth_failed"):
        _counters["llm_errors"] += 1
    elif evt == "alice_invite_accepted":
        # Distinguish failover (reason starts with FAILOVER:) from normal invites.
        reason = entry.get("reason_preview", "") or ""
        if reason.startswith("FAILOVER"):
            _counters["failover_received"] += 1
        else:
            _counters["invite_received"] += 1
    elif evt == "alice_chat_turn_complete":
        _counters["turns_total"] += 1
    elif evt in (
        "alice_gateway_watchdog_silent_too_long_restart",
        "alice_gateway_watchdog_heartbeat_dead_restart",
        "alice_gateway_watchdog_zombie_detected_restart",
    ):
        _counters["watchdog_restarts"] += 1


def build_metrics_snapshot(bot_latency_ms: int, guilds: int) -> dict:
    """Build the metrics snapshot the dashboard reads."""
    return {
        "bot": "alice",
        "timestamp": time.time(),
        "uptime_seconds": int(time.time() - _start_time),
        "gateway": {
            "latency_ms": bot_latency_ms,
            "guilds": guilds,
        },
        "counters": dict(_counters),
    }


def build_logs_snapshot() -> list[dict]:
    return list(_log_buffer)


async def upload_dashboard_data(bot_latency_ms: int, guilds: int) -> None:
    """Upload metrics + logs JSON to Azure Blob (container alice-bot)."""
    if not os.environ.get("AZURE_STORAGE_CONNECTION_STRING"):
        return

    try:
        from azure.storage.blob import ContentSettings
        from azure.storage.blob.aio import BlobServiceClient

        cs = ContentSettings(content_type="application/json", cache_control="no-cache, max-age=0")
        conn_str = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
        async with BlobServiceClient.from_connection_string(conn_str) as client:
            container = client.get_container_client(CONTAINER_NAME)

            # Auto-create the container if it doesn't exist yet (first deploy).
            with contextlib.suppress(Exception):
                await container.create_container()

            metrics_blob = container.get_blob_client(METRICS_BLOB)
            metrics = build_metrics_snapshot(bot_latency_ms, guilds)
            await metrics_blob.upload_blob(
                json.dumps(metrics, default=str),
                overwrite=True,
                content_settings=cs,
            )

            logs_blob = container.get_blob_client(LOGS_BLOB)
            await logs_blob.upload_blob(
                json.dumps(build_logs_snapshot(), default=str),
                overwrite=True,
                content_settings=cs,
            )
    except Exception:
        log.exception("alice_dashboard_upload_failed")
