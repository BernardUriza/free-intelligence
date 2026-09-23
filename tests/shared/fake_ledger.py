"""Un `TicketLedger` en RAM que modela la semántica de las filas: CAS al
reclamar, cierre condicionado al dueño, `stale` como el latido vencido.

Compartido por los tests del primitivo (`tests/shared/test_tickets.py`) y los
del API del runner (`tests/agent/test_turn_jobs_api.py`): un "restart" es un
registro nuevo sobre el mismo FakeLedger.
"""

from __future__ import annotations

from typing import Any

from khimeras_shared.tickets import LedgerRow


class FakeLedger:
    def __init__(self) -> None:
        self.rows: dict[str, dict[str, Any]] = {}
        self.fail = False

    def _row(self, ticket_id: str, me: str | None) -> LedgerRow:
        r = self.rows[ticket_id]
        return LedgerRow(
            ticket_id=ticket_id,
            status=r["status"],
            attempts=r["attempts"],
            payload=r["payload"],
            result=r["result"],
            error=r["error"],
            stale=r["stale"],
            owned=(me is not None and r["claimed_by"] == me),
            extra={"label": r["label"], "aire_sent": r.get("aire_sent", False)},
        )

    def age(self, ticket_id: str) -> None:
        self.rows[ticket_id]["stale"] = True

    async def open(self, ticket_id, *, label, payload, deadline_s, claimed_by):
        if self.fail:
            return None
        if ticket_id not in self.rows:
            self.rows[ticket_id] = {
                "status": "running",
                "attempts": 1,
                "payload": payload,
                "result": None,
                "error": None,
                "stale": False,
                "claimed_by": claimed_by,
                "label": label,
            }
        return self._row(ticket_id, claimed_by)

    async def get(self, ticket_id):
        if self.fail or ticket_id not in self.rows:
            return None
        return self._row(ticket_id, None)

    async def claim(self, ticket_id, *, claimed_by, stale_s, max_attempts):
        if self.fail:
            return None
        r = self.rows.get(ticket_id)
        if (
            r is None
            or r["status"] not in ("running", "queued")
            or r["claimed_by"] == claimed_by
            or not r["stale"]
            or r["attempts"] >= max_attempts
        ):
            return None
        r.update(status="running", claimed_by=claimed_by, attempts=r["attempts"] + 1, stale=False)
        return self._row(ticket_id, claimed_by)

    async def heartbeat(self, ticket_ids, *, claimed_by):
        if self.fail:
            return None
        return {
            t
            for t in ticket_ids
            if t in self.rows and self.rows[t]["claimed_by"] == claimed_by and self.rows[t]["status"] == "running"
        }

    async def finish(self, ticket_id, *, claimed_by, status, result, error):
        if self.fail:
            return None
        r = self.rows.get(ticket_id)
        if r is None:
            return False
        if claimed_by is not None and (r["claimed_by"] != claimed_by or r["status"] != "running"):
            return False
        r.update(status=status, result=result, error=error)
        return True

    async def release(self, *, claimed_by):
        if self.fail:
            return None
        n = 0
        for r in self.rows.values():
            if r["claimed_by"] == claimed_by and r["status"] == "running":
                r.update(status="queued", claimed_by=None, stale=True)
                n += 1
        return n

    async def reap(self, *, result_ttl_s):
        return 0

    async def mark_aire_sent(self, ticket_id):
        if self.fail or ticket_id not in self.rows:
            return None
        self.rows[ticket_id]["aire_sent"] = True
        return True

    async def stale_ids(self, *, stale_s, max_attempts, limit):
        if self.fail:
            return None
        return [
            t
            for t, r in self.rows.items()
            if r["status"] in ("running", "queued") and r["stale"] and r["attempts"] < max_attempts
        ][:limit]
