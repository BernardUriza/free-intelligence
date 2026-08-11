"""Request access — the second half of the landing (backlog #32, slice c).

A stranger who liked the name the model gave them presses one button. Bernard
gets an email with a link. Clicking that link IS the approval — there is no
console to log into, no queue to remember, no second factor to invent.

Two things this deliberately does NOT do, and they are slice (d): mint a token
for the approved nickname, and teach `server.py` to accept it. Recording an
approval nobody enforces is honest; issuing a credential nobody checks would be
theatre.

The signature is what makes a link in an inbox safe to trust. `/access/approve`
cannot carry a Bearer token — it is clicked from a mail client — so the HMAC
over `nickname|expiry` IS its authentication, verified in constant time. An
unsigned approve URL would let anyone who guesses a nickname approve themselves.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from html import escape

import asyncpg
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse

from . import mail

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


def _sign(nickname: str, expiry: int) -> str:
    payload = f"{nickname}|{expiry}".encode("utf-8")
    digest = hmac.new(_secret(), payload, hashlib.sha256).hexdigest()[:32]
    return f"{expiry}.{digest}"


def _valid(nickname: str, ticket: str) -> bool:
    expiry, _, _ = ticket.partition(".")
    if not expiry.isdigit() or int(expiry) < time.time():
        return False
    return hmac.compare_digest(_sign(nickname, int(expiry)), ticket)


def _throttled() -> bool:
    """A public button that mails a real person is a spam cannon until it is
    capped. The window is global on purpose: the front proxies every visitor, so
    per-IP counting here would see one address and stop nothing."""
    cutoff = time.time() - 3600
    _sent[:] = [t for t in _sent if t > cutoff]
    return len(_sent) >= MAX_PER_HOUR


async def _record(nickname: str, blurb: str) -> None:
    conn = await asyncpg.connect(os.environ.get("AIRE_DATABASE_URL", ""), timeout=10)
    try:
        await conn.execute(DDL)  # as role `aire`, so the console's reader can see it
        await conn.execute(
            "INSERT INTO aire_access_request (nickname, blurb) VALUES ($1, $2) "
            "ON CONFLICT (nickname) DO UPDATE SET blurb = EXCLUDED.blurb",
            nickname, blurb or None,
        )
    finally:
        await conn.close()


async def _approve(nickname: str) -> None:
    conn = await asyncpg.connect(os.environ.get("AIRE_DATABASE_URL", ""), timeout=10)
    try:
        await conn.execute(DDL)
        await conn.execute(
            "UPDATE aire_access_request SET approved_at = now() WHERE nickname = $1", nickname
        )
    finally:
        await conn.close()


def _invitation(nickname: str, blurb: str, link: str) -> str:
    return (
        f"<p><b>{escape(nickname)}</b> wants in.</p>"
        f"<blockquote>{escape(blurb or '(said nothing)')}</blockquote>"
        f"<p>Clicking this approves them — nothing else is needed:</p>"
        f'<p><a href="{escape(link)}">approve {escape(nickname)}</a></p>'
        f"<p style='color:#888;font-size:12px'>The link expires in 14 days. "
        f"Ignoring it is a refusal.</p>"
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
        await mail.send(f"AIRE — {nickname} wants in", _invitation(nickname, blurb, link))
    except Exception as exc:  # noqa: BLE001 — the visitor deserves the truth
        return JSONResponse({"detail": f"could not reach the owner: {exc}"}, status_code=502)
    _sent.append(time.time())
    return JSONResponse({"status": "sent", "nickname": nickname})


@router.get("/approve")
async def approve(n: str = "", t: str = "") -> RedirectResponse:
    """Bernard clicks this from his inbox. The daemon writes (it holds the pen)
    and hands the rendering to the front, which is the only half allowed to show
    a human anything."""
    front = os.environ.get("AIRE_FRONT_URL", "https://aire.bernarduriza.com")
    if not n or not _valid(n, t):
        return RedirectResponse(f"{front}/approved?bad=1", status_code=303)
    await _approve(n)
    return RedirectResponse(f"{front}/approved?n={n}", status_code=303)
