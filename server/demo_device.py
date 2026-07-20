"""app-demo-device — a simulated device (like a GPS receiver).

Opens a TCP connection to AIRE and sends it, forever and at random:
- a **KEEPALIVE** every ~2s — the heartbeat, like a GPS saying "still alive".
- a random **MESSAGE** now and then — position, speed, panic, geofence.
- an occasional **MKDIR** — it asks the daemon for a session casita, at random
  moments, hard-capped at 2 per hour. The pacing rules live HERE, in the
  device: the server only checks the token, it knows nothing about rhythms.
  Needs ``AIRE_VERB_TOKEN`` in the environment; without it the device never
  asks (its unit loads it from ``/etc/aire/env``).

It is the demo app from the brief: it keeps sending messages to the always-open
server. It knows nothing about AIRE or AI — it just writes lines to a socket,
exactly like a GPS receiver pushing over GPRS.

    python demo_device.py                        # one device
    DEVICE_ID=patrol-07 python demo_device.py    # another device, in parallel
"""

from __future__ import annotations

import asyncio
import os
import random
import time
from collections import deque

HOST = os.environ.get("AIRE_HOST", "127.0.0.1")
PORT = int(os.environ.get("AIRE_PORT", "9099"))
DEVICE = os.environ.get("DEVICE_ID", "app-demo-device-01")
VERB_TOKEN = os.environ.get("AIRE_VERB_TOKEN", "")
MKDIR_MAX_PER_HOUR = 2
MKDIR_CHANCE = float(os.environ.get("MKDIR_CHANCE", "0.0011"))

EVENTS = [
    "POS lat=20.6736 lon=-103.3440",
    "POS lat=20.6598 lon=-103.3496",
    "SPEED 82kmh",
    "SPEED 118kmh OVERSPEED",
    "IGN on",
    "IGN off",
    "PANIC button-pressed",
    "GEOFENCE exit downtown-zone",
]

CASITA_NAMES = [
    "bio-sim",
    "market-scan",
    "route-optimizer",
    "weather-model",
    "genome-notes",
]


async def maybe_ask_for_casita(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    recent: deque[float],
) -> None:
    """The device's own pacing law: random moments, at most 2 per hour."""
    if not VERB_TOKEN or random.random() >= MKDIR_CHANCE:
        return
    now = time.monotonic()
    while recent and now - recent[0] > 3600:
        recent.popleft()
    if len(recent) >= MKDIR_MAX_PER_HOUR:
        return
    name = random.choice(CASITA_NAMES)
    writer.write(f"MKDIR {VERB_TOKEN} {name}\n".encode())
    await writer.drain()
    ack = await asyncio.wait_for(reader.readline(), timeout=10)
    recent.append(now)
    print(f"{DEVICE} asked for casita '{name}' → {ack.decode().strip()}", flush=True)


async def main() -> None:
    reader, writer = await asyncio.open_connection(HOST, PORT)
    print(f"{DEVICE} connected to AIRE {HOST}:{PORT}", flush=True)
    seq = 0
    recent_mkdirs: deque[float] = deque()
    try:
        while True:
            seq += 1
            writer.write(f"{DEVICE} KEEPALIVE seq={seq}\n".encode())
            await writer.drain()
            if random.random() < 0.4:  # ~40% of ticks carry a real message
                writer.write(f"{DEVICE} MESSAGE {random.choice(EVENTS)}\n".encode())
                await writer.drain()
            await maybe_ask_for_casita(reader, writer, recent_mkdirs)
            await asyncio.sleep(2)
    finally:
        writer.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
