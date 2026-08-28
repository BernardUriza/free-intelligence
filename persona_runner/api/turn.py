"""Turn surface — every persona turn rides AIRE's engine door.

The local Claude-Agent-SDK host this module used to run (a pooled
ClaudeSDKClient per channel, history folding, the `_drain` stream
accumulator) died when the AIRE flag flipped permanent — backlog
``aire-engine-stage2.md``, deletion step. The route itself (casitas, topics,
facts pre-fetch, error mapping) lives in ``engine/aire_route.py``.
"""

from __future__ import annotations

from fastapi import APIRouter, Header

from persona_runner.core.auth import check_auth
from persona_runner.core.schemas import TurnRequest, TurnResponse
from persona_runner.engine import aire_route

router = APIRouter()


@router.post("/v1/turn", response_model=TurnResponse)
async def turn(req: TurnRequest, authorization: str | None = Header(default=None)) -> TurnResponse:
    """Run one persona turn through AIRE's engine door."""
    check_auth(authorization)
    return await aire_route.turn_via_aire(req)
