"""The one outbound GET the engine makes on a caller's behalf — an image or a
document by reference (#50). A door that fetches what a caller names is an SSRF door, so
every guard lives here, in this order:

1. **Host allowlist** (`AIRE_IMAGE_HOSTS`, Discord's CDN by default), https only,
   default port only. An off-list URL is refused before a DNS query leaves.
2. **Resolve ONCE, check EVERY address, connect to the one checked.** An
   allowlist alone loses to DNS rebinding: the name resolves public when checked
   and private when connected. So the socket goes to the IP that passed, with
   `Host` and TLS SNI kept on the real name — the certificate is still verified
   against it. Any non-global address in the answer refuses the whole name
   (loopback, private, link-local and the 169.254.169.254 metadata IP, CGNAT).
3. **No redirects.** A 3xx is refused, not followed: following would need the
   same check again at every hop, and Discord's CDN does not redirect.
4. **Bounded in time and bytes**: 15 s for the whole fetch, DNS included (a CDN
   read with no timeout hung 60-120 s in hermes-agent #33400), and a byte cap
   enforced while streaming, not after the body is already in RAM."""

import asyncio
import ipaddress
import os
import socket
from typing import Any, Awaitable, Callable
from urllib.parse import urlsplit

import httpx

HOSTS = frozenset(h.strip().lower() for h in os.environ.get(
    "AIRE_IMAGE_HOSTS", "cdn.discordapp.com,media.discordapp.net").split(",") if h.strip())
MAX_FETCH_BYTES = 10 * 1024 * 1024  # Discord's free upload cap; the shrink cuts it down after
TOTAL_S = 15.0
_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)

Resolver = Callable[[str], Awaitable[list[str]]]


class FetchRefused(Exception):
    """Why a referenced file never arrived — the caller's 422 detail."""


async def system_resolve(host: str) -> list[str]:
    infos = await asyncio.get_running_loop().getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    return [info[4][0] for info in infos]


def check_url(url: str) -> str:
    """The host an allowed URL names, or a refusal — no network touched."""
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if parts.scheme != "https" or parts.port not in (None, 443) or parts.username:
        raise FetchRefused("url must be plain https on the default port")
    if host not in HOSTS:
        raise FetchRefused(f"host not allowed: {host or '?'}; allowed: {sorted(HOSTS)}")
    return host


def pin_address(host: str, addresses: list[str]) -> str:
    """The address to connect to — only if EVERY address the name gave is public."""
    if not addresses:
        raise FetchRefused(f"host did not resolve: {host}")
    for raw in addresses:
        ip = ipaddress.ip_address(raw.split("%")[0])
        if not ip.is_global or ip.is_multicast:
            raise FetchRefused(f"host resolves to a non-public address: {host}")
    return addresses[0]


def _pinned_url(url: str, ip: str) -> str:
    parts = urlsplit(url)
    netloc = f"[{ip}]" if ":" in ip else ip
    return parts._replace(netloc=netloc).geturl()


async def _read_capped(resp: httpx.Response) -> bytes:
    declared = resp.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_FETCH_BYTES:
        raise FetchRefused(f"file too big: {declared} bytes > {MAX_FETCH_BYTES}")
    body = bytearray()
    async for chunk in resp.aiter_bytes():
        body.extend(chunk)
        if len(body) > MAX_FETCH_BYTES:
            raise FetchRefused(f"file too big: over {MAX_FETCH_BYTES} bytes")
    return bytes(body)


async def _get(url: str, host: str, ip: str, transport: Any) -> bytes:
    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=False,
                                 transport=transport, trust_env=False) as client:
        req = client.build_request("GET", _pinned_url(url, ip), headers={"Host": host},
                                   extensions={"sni_hostname": host})
        resp = await client.send(req, stream=True)
        try:
            if resp.is_redirect:
                raise FetchRefused(f"url redirects ({resp.status_code}); redirects are refused")
            if resp.status_code != 200:
                raise FetchRefused(f"fetch answered {resp.status_code} (expired signature?)")
            return await _read_capped(resp)
        finally:
            await resp.aclose()


async def fetch(url: str, *, resolve: Resolver = system_resolve, transport: Any = None) -> bytes:
    """The referenced bytes, or `FetchRefused` naming why not."""
    host = check_url(url)
    try:
        async with asyncio.timeout(TOTAL_S):
            ip = pin_address(host, await resolve(host))
            return await _get(url, host, ip, transport)
    except TimeoutError as exc:
        raise FetchRefused(f"fetch timed out after {TOTAL_S:.0f}s") from exc
    except (httpx.HTTPError, OSError) as exc:
        raise FetchRefused(f"fetch failed: {type(exc).__name__}") from exc
