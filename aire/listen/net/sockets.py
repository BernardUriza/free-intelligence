"""Socket helpers: peer identity + best-effort teardown."""

import asyncio


def peer_info(writer: asyncio.StreamWriter) -> tuple[str, str, bool]:
    peer = writer.get_extra_info("peername")
    addr = f"{peer[0]}:{peer[1]}" if peer else "?"
    ip = peer[0] if peer else "?"
    return ip, addr, ip.startswith("127.") or ip == "::1"


async def hangup(writer: asyncio.StreamWriter) -> None:
    writer.close()
    try:
        await writer.wait_closed()
    except Exception:  # noqa: BLE001 - teardown of a dead socket is best-effort
        pass
