"""The daemon that listens — story: docs/listener-doctrine.md; parts: aire/listen/."""

import asyncio

from .listen import roster
from .listen.applog import MIRRORS, _now, append
from .listen.config import DSN, HOST, LOG, PORT
from .listen.net import handle
from .listen.pen import Pen
from .listen.tasks import spawn


async def main() -> None:
    if DSN:
        pen = Pen(DSN)
        MIRRORS.append(pen.write)
        spawn(pen.run())
        await roster.start()
    server = await asyncio.start_server(handle, HOST, PORT)
    append(f"{_now()} - LISTENING {HOST}:{PORT}")
    print(f"AIRE listener listening on {HOST}:{PORT} → {LOG}", flush=True)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
