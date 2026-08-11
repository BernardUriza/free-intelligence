"""The one way this daemon speaks to a human outside HTTP: an email to its owner.

Resend, chosen for a reason that is specific and not a preference: its free tier
sends to the account's OWN address with no verified domain and no DNS records —
and the only recipient this system ever has is Bernard. A Gmail app password
would have worked too and was rejected: it is a credential to his whole mailbox,
where this is a scoped, revocable key that can do nothing but send.

Failure is REPORTED, never swallowed. A request-access button that silently
posts into a void is worse than one that says it could not reach anybody.
"""

from __future__ import annotations

import os

import httpx

API = "https://api.resend.com/emails"
# `onboarding@resend.dev` is Resend's shared sender, allowed without a verified
# domain precisely for this case: mail to your own account address.
SENDER = os.environ.get("AIRE_MAIL_FROM", "AIRE <onboarding@resend.dev>")
TIMEOUT_S = 15.0


def configured() -> bool:
    return bool(os.environ.get("RESEND_API_KEY") and os.environ.get("AIRE_OWNER_EMAIL"))


async def send(subject: str, html: str) -> None:
    """Mail the owner. Raises on any non-2xx so the caller can answer honestly."""
    key = os.environ.get("RESEND_API_KEY", "")
    owner = os.environ.get("AIRE_OWNER_EMAIL", "")
    if not key or not owner:
        raise RuntimeError("no mail transport is configured")
    async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
        response = await client.post(
            API,
            headers={"authorization": f"Bearer {key}"},
            json={"from": SENDER, "to": [owner], "subject": subject, "html": html},
        )
    if response.status_code >= 300:
        raise RuntimeError(f"resend answered {response.status_code}: {response.text[:200]}")
