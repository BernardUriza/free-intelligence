"""app-demo-device — a simulated device (like a GPS receiver).

Opens a TCP connection to AIRE and sends it, forever and at random:
- a **KEEPALIVE** every ~2s — the heartbeat, like a GPS saying "still alive".
- a random **MESSAGE** now and then — position, speed, panic, geofence.

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

HOST = os.environ.get("AIRE_HOST", "127.0.0.1")
PORT = int(os.environ.get("AIRE_PORT", "9099"))
DEVICE = os.environ.get("DEVICE_ID", "app-demo-device-01")

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


async def main() -> None:
    _reader, writer = await asyncio.open_connection(HOST, PORT)
    print(f"{DEVICE} connected to AIRE {HOST}:{PORT}", flush=True)
    seq = 0
    try:
        while True:
            seq += 1
            writer.write(f"{DEVICE} KEEPALIVE seq={seq}\n".encode())
            await writer.drain()
            if random.random() < 0.4:  # ~40% of ticks carry a real message
                writer.write(f"{DEVICE} MESSAGE {random.choice(EVENTS)}\n".encode())
                await writer.drain()
            await asyncio.sleep(2)
    finally:
        writer.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
