"""FastAPI server exposing the gateway's `/invite` endpoint.

This is the gateway-hosted port of `personas.alice.api.server`. The legacy
`alice-bot` container owned `/invite` while ALICE ran as a separate Discord bot;
once ALICE moved into the persona gateway (one brain per `persona_id` via the
runner), the invite endpoint must live here too — otherwise ALICE runs on two
hosts with the same token (double replies) and the legacy container cannot be
retired (it is the sole `/invite` host). See `.claude/rules/sibling-personas.md`.

Insult is the only authorized caller. Auth is the same shared bearer token
(`INSULT_TO_ALICE_TOKEN`) the legacy endpoint used, so repointing
`discord-bot.ALICE_INVITE_URL` at the gateway needs no caller change.

Endpoint contract (unchanged from the legacy server):

    POST /invite
    Authorization: Bearer <INSULT_TO_ALICE_TOKEN>
    Content-Type: application/json
    { "channel_id": "...", "guild_id": "...", "channel_name": "general", "reason": "..." }

    → 202 Accepted  { "status": "invited", "channel_id": "..." }

The persona responds asynchronously: the HTTP call returns as soon as the work
is scheduled. Insult does not wait — the reply lands in Discord directly.
"""

from __future__ import annotations

import asyncio
import hmac
import time
from typing import TYPE_CHECKING

import structlog
from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

from persona_gateway.boot import GatewayBootState

if TYPE_CHECKING:
    from persona_gateway.gateway import PersonaClient

log = structlog.get_logger()

# Which persona /invite summons when the request carries no persona_id. The
# legacy endpoint was ALICE-only and Insult's `invoke_alice` tool carries no
# persona_id, so the bare wire contract still maps /invite → "alice"; the
# optional `persona_id` field (HOST 5/6 slice C) lets the LLM router cutover
# summon any gateway persona through the same endpoint.
INVITE_PERSONA_ID = "alice"

# A persona is "mute-suspected" only if the last addressed message it saw is
# older than this AND no reply followed. A single turn's runner call can take
# ~120s; 180s leaves margin so an in-flight turn is never misread as mute.
_MUTE_GRACE_SECONDS = 180.0


class InviteRequest(BaseModel):
    """What Insult sends when it wants the persona in the channel."""

    channel_id: str = Field(..., min_length=1)
    guild_id: str | None = None
    channel_name: str | None = None
    reason: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Free-text reason the persona is summoned. Instruction, not user message.",
    )
    persona_id: str | None = Field(
        default=None,
        description="Gateway persona to summon. Omitted → alice (legacy wire contract).",
    )
    invited_by: str | None = Field(
        default=None,
        description="Summon source label for telemetry/instruction framing. Omitted → insult_rest.",
    )
    trigger_message_id: str | None = Field(
        default=None,
        description=(
            "Discord message id that triggered the summon. The persona reacts to it "
            "when its reply carries [REACT:] markers; omitted → reactions are dropped."
        ),
    )


class InviteResponse(BaseModel):
    status: str
    channel_id: str
    detail: str | None = None


def build_invite_app(
    personas: dict[str, PersonaClient],
    expected_token: str,
    boot: GatewayBootState | None = None,
) -> FastAPI:
    """Wire FastAPI with bearer auth + the /invite handler.

    `personas` is the live persona_id → PersonaClient registry the gateway builds
    in `_main`; the handler routes the invite to `INVITE_PERSONA_ID`'s client.
    `boot` carries the shared boot signals `/health` reports honestly.
    """
    app = FastAPI(title="Persona Gateway Invite API", version="1.0.0")
    app.state.background_tasks = set()
    state = boot if boot is not None else GatewayBootState()

    def _ready_personas() -> list[str]:
        return sorted(
            persona_id
            for persona_id, client in personas.items()
            if getattr(client, "user", None) is not None and not state.is_down(persona_id)
        )

    @app.get("/health")
    async def health() -> dict[str, object]:
        ready = _ready_personas()
        now = time.time()

        def _age(ts: float | None) -> float | None:
            return None if ts is None else round(now - ts, 1)

        # "Alive but mute" (#14): a persona that took an addressed message and
        # produced no reply. serving:true can't see it; these can. Suspected when
        # a message was seen more recently than a turn was delivered AND that
        # message is older than the grace window (a turn's own runner call can
        # take up to ~2 min — below the window it's just in flight, not mute).
        liveness: dict[str, dict] = {}
        mute_suspected: list[str] = []
        for persona_id, client in personas.items():
            seen = getattr(client, "last_message_seen", None)
            delivered = getattr(client, "last_turn_delivered", None)
            is_mute = (
                seen is not None and (delivered is None or seen > delivered) and (now - seen) > _MUTE_GRACE_SECONDS
            )
            if is_mute:
                mute_suspected.append(persona_id)
            liveness[persona_id] = {
                "last_message_age_s": _age(seen),
                "last_turn_age_s": _age(delivered),
                "mute_suspected": is_mute,
            }

        return {
            "status": "ok",
            "service": "persona-gateway-invite",
            "serving": bool(ready),
            "personas_ready": ready,
            "personas_expected": sorted(personas),
            "personas_down": sorted(state.personas_down),
            "db_connected": state.db_connected,
            # The anti-boot-zombie signal: serving:true is NOT proof of answering.
            "liveness": liveness,
            "mute_suspected": sorted(mute_suspected),
        }

    @app.post("/invite", response_model=InviteResponse, status_code=status.HTTP_202_ACCEPTED)
    async def invite(req: InviteRequest, authorization: str | None = Header(default=None)) -> InviteResponse:
        if not expected_token:
            log.error("persona_gateway_invite_no_token_configured")
            raise HTTPException(status_code=503, detail="Invite endpoint not configured (missing token).")

        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing bearer token")
        provided = authorization[len("Bearer ") :]
        if not hmac.compare_digest(provided, expected_token):
            raise HTTPException(status_code=401, detail="Invalid token")

        persona_id = req.persona_id or INVITE_PERSONA_ID
        client = personas.get(persona_id)
        if client is None and req.persona_id:
            log.warning(
                "persona_gateway_invite_unknown_persona",
                persona_id=persona_id,
                known=sorted(personas),
            )
            raise HTTPException(status_code=400, detail=f"Unknown persona_id {persona_id!r}.")
        if client is None or client.user is None:
            log.error("persona_gateway_invite_persona_not_ready", persona_id=persona_id)
            raise HTTPException(status_code=503, detail="Persona not finished booting; retry in a few seconds.")

        # Fire-and-forget: the persona responds asynchronously. Keep a reference
        # on app state so the task isn't GC'd mid-flight (RUF006); auto-pruned.
        task = asyncio.create_task(
            client.respond_to_invite(
                channel_id=req.channel_id,
                guild_id=req.guild_id,
                channel_name=req.channel_name,
                reason=req.reason,
                invited_by=req.invited_by or "insult_rest",
                trigger_message_id=req.trigger_message_id,
            )
        )
        app.state.background_tasks.add(task)
        task.add_done_callback(app.state.background_tasks.discard)
        log.info(
            "persona_gateway_invite_scheduled",
            persona_id=persona_id,
            channel_id=req.channel_id,
            invited_by=req.invited_by or "insult_rest",
            reason_preview=req.reason[:100],
        )
        return InviteResponse(status="invited", channel_id=req.channel_id)

    return app
