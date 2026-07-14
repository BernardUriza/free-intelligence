"""app-demo-device — un dispositivo simulado (como un GPS).

Abre una conexión TCP a AIRE y le manda, para siempre y al azar:
- un **KEEPALIVE** cada ~2s — el latido, como el GPS diciendo "sigo vivo".
- un **MESSAGE** random de vez en cuando — posición, velocidad, pánico, geocerca.

Es la app demo del enunciado: le anda mandando mensajes al servidor siempre
abierto. No sabe nada de AIRE ni de IA — solo escribe líneas a un socket, igual
que un receptor GPS empujando por GPRS.

    python demo_device.py            # un device
    DEVICE_ID=patrulla-07 python demo_device.py   # otro device, en paralelo
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
    "SPEED 118kmh EXCESO",
    "IGN on",
    "IGN off",
    "PANIC boton-presionado",
    "GEOFENCE salida zona-centro",
]


async def main() -> None:
    _reader, writer = await asyncio.open_connection(HOST, PORT)
    print(f"{DEVICE} conectado a AIRE {HOST}:{PORT}", flush=True)
    seq = 0
    try:
        while True:
            seq += 1
            writer.write(f"{DEVICE} KEEPALIVE seq={seq}\n".encode())
            await writer.drain()
            if random.random() < 0.4:  # ~40% de los ticks lleva un mensaje real
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
