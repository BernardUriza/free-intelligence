"""FastAPI server exposing ALICE's `/invite` endpoint.

Insult is the only authorized caller. Auth is a shared bearer token
(`INSULT_TO_ALICE_TOKEN`) — not OAuth, not JWT, because both bots run
in trusted infrastructure and the token is short-lived secret rotation
handled by Azure Key Vault out-of-band.

Endpoint contract:

    POST /invite
    Authorization: Bearer <INSULT_TO_ALICE_TOKEN>
    Content-Type: application/json
    {
      "channel_id": "1489...",
      "guild_id": "1489...",
      "channel_name": "general",
      "reason": "Bernard is pattern-matching on Alex's silence; I'm getting too sharp. Need empathic mirror."
    }

    → 202 Accepted
    { "status": "invited", "channel_id": "..." }

ALICE responds asynchronously: the HTTP call returns as soon as she's
scheduled the work. Insult doesn't wait for her reply — her reply
arrives in the Discord channel directly (where Insult can see it via
the shared `messages` table on the next turn).
"""

from __future__ import annotations

import asyncio
import hmac
from typing import TYPE_CHECKING

import structlog
from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from alice.app import Container

log = structlog.get_logger()


class InviteRequest(BaseModel):
    """What Insult sends when she wants ALICE in the channel."""

    channel_id: str = Field(..., min_length=1)
    guild_id: str | None = None
    channel_name: str | None = None
    reason: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Free-text reason why ALICE is being summoned. Treated as instruction, not user message.",
    )


class InviteResponse(BaseModel):
    status: str
    channel_id: str
    detail: str | None = None


def build_app(container: Container) -> FastAPI:
    """Wire FastAPI with auth middleware + the /invite handler.

    Container is passed in so the handler can reach the chat cog
    (`container.bot._alice_chat_cog`) without a global import dance.
    """
    app = FastAPI(title="ALICE Invite API", version="0.1.0")
    expected_token = container.settings.insult_to_alice_token
    # Set of live background tasks so create_task references survive GC.
    app.state.background_tasks = set()

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Liveness probe — public, no auth.

        Same posture as Insult's `/debug/health`: always 200, body
        carries the actual state for monitoring to interpret.
        """
        return {"status": "ok", "service": "alice-invite"}

    @app.post("/invite", response_model=InviteResponse, status_code=status.HTTP_202_ACCEPTED)
    async def invite(req: InviteRequest, authorization: str | None = Header(default=None)) -> InviteResponse:
        """Receive an invite from Insult. Schedule ALICE's response."""
        # Auth: bearer token must match exactly. `hmac.compare_digest` is
        # constant-time to deny timing side-channels. Same pattern as
        # Insult's `_auth_middleware` for /debug.
        if not expected_token:
            log.error("alice_invite_no_token_configured")
            raise HTTPException(status_code=503, detail="ALICE invite endpoint not configured (missing token).")

        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing bearer token")
        provided = authorization[len("Bearer ") :]
        if not hmac.compare_digest(provided, expected_token):
            raise HTTPException(status_code=401, detail="Invalid token")

        # Pull the cog the lazy way — set by bot.py at boot.
        cog = getattr(container.bot, "_alice_chat_cog", None)
        if cog is None:
            log.error("alice_invite_cog_not_ready")
            raise HTTPException(status_code=503, detail="ALICE not finished booting; retry in a few seconds.")

        # Fire-and-forget: ALICE responds asynchronously. The HTTP call
        # returns 202 immediately. Errors inside the response coroutine
        # are logged inside `_respond` itself — not surfaced to Insult,
        # because by then the user is the audience, not the API caller.
        # We keep a reference on the FastAPI app state so the task isn't
        # garbage-collected mid-flight (RUF006); auto-pruned on completion.
        task = asyncio.create_task(
            cog.respond_to_invite(
                channel_id=req.channel_id,
                guild_id=req.guild_id,
                channel_name=req.channel_name,
                reason=req.reason,
                invited_by="insult_rest",
            )
        )
        app.state.background_tasks.add(task)
        task.add_done_callback(app.state.background_tasks.discard)
        log.info(
            "alice_invite_accepted",
            channel_id=req.channel_id,
            reason_preview=req.reason[:100],
        )
        return InviteResponse(status="invited", channel_id=req.channel_id)

    return app
