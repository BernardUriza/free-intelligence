"""Read and sanitize one line: None → close; '' → skip; text → process."""

import asyncio

from ..applog import _now, append
from ..config import MAX_LINE_BYTES


async def read_line(reader: asyncio.StreamReader, addr: str) -> str | None:
    try:
        raw = await reader.readline()
    except ValueError:
        append(f"{_now()} {addr} OVERLONG-LINE dropped")
        return None
    if not raw:
        return None
    if len(raw) > MAX_LINE_BYTES:
        append(f"{_now()} {addr} OVERSIZED-LINE dropped")
        return None
    # NUL is valid UTF-8 but Postgres text cannot hold it — the 6-day poison
    # pill (docs/listener-doctrine.md). Neutralize it at the mouth.
    return raw.decode(errors="replace").replace("\x00", "�").rstrip("\r\n")
