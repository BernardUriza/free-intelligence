"""Raise (or lower) one invited key's ceiling without re-minting it (backlog #51).

An invitation is minted at the global default and the only way to change that
number used to be approving the nickname again — which hands out a NEW key and
wipes its spend history. A ceiling is the owner's decision about the owner's
money, so this route answers to exactly one credential: AIRE_AUTH_TOKEN,
Bernard's own. The front's canary, the runner, the pulse and the gatekeeper are
door tokens; none of them may resize what a door token can spend. The spend
stays as it is: only the limit moves.
"""

from __future__ import annotations

import hmac
import math
import os

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from . import bearer, db, tokens

router = APIRouter(prefix="/access")


def _is_owner(presented: str) -> bool:
    owner = os.environ.get("AIRE_AUTH_TOKEN", "")
    if not owner:
        return False
    return hmac.compare_digest(presented.encode("utf-8"), owner.encode("utf-8"))


def _budget(raw: object) -> float | None:
    try:
        value = float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) and value > 0 else None


async def _move(nickname: str, budget_usd: float) -> tokens.Holder | None:
    async with db.acquire() as conn:
        await conn.execute(tokens.DDL)
        row = await conn.fetchrow(
            "UPDATE aire_token SET budget_usd = $2 WHERE nickname = $1 AND revoked_at IS NULL "
            "RETURNING nickname, budget_usd, spent_usd",
            nickname, budget_usd,
        )
    if row is None:
        return None
    await tokens.load()
    return tokens.Holder(row["nickname"], float(row["budget_usd"]), float(row["spent_usd"]))


@router.post("/ceiling")
async def set_ceiling(request: Request) -> JSONResponse:
    if not _is_owner(bearer.presented_token(request)):
        return JSONResponse({"detail": "the ceiling answers to the owner only"}, status_code=401)
    body = await request.json()
    nickname = str(body.get("nickname", "")).strip()[:80]
    budget = _budget(body.get("budget_usd"))
    if not nickname or budget is None:
        return JSONResponse({"detail": "a nickname and a positive budget_usd are required"},
                            status_code=400)
    holder = await _move(nickname, budget)
    if holder is None:
        return JSONResponse({"detail": f"no live key for {nickname!r}"}, status_code=404)
    return JSONResponse({"nickname": holder.nickname, "budget_usd": holder.budget_usd,
                         "spent_usd": holder.spent_usd})
