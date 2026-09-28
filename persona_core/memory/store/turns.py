"""Invite-turns facade — la fila del boleto del gateway, expuesta al TurnRunner."""

from __future__ import annotations

from typing import Any

from persona_core.memory.repositories import InviteTurnsRepository


class InviteTurnsFacade:
    _invite_turns: InviteTurnsRepository

    @property
    def invite_turn_ledger(self) -> InviteTurnsRepository:
        """El repositorio implementa `TicketLedger`; el registro lo consume directo."""
        return self._invite_turns

    async def advance_invite_turn(
        self, turn_id: str, stage: str, *, text: str | None = None, tail: dict[str, Any] | None = None
    ) -> bool | None:
        return await self._invite_turns.advance_stage(turn_id, stage, text=text, tail=tail)

    async def mark_invite_turn_delivered(
        self, turn_id: str, message_ids: list[int], *, partial: bool = False
    ) -> bool | None:
        return await self._invite_turns.mark_delivered(turn_id, message_ids, partial=partial)

    async def stale_invite_turn_ids(self, *, stale_s: float, max_attempts: int, limit: int) -> list[str] | None:
        return await self._invite_turns.stale_ids(stale_s=stale_s, max_attempts=max_attempts, limit=limit)
