"""Metrics collection and Azure Blob export for the dashboard.

Collects structlog events in a ring buffer and periodically uploads
a JSON snapshot to Azure Blob Storage for the Brython dashboard to fetch.
"""

import json
import os
import time
from collections import deque

import structlog

log = structlog.get_logger()

CONTAINER_NAME = "insult-bot"
METRICS_BLOB = "metrics.json"
LOGS_BLOB = "logs.json"
TRACES_BLOB = "traces.json"
MAX_LOG_ENTRIES = 200  # Keep last 200 log events
MAX_MESSAGE_TRACES = 30  # Keep last 30 message traces for carousel

# Global ring buffer for log events
_log_buffer: deque[dict] = deque(maxlen=MAX_LOG_ENTRIES)

# Message traces — one per bot response with all reasoning data
_message_traces: deque[dict] = deque(maxlen=MAX_MESSAGE_TRACES)

# Global counters (reset on restart)
_counters: dict[str, int] = {
    "messages_total": 0,
    "llm_requests": 0,
    "llm_errors": 0,
    "preset_default_abrasive": 0,
    "preset_playful_roast": 0,
    "preset_intellectual_pressure": 0,
    "preset_relational_probe": 0,
    "preset_respectful_serious": 0,
    "preset_meta_deflection": 0,
    "character_breaks": 0,
    "anti_patterns": 0,
    "whisper_transcriptions": 0,
    "reminders_created": 0,
    "facts_extracted": 0,
    "facts_failed": 0,
    # Ops signals (DASH-1c, v3.9.45). These rarely fire when healthy but
    # are the events Bernard most needs to see when things break. The
    # dashboard frontend can read these from the metrics blob without
    # any UI changes — they appear in the existing counter card.
    "gateway_zombie_restarts": 0,  # Signal B (msg_create starved + reconnect loop)
    "gateway_heartbeat_dead_restarts": 0,  # Signal A (bot.latency dead/NaN)
    "alice_failovers": 0,  # FAILOVER-1 invocations when runner died mid-turn
    "invoke_alice_calls": 0,  # Insult's persona-driven tool calls to ALICE
    "remember_facts_added": 0,  # [REMEMBER:] markers persisted as agent-source facts
    "agent_runner_image_turns": 0,  # turns where the runner received non-text attachments (v3.9.43)
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

    # Update counters based on event type
    evt = entry["event"]
    if evt == "llm_request":
        _counters["llm_requests"] += 1
    elif evt in ("llm_rate_error", "llm_timeout_error", "llm_auth_error", "llm_api_error"):
        _counters["llm_errors"] += 1
    elif evt == "preset_classified":
        # `preset` is the field name the ONE emitter uses (chat stage 08). A second
        # emitter in the prompt layer used to fire the same event with `mode=`,
        # double-counting messages_total while only single-counting the per-preset
        # keys — so every `preset_X / messages_total` ratio read HALF its real
        # value, and the "flag if 90%+ is DEFAULT_ABRASIVE" drift alarm could never
        # trip. One event, one emitter.
        _counters["messages_total"] += 1
        key = f"preset_{entry.get('preset', '')}"
        if key in _counters:
            _counters[key] += 1
    elif evt == "character_break_detected":
        _counters["character_breaks"] += 1
    elif evt == "anti_pattern_detected":
        _counters["anti_patterns"] += 1
    elif evt == "whisper_transcribed":
        _counters["whisper_transcriptions"] += 1
    elif evt == "reminder_created":
        _counters["reminders_created"] += 1
    elif evt == "facts_extracted":
        _counters["facts_extracted"] += 1
    elif evt == "facts_extraction_failed":
        _counters["facts_failed"] += 1
    # --- Ops signals (DASH-1c) ---
    elif evt == "gateway_watchdog_zombie_detected_restart":
        _counters["gateway_zombie_restarts"] += 1
    elif evt == "gateway_watchdog_heartbeat_dead_restart":
        _counters["gateway_heartbeat_dead_restarts"] += 1
    elif evt == "alice_failover_invoked":
        _counters["alice_failovers"] += 1
    elif evt == "invoke_alice_called":
        _counters["invoke_alice_calls"] += 1
    elif evt == "remember_fact_added":
        _counters["remember_facts_added"] += 1
    elif evt == "agent_runner_client_attachments_forwarded":
        _counters["agent_runner_image_turns"] += 1


def record_message_trace(trace: dict) -> None:
    """Record a complete message trace for the dashboard carousel."""
    trace["ts"] = time.time()
    _message_traces.append(trace)


def build_message_traces_snapshot() -> list[dict]:
    """Return message traces as a list (most recent last)."""
    return list(_message_traces)


def build_metrics_snapshot(bot_latency_ms: int, guilds: int, db_stats: dict) -> dict:
    """Build the full metrics snapshot for the dashboard."""
    return {
        "timestamp": time.time(),
        "uptime_seconds": int(time.time() - _start_time),
        "bot": {
            "latency_ms": bot_latency_ms,
            "guilds": guilds,
        },
        "db": db_stats,
        "counters": dict(_counters),
    }


def build_logs_snapshot() -> list[dict]:
    """Return the log buffer as a list (most recent last)."""
    return list(_log_buffer)


FACTS_BLOB = "facts.json"


async def upload_dashboard_data(
    bot_latency_ms: int, guilds: int, db_stats: dict, all_facts: list[dict] | None = None
) -> None:
    """Upload metrics + logs + traces + facts JSON blobs to Azure Blob Storage."""
    if not os.environ.get("AZURE_STORAGE_CONNECTION_STRING"):
        return

    try:
        from azure.storage.blob.aio import BlobServiceClient

        conn_str = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
        async with BlobServiceClient.from_connection_string(conn_str) as client:
            container = client.get_container_client(CONTAINER_NAME)

            # Upload metrics
            metrics = build_metrics_snapshot(bot_latency_ms, guilds, db_stats)
            metrics_blob = container.get_blob_client(METRICS_BLOB)
            await metrics_blob.upload_blob(
                json.dumps(metrics, default=str),
                overwrite=True,
                content_settings=_blob_content_settings(),
            )

            # Upload logs
            logs = build_logs_snapshot()
            logs_blob = container.get_blob_client(LOGS_BLOB)
            await logs_blob.upload_blob(
                json.dumps(logs, default=str),
                overwrite=True,
                content_settings=_blob_content_settings(),
            )

            # Upload message traces
            traces = build_message_traces_snapshot()
            traces_blob = container.get_blob_client(TRACES_BLOB)
            await traces_blob.upload_blob(
                json.dumps(traces, default=str),
                overwrite=True,
                content_settings=_blob_content_settings(),
            )

            # Upload facts (all users)
            if all_facts is not None:
                facts_blob = container.get_blob_client(FACTS_BLOB)
                await facts_blob.upload_blob(
                    json.dumps(all_facts, default=str),
                    overwrite=True,
                    content_settings=_blob_content_settings(),
                )

    except Exception:
        log.exception("dashboard_upload_failed")


def _blob_content_settings():
    """Return ContentSettings for JSON blobs with CORS-friendly headers."""
    from azure.storage.blob import ContentSettings

    return ContentSettings(content_type="application/json", cache_control="no-cache, max-age=0")
