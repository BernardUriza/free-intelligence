"""Gateway zombie watchdog.

Bug observed 2026-05-16/17: discord.py held a session for ~65h, kept
heartbeating to the gateway (so bot_resumed fired periodically), but
MESSAGE_CREATE events stopped reaching on_message. Users saw "Insult
online" on Discord and sent messages; the bot silently dropped them.
Bernard's `1505213719825744033` (2026-05-16 14:21Z) is the canonical
lost-message — gap of 23h in our messages table.

Detection: track the wall-clock of any socket event and specifically
MESSAGE_CREATE separately. Discord sends a HEARTBEAT_ACK every ~41s by
default, so on a healthy gateway the socket clock advances even if no
human is talking. If MESSAGE_CREATE silence stretches past 6h AND we've
seen repeated bot_resumed (gateway reconnecting, suspicious session-id
state), the gateway is zombi → force exit; Container Apps recreates the
replica with a fresh session.

Hard-fail backup: if the WebSocket heartbeat (bot.latency) is dead, the
gateway connection is gone even though our process lives → force exit.

State (socket clock, MESSAGE_CREATE clock, resume ring) plus the loop and
the two event hooks live together on one instance so they can't drift.
"""

from __future__ import annotations

import asyncio
import os
import time as _time
from collections import deque

import structlog
from discord.ext import tasks

log = structlog.get_logger()


class GatewayWatchdog:
    """Owns the liveness clocks + the 5-minute watchdog loop.

    Wire `on_socket_event` to ``@bot.event on_socket_event_type`` and
    `note_resumed` to ``@bot.event on_resumed``; start/cancel `self.loop`
    alongside the other background loops.
    """

    def __init__(self, bot) -> None:
        self._bot = bot
        self._last_socket_event_ts = _time.monotonic()
        self._last_msg_create_ts = _time.monotonic()
        self._resumed_ring: deque[float] = deque(maxlen=20)
        self.loop = self._build_loop()

    def on_socket_event(self, event_type: str) -> None:
        """Advance the socket clock; MESSAGE_CREATE also advances its own clock."""
        self._last_socket_event_ts = _time.monotonic()
        if event_type == "MESSAGE_CREATE":
            self._last_msg_create_ts = _time.monotonic()

    def note_resumed(self) -> None:
        """Record a gateway RESUME so the zombie heuristic can count reconnects."""
        self._resumed_ring.append(_time.monotonic())

    def _build_loop(self) -> tasks.Loop:
        @tasks.loop(minutes=5)
        async def _gateway_watchdog():
            now = _time.monotonic()
            # Purge resume events older than 1h.
            while self._resumed_ring and now - self._resumed_ring[0] > 3600:
                self._resumed_ring.popleft()

            socket_age = now - self._last_socket_event_ts
            msg_create_age = now - self._last_msg_create_ts
            resumes_last_hour = len(self._resumed_ring)

            # bot.latency is the WebSocket heartbeat round-trip from
            # discord.py's keepalive thread. NaN/inf = no heartbeat sent yet
            # or connection is dead. A huge value (>60s) means heartbeat ACK
            # has been silent.
            latency_s = self._bot.latency
            if not isinstance(latency_s, float) or latency_s != latency_s:  # NaN check
                latency_s = -1.0

            log.info(
                "gateway_watchdog_tick",
                socket_age_s=int(socket_age),
                msg_create_age_s=int(msg_create_age),
                resumes_last_hour=resumes_last_hour,
                latency_ms=int(latency_s * 1000) if latency_s >= 0 else -1,
            )

            # Signal A: WebSocket heartbeat is dead.
            # `bot.latency` measures the HEARTBEAT/HEARTBEAT_ACK round-trip
            # from discord.py's keepalive thread. NaN or >60s means the
            # gateway connection is no longer alive even though our process
            # is. This is the TRUE liveness signal — NOT `on_socket_event_type`,
            # which only fires for DISPATCH events (MESSAGE_CREATE, PRESENCE_UPDATE,
            # TYPING_START, etc.) and can legitimately go quiet for many minutes
            # in low-activity servers.
            if latency_s < 0 or latency_s > 60.0:
                log.critical(
                    "gateway_watchdog_heartbeat_dead_restart",
                    latency_s=latency_s,
                    socket_age_s=int(socket_age),
                )
                await asyncio.sleep(0.5)
                os._exit(1)

            # Signal B: gateway heartbeating fine but MESSAGE_CREATE starved
            # AND repeated reconnects happening — session_id is likely stale,
            # events being filtered server-side. This is the zombie bug.
            #
            # v3.9.40 fix: previous threshold (msg_create > 2h AND resumes > 0)
            # fired in healthy conditions — one network hiccup = 1 resume,
            # quiet nighttime channel = 2h silence, combination is NORMAL.
            # KQL showed 9 false restarts/24h across discord-bot + alice-bot.
            # Real zombie pattern is REPEATED reconnections (>=3 in 1h) AND
            # prolonged silence (>=6h). A single resume in healthy weekly
            # ops happens hourly and is not zombie evidence.
            if msg_create_age > 21600 and resumes_last_hour >= 3:
                log.critical(
                    "gateway_watchdog_zombie_detected_restart",
                    socket_age_s=int(socket_age),
                    msg_create_age_s=int(msg_create_age),
                    resumes_last_hour=resumes_last_hour,
                )
                await asyncio.sleep(0.5)
                os._exit(1)

        return _gateway_watchdog
