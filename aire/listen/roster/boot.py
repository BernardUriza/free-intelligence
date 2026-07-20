"""Boot load + periodic refresh — a DB hiccup must not stop the daemon."""

import asyncio

from ..applog import _now, append
from ..config import WHITELIST_ENFORCE
from ..tasks import spawn
from . import db, state


async def start() -> None:
    try:
        await db.load()
        append(f"{_now()} - WHITELIST loaded {len(state.IPS)} devices "
               f"(enforce={'on' if WHITELIST_ENFORCE else 'off'})")
    except Exception as exc:  # noqa: BLE001 - fail-closed is enforced at the gate
        append(f"{_now()} - WHITELIST-LOAD-ERROR {exc!r}")
        if WHITELIST_ENFORCE:
            append(f"{_now()} - WHITELIST enforce=on but roster UNLOADED "
                   "→ denying all non-loopback until it loads")
    spawn(refresher())


async def refresher(interval: int = 60) -> None:
    while True:
        await asyncio.sleep(interval)
        await db.refresh()
