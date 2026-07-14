"""AIRE — el daemon que escucha. SIN inteligencia.

El chasis eterno, desnudo: `accept()` → lee líneas → **append al log**. Es el
daemon de EC-GPS —un servicio siempre prendido escuchando en un puerto TCP— sin
el Perl y sin el cerebro. La IA (engine/render/store, que siguen en el repo) se
sienta DESPUÉS, entre el `accept()` y el append. Hoy no está: a propósito.

Cada línea que llega de un device se agrega, tal cual, a un log **append-only**
(`aire.log`), con timestamp y el peer. Greppable, que es toda la meta:

    tail -f aire.log | grep KEEPALIVE      # los latidos, en vivo
    grep MESSAGE aire.log                   # los mensajes random del device

El día que esto viva en una VM de Azure, "entrar por SSH y hacer grep" es
literalmente eso — la experiencia de EC-GPS, recreada.
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path

LOG = Path(os.environ.get("AIRE_LOG", Path(__file__).resolve().parent.parent / "aire.log"))
HOST = os.environ.get("AIRE_HOST", "0.0.0.0")
PORT = int(os.environ.get("AIRE_PORT", "9099"))


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def append(line: str) -> None:
    """Append-only: solo se agrega, nunca se reescribe (la ley del repo,
    [[log-es-la-verdad]]). El log ES la verdad."""
    with LOG.open("a") as f:
        f.write(line + "\n")
        f.flush()


async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    peer = writer.get_extra_info("peername")
    addr = f"{peer[0]}:{peer[1]}" if peer else "?"
    append(f"{_now()} {addr} CONNECT")
    try:
        while True:
            raw = await reader.readline()
            if not raw:  # el device cerró la conexión
                break
            msg = raw.decode(errors="replace").rstrip("\r\n")
            if msg:
                append(f"{_now()} {addr} {msg}")
    finally:
        append(f"{_now()} {addr} DISCONNECT")
        writer.close()


async def main() -> None:
    server = await asyncio.start_server(handle, HOST, PORT)
    append(f"{_now()} - LISTENING {HOST}:{PORT}")
    print(f"AIRE listener escuchando en {HOST}:{PORT} → {LOG}", flush=True)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
