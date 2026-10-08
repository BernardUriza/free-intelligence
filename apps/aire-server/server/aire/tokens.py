"""Per-nickname keys, with a spend ceiling each (backlog #32 slice d, and #28).

Until now the door knew exactly two secrets, both constants in the environment:
Bernard's and the front's canary. An approved stranger needed a third kind — one
key per person, revocable alone, and CAPPED alone. #28 is the reason the cap is
not optional: a leaked invitation with no ceiling of its own can burn the whole
global budget before anyone notices.

**Only the hash is stored.** A database backup, a `SELECT` from the console, or a
stolen read credential yields nothing usable — the plaintext exists once, in the
mail to Bernard, and never again. Lookup is by hash, so the comparison is over a
digest, never over the secret.

The cache is the `aire_device` pattern exactly (Art. 6): loaded at startup, kept
in lockstep with this module's own writes, never polled per request. Reading it is
the same kind of read the roster already is — it gates writes, it renders nothing
([[write-only-daemon]]).
"""

from __future__ import annotations

import hashlib
import os
import secrets
from dataclasses import dataclass
from typing import Any

from . import db, pricing, spend

DDL = (
    "CREATE TABLE IF NOT EXISTS aire_token ("
    "nickname text PRIMARY KEY, token_hash text UNIQUE NOT NULL, "
    "budget_usd double precision NOT NULL DEFAULT 1.0, "
    "spent_usd double precision NOT NULL DEFAULT 0, "
    "created_at timestamptz NOT NULL DEFAULT now(), revoked_at timestamptz);"
)
DEFAULT_BUDGET_USD = float(os.environ.get("AIRE_INVITE_BUDGET_USD", "1.0"))


@dataclass
class Holder:
    nickname: str
    budget_usd: float
    spent_usd: float

    def exhausted(self) -> bool:
        return self.spent_usd >= self.budget_usd


_by_hash: dict[str, Holder] = {}


def digest(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


async def load() -> None:
    """Every live key, at startup. A revoked one is simply absent from the cache."""
    async with db.acquire() as conn:
        await conn.execute(DDL)  # as role `aire`, so the console's reader can see it
        rows = await conn.fetch(
            "SELECT nickname, token_hash, budget_usd, spent_usd FROM aire_token "
            "WHERE revoked_at IS NULL"
        )
    _by_hash.clear()
    for row in rows:
        _by_hash[row["token_hash"]] = Holder(
            row["nickname"], float(row["budget_usd"]), float(row["spent_usd"])
        )


def identify(presented: str) -> Holder | None:
    return _by_hash.get(digest(presented)) if presented else None


async def mint(nickname: str, budget_usd: float = DEFAULT_BUDGET_USD) -> str:
    """A new key for a nickname, replacing any previous one — approving twice
    hands out one working key, never two. The plaintext is returned once."""
    plaintext = f"aire_{secrets.token_urlsafe(32)}"
    async with db.acquire() as conn:
        await conn.execute(DDL)
        await conn.execute(
            "INSERT INTO aire_token (nickname, token_hash, budget_usd) VALUES ($1, $2, $3) "
            "ON CONFLICT (nickname) DO UPDATE SET token_hash = EXCLUDED.token_hash, "
            "budget_usd = EXCLUDED.budget_usd, spent_usd = 0, revoked_at = NULL",
            nickname, digest(plaintext), budget_usd,
        )
    await load()
    return plaintext


def biller(holder: Holder | None) -> Any:
    """How an identified gateway turn pays against its key's ceiling — a lent
    credential (#32) and a metered pass-through (#34) bank the same way, at the
    same list prices. A real turn that prices at $0 is PRINTED, never swallowed:
    that is a ceiling not biting, and it stayed invisible once."""
    if holder is None:
        return None

    async def bank(usage: dict[str, Any] | None, model: str) -> None:
        cost = pricing.usd(usage, model)
        if cost <= 0:
            print(f"KEY {holder.nickname}: a relayed turn banked $0 "
                  f"(model={model!r}) — the ceiling is not biting", flush=True)
        # The key's ceiling first, the daemon's month second, and the order is a
        # choice: they are two different questions — `aire_token.spent_usd`
        # answers "has this invitation spent its allowance", `aire_spend` answers
        # "what did AIRE spend" — and if the database is failing, exactly one of
        # them can be recorded. The ceiling wins because it GATES the next turn
        # while the month only reports on turns already taken.
        await charge(holder.nickname, cost)
        await spend.bank("gateway", None, None, holder.nickname, cost)

    return bank


async def charge(nickname: str, usd: float) -> None:
    """Bank what a turn cost against its own key. The cache is updated in the same
    breath, so the very next request already sees the new total."""
    if usd <= 0:
        return
    async with db.acquire() as conn:
        await conn.execute(
            "UPDATE aire_token SET spent_usd = spent_usd + $2 WHERE nickname = $1", nickname, usd
        )
    for holder in _by_hash.values():
        if holder.nickname == nickname:
            holder.spent_usd += usd


async def revoke(nickname: str) -> bool:
    async with db.acquire() as conn:
        await conn.execute(DDL)
        result = await conn.execute(
            "UPDATE aire_token SET revoked_at = now() WHERE nickname = $1 AND revoked_at IS NULL",
            nickname,
        )
    await load()
    return result.endswith("1")
