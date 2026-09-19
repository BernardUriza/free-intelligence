"""FastAPI server exposing the gateway's `/invite` endpoint.

This is the gateway-hosted port of `personas.alice.api.server`. The legacy
`alice-bot` container owned `/invite` while ALICE ran as a separate Discord bot;
once ALICE moved into the persona gateway (one brain per `persona_id` via the
runner), the invite endpoint must live here too — otherwise ALICE runs on two
hosts with the same token (double replies) and the legacy container cannot be
retired (it is the sole `/invite` host). See `.claude/rules/sibling-personas.md`.

The host is the caller. Auth is a shared bearer token (`GATEWAY_INVITE_TOKEN`),
carried over from the legacy ALICE-only endpoint this replaced — renamed
2026-08-06 because the endpoint summons ANY persona and the old name made every
log line and env var claim otherwise.

Endpoint contract (unchanged from the legacy server):

    POST /invite
    Authorization: Bearer <GATEWAY_INVITE_TOKEN>
    Content-Type: application/json
    { "channel_id": "...", "guild_id": "...", "channel_name": "general", "reason": "..." }

    → 202 Accepted  { "status": "invited", "channel_id": "..." }

The persona responds asynchronously: the HTTP call returns as soon as the work
is scheduled. Insult does not wait — the reply lands in Discord directly.

With ``"wait": true`` (2026-09-03) the call AWAITS the turn and reports what
actually happened, because a 202 at scheduling time made success and failure
indistinguishable to the host — the persona was left to mumble "…" on its own:

    → 200 OK           { "status": "delivered" | "empty", "channel_id": "..." }
    → 502 Bad Gateway  { "status": "failed", "channel_id": "...", "detail": "<error type>" }

A waiting caller OWNS the failure: the gateway posts no "…" on this path. The
host retries once and, if the persona still cannot answer, says so in its own
voice (`demux_ai/fallback.py`).

Con ``"wait": true, "ticket": true`` (2026-09-19) la espera deja de ser UNA
request: el ingress de Container Apps corta toda request a los 240 s, y un turno
de Opus con caché frío puede tardar más (326.9 s, entregado y tirado). El turno
corre en una task del gateway y el host pregunta por su boleto en requests cortas:

    → 202 Accepted  { "status": "running", "channel_id": "...", "turn_id": "..." }
    GET /invite/turns/{turn_id}?wait_s=45
    → 200 OK        { "status": "running" | "delivered" | "empty" | "failed", ... }
    → 404           el gateway se reinició con el turno adentro
"""

from __future__ import annotations

import asyncio
import hmac
import time
from typing import TYPE_CHECKING

import structlog
from fastapi import FastAPI, Header, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from khimeras_shared.tickets import MAX_WAIT_S, TicketRegistry
from persona_gateway.boot import GatewayBootState
from shared.personas.registry import DEFAULT_INVITE_PERSONA_ID

if TYPE_CHECKING:
    from shared.personas.registry import DEFAULT_INVITE_PERSONA_ID
from persona_gateway.gateway import PersonaClient

log = structlog.get_logger()

# Which persona /invite summons when the request carries no persona_id. The
# legacy endpoint was ALICE-only, so the bare wire contract still maps
# /invite → "alice"; the optional `persona_id` field (HOST 5/6 slice C) lets a
# caller summon any gateway persona through the same endpoint.
INVITE_PERSONA_ID = DEFAULT_INVITE_PERSONA_ID

# A persona is "mute-suspected" only if the last addressed message it saw is
# older than this AND no reply followed. Un turno puede durar hasta
# `first_turn_timeout_s` (600 s desde 2026-09-19, vía boleto); el margen va por
# encima para que un turno vivo nunca se lea como mudez.
_MUTE_GRACE_SECONDS = 660.0


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
    trigger_transcript: str = Field(
        default="",
        description=(
            "What the trigger message's voice notes SAID, transcribed by the host — "
            "the only component that talks to susurro. Uncapped on purpose: `reason` "
            "is truncated for the router, this is the persona's copy of the words."
        ),
    )
    wait: bool = Field(
        default=False,
        description=(
            "Await the turn and report its outcome (200 delivered/empty, 502 failed) "
            "instead of a 202 at scheduling time. The waiting caller owns the failure "
            "UX: the gateway posts no '…' on this path."
        ),
    )
    ticket: bool = Field(
        default=False,
        description=(
            "With wait: answer 202 + turn_id at once and let the caller poll "
            "GET /invite/turns/{turn_id}. The turn's length stops being a request's length."
        ),
    )


class InviteResponse(BaseModel):
    status: str
    channel_id: str
    detail: str | None = None
    turn_id: str | None = None


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
    app.state.turn_tickets = TicketRegistry[str]("invite-turn")
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
            # SIGTERM recibido: esta réplica ya NO acepta turnos nuevos y está
            # esperando a los vivos. `serving` sigue diciendo la verdad sobre
            # quién puede contestar; esto dice si va a seguir aceptando.
            "stopping": state.stopping,
            # The anti-boot-zombie signal: serving:true is NOT proof of answering.
            "liveness": liveness,
            "mute_suspected": sorted(mute_suspected),
        }

    @app.post("/invite", response_model=InviteResponse, status_code=status.HTTP_202_ACCEPTED)
    async def invite(
        req: InviteRequest, authorization: str | None = Header(default=None)
    ) -> InviteResponse | JSONResponse:
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

        if req.wait and req.ticket:
            # El turno corre aquí; el host pregunta por el boleto. El turno
            # sigue siendo del host (fallback=False): el gateway no pone "…".
            ticket = app.state.turn_tickets.submit(
                client.dispatch_invite(
                    channel_id=req.channel_id,
                    guild_id=req.guild_id,
                    channel_name=req.channel_name,
                    reason=req.reason,
                    invited_by=req.invited_by or "insult_rest",
                    trigger_message_id=req.trigger_message_id,
                    trigger_transcript=req.trigger_transcript,
                    fallback=False,
                ),
                label=req.channel_id,
            )
            log.info(
                "persona_gateway_invite_ticketed",
                persona_id=persona_id,
                channel_id=req.channel_id,
                invited_by=req.invited_by or "insult_rest",
                turn_id=ticket.ticket_id,
            )
            return InviteResponse(status="running", channel_id=req.channel_id, turn_id=ticket.ticket_id)

        if req.wait:
            # The caller owns the outcome — so it gets the outcome, not a receipt
            # for the scheduling. No "…" from the gateway on this path.
            outcome = await client.dispatch_invite(
                channel_id=req.channel_id,
                guild_id=req.guild_id,
                channel_name=req.channel_name,
                reason=req.reason,
                invited_by=req.invited_by or "insult_rest",
                trigger_message_id=req.trigger_message_id,
                trigger_transcript=req.trigger_transcript,
                fallback=False,
            )
            log.info(
                "persona_gateway_invite_awaited",
                persona_id=persona_id,
                channel_id=req.channel_id,
                invited_by=req.invited_by or "insult_rest",
                outcome=outcome,
            )
            code = status.HTTP_502_BAD_GATEWAY if outcome == "failed" else status.HTTP_200_OK
            body = InviteResponse(status=outcome, channel_id=req.channel_id)
            return JSONResponse(status_code=code, content=body.model_dump())

        # Fire-and-forget: the persona responds asynchronously. Keep a reference
        # on app state so the task isn't GC'd mid-flight (RUF006); auto-pruned.
        task = asyncio.create_task(
            client.dispatch_invite(
                channel_id=req.channel_id,
                guild_id=req.guild_id,
                channel_name=req.channel_name,
                reason=req.reason,
                invited_by=req.invited_by or "insult_rest",
                trigger_message_id=req.trigger_message_id,
                trigger_transcript=req.trigger_transcript,
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

    @app.get("/invite/turns/{turn_id}", response_model=InviteResponse)
    async def poll_turn(
        turn_id: str,
        authorization: str | None = Header(default=None),
        wait_s: float = Query(default=MAX_WAIT_S, ge=0.0),
    ) -> InviteResponse:
        """Long-poll acotado del boleto de un `/invite` con ticket.

        Un `dispatch_invite` nunca levanta — devuelve "failed" — así que aquí
        no hay excepción que mapear: el outcome viaja tal cual. 404 = el
        gateway se reinició con el turno adentro; el host lo lee como
        "unreachable" y aplica su reintento único.
        """
        if not expected_token:
            raise HTTPException(status_code=503, detail="Invite endpoint not configured (missing token).")
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing bearer token")
        if not hmac.compare_digest(authorization[len("Bearer ") :], expected_token):
            raise HTTPException(status_code=401, detail="Invalid token")

        registry: TicketRegistry[str] = app.state.turn_tickets
        ticket = registry.get(turn_id)
        if ticket is None:
            raise HTTPException(status_code=404, detail=f"unknown turn {turn_id!r}")
        try:
            done, outcome = await registry.wait(ticket, wait_s)
        except Exception:
            log.exception("persona_gateway_invite_ticket_crashed", turn_id=turn_id, channel_id=ticket.label)
            registry.drop(turn_id)
            return InviteResponse(status="failed", channel_id=ticket.label, turn_id=turn_id)
        if not done:
            return InviteResponse(status="running", channel_id=ticket.label, turn_id=turn_id)
        registry.drop(turn_id)
        log.info(
            "persona_gateway_invite_awaited", turn_id=turn_id, channel_id=ticket.label, outcome=outcome, ticketed=True
        )
        return InviteResponse(status=str(outcome), channel_id=ticket.label, turn_id=turn_id)

    return app
