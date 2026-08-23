"""Request access — the second half of the landing (backlog #32, slices c and d).

A stranger who liked the name the model gave them presses one button. Bernard
gets an email with a link. Clicking that link IS the approval — there is no
console to log into, no queue to remember, no second factor to invent — and it
mints that nickname's key, which arrives in a second mail with its own revoke
link. Nobody is ever asked for an email address: the visitor leaves a name, and
Bernard hands over the key however he likes. AIRE stores no stranger's contact.

The signature is what makes a link in an inbox safe to trust. These routes cannot
carry a Bearer token — they are clicked from a mail client — so the HMAC over
`verb|nickname|expiry` IS their authentication, verified in constant time. The
verb is signed in, so an approve link cannot be replayed as a revoke by editing
the path, and an unsigned URL would let anyone who guesses a nickname let
themselves in.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse

from . import db, mail, tokens

router = APIRouter(prefix="/access")
DDL = (
    "CREATE TABLE IF NOT EXISTS aire_access_request ("
    "nickname text PRIMARY KEY, blurb text, "
    "requested_at timestamptz NOT NULL DEFAULT now(), approved_at timestamptz);"
)
LINK_TTL_S = 14 * 24 * 3600
MAX_PER_HOUR = 12
_sent: list[float] = []


def _secret() -> bytes:
    return os.environ.get("AIRE_ACCESS_SECRET", "").encode("utf-8")


def _sign(nickname: str, expiry: int, verb: str = "approve") -> str:
    payload = f"{verb}|{nickname}|{expiry}".encode("utf-8")
    digest = hmac.new(_secret(), payload, hashlib.sha256).hexdigest()[:32]
    return f"{expiry}.{digest}"


def _valid(nickname: str, ticket: str, verb: str = "approve") -> bool:
    """The verb is INSIDE the signature, so an approve link can never be replayed
    as a revoke link (or the reverse) by editing the path."""
    expiry, _, _ = ticket.partition(".")
    if not expiry.isdigit() or int(expiry) < time.time():
        return False
    return hmac.compare_digest(_sign(nickname, int(expiry), verb), ticket)


def _throttled() -> bool:
    """A public button that mails a real person is a spam cannon until it is
    capped. The window is global on purpose: the front proxies every visitor, so
    per-IP counting here would see one address and stop nothing."""
    cutoff = time.time() - 3600
    _sent[:] = [t for t in _sent if t > cutoff]
    return len(_sent) >= MAX_PER_HOUR


async def _record(nickname: str, blurb: str) -> None:
    async with db.acquire() as conn:
        await conn.execute(DDL)  # as role `aire`, so the console's reader can see it
        await conn.execute(
            "INSERT INTO aire_access_request (nickname, blurb) VALUES ($1, $2) "
            "ON CONFLICT (nickname) DO UPDATE SET blurb = EXCLUDED.blurb",
            nickname, blurb or None,
        )


async def _approve(nickname: str) -> None:
    async with db.acquire() as conn:
        await conn.execute(DDL)
        await conn.execute(
            "UPDATE aire_access_request SET approved_at = now() WHERE nickname = $1", nickname
        )


@router.post("/request")
async def request_access(request: Request) -> JSONResponse:
    if not _secret() or not mail.configured():
        return JSONResponse({"detail": "invitations are not wired up yet"}, status_code=503)
    body = await request.json()
    nickname = str(body.get("nickname", "")).strip()[:80]
    blurb = str(body.get("blurb", "")).strip()[:400]
    if not nickname:
        return JSONResponse({"detail": "a nickname is required"}, status_code=400)
    if _throttled():
        return JSONResponse({"detail": "too many requests today, try tomorrow"}, status_code=429)

    expiry = int(time.time()) + LINK_TTL_S
    base = os.environ.get("AIRE_GATE_PUBLIC_URL", "https://gate.bernarduriza.com")
    link = f"{base}/access/approve?n={nickname}&t={_sign(nickname, expiry)}"
    await _record(nickname, blurb)
    try:
        await mail.send(f"AIRE — {nickname} wants in", mail.invitation(nickname, blurb, link))
    except Exception as exc:  # noqa: BLE001 — the visitor deserves the truth
        return JSONResponse({"detail": f"could not reach the owner: {exc}"}, status_code=502)
    _sent.append(time.time())
    return JSONResponse({"status": "sent", "nickname": nickname})


@router.get("/approve")
async def approve(n: str = "", t: str = "") -> RedirectResponse:
    """Bernard clicks this from his inbox. The daemon writes (it holds the pen)
    and hands the rendering to the front, which is the only half allowed to show
    a human anything.

    The minted key goes back by MAIL, never in the redirect: a secret in a URL
    lands in browser history and in the front's access logs, and this one is a
    working credential."""
    front = os.environ.get("AIRE_FRONT_URL", "https://aire.bernarduriza.com")
    if not n or not _valid(n, t):
        return RedirectResponse(f"{front}/approved?bad=1", status_code=303)
    await _approve(n)
    key = await tokens.mint(n)
    base = os.environ.get("AIRE_GATE_PUBLIC_URL", "https://gate.bernarduriza.com")
    expiry = int(time.time()) + LINK_TTL_S
    revoke_link = f"{base}/access/revoke?n={n}&t={_sign(n, expiry, 'revoke')}"
    await mail.send(f"AIRE — the key for {n}", mail.key_issued(n, key, revoke_link))
    return RedirectResponse(f"{front}/approved?n={n}", status_code=303)


@router.get("/revoke")
async def revoke(n: str = "", t: str = "") -> RedirectResponse:
    """The undo, in the same inbox as the key. Revoking is idempotent — clicking
    an old revoke link twice is not an error, it is the same answer."""
    front = os.environ.get("AIRE_FRONT_URL", "https://aire.bernarduriza.com")
    if not n or not _valid(n, t, "revoke"):
        return RedirectResponse(f"{front}/approved?bad=1", status_code=303)
    await tokens.revoke(n)
    return RedirectResponse(f"{front}/approved?revoked={n}", status_code=303)
