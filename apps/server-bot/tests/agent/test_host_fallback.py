"""The host owns the failure of the turns it routes (2026-09-03).

Positive: a turn that fails once is retried with the same persona; a turn that
fails twice makes the HOST post a notice naming who went quiet. Resistance: a
delivered turn is never retried; an "empty" turn (reactions-only) is a choice,
not a fault, so it is never retried either; a fallback that cannot be posted
never raises out of the background task.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

from demux_ai import fallback
from demux_ai.fallback import deliver_or_fallback

KW = {"channel_id": "1489180895264116736", "guild_id": "G", "channel_name": "general", "persona_id": "insult"}


async def test_delivered_first_try_no_retry_no_notice():
    summon = AsyncMock(return_value="delivered")
    say = AsyncMock()
    outcome = await deliver_or_fallback({"reason": "r"}, say=say, summon=summon, invited_by="host", **KW)
    assert outcome == "delivered"
    summon.assert_awaited_once()
    say.assert_not_awaited()


async def test_empty_turn_is_a_choice_not_a_fault():
    summon = AsyncMock(return_value="empty")
    say = AsyncMock()
    outcome = await deliver_or_fallback({"reason": "r"}, say=say, summon=summon, **KW)
    assert outcome == "empty"
    summon.assert_awaited_once()
    say.assert_not_awaited()


async def test_failed_then_delivered_retries_once_with_the_same_persona():
    summon = AsyncMock(side_effect=["failed", "delivered"])
    say = AsyncMock()
    outcome = await deliver_or_fallback({"reason": "r"}, say=say, summon=summon, invited_by="host", **KW)
    assert outcome == "delivered"
    assert summon.await_count == 2
    first, second = summon.await_args_list
    assert first.kwargs["persona_id"] == second.kwargs["persona_id"] == "insult"
    assert first.kwargs["invited_by"] == "host"
    assert second.kwargs["invited_by"] == fallback.RETRY_INVITED_BY
    say.assert_not_awaited()


async def test_failed_twice_the_host_speaks_naming_the_persona():
    summon = AsyncMock(side_effect=["failed", "unreachable"])
    say = AsyncMock()
    outcome = await deliver_or_fallback({"reason": "r"}, say=say, summon=summon, **KW)
    assert outcome == "unreachable"
    assert summon.await_count == 2
    say.assert_awaited_once()
    channel_id, text = say.await_args.args
    assert channel_id == KW["channel_id"]
    assert "Insult" in text
    assert "…" not in text


async def test_notice_that_cannot_be_posted_never_raises():
    summon = AsyncMock(return_value="failed")
    say = AsyncMock(side_effect=RuntimeError("403"))
    outcome = await deliver_or_fallback({"reason": "r"}, say=say, summon=summon, **KW)
    assert outcome == "failed"


def test_unknown_persona_still_gets_a_label():
    assert fallback.persona_label("nobody") == "nobody"
    assert fallback.persona_label(None) == "La persona"


# --- el boleto del host (2026-09-23) ---------------------------------------------


async def test_both_attempts_carry_a_turn_id_and_unreachable_reuses_it():
    """Un gateway que se reinició no sabe qué pasó: el reintento lleva el MISMO id
    para que su ledger conteste lo que ya entregó en vez de correr otro turno."""
    summon = AsyncMock(side_effect=["unreachable", "delivered"])
    say = AsyncMock()
    outcome = await deliver_or_fallback({"reason": "r"}, say=say, summon=summon, **KW)
    assert outcome == "delivered"
    first, second = summon.await_args_list
    assert first.kwargs["turn_id"] and first.kwargs["turn_id"] == second.kwargs["turn_id"]
    say.assert_not_awaited()


async def test_a_declared_failure_retries_under_a_fresh_turn_id():
    summon = AsyncMock(side_effect=["failed", "delivered"])
    say = AsyncMock()
    await deliver_or_fallback({"reason": "r"}, say=say, summon=summon, **KW)
    first, second = summon.await_args_list
    assert first.kwargs["turn_id"] and second.kwargs["turn_id"]
    assert first.kwargs["turn_id"] != second.kwargs["turn_id"]


async def test_uncertain_is_neither_retried_nor_covered_by_the_house():
    summon = AsyncMock(return_value="uncertain")
    say = AsyncMock()
    outcome = await deliver_or_fallback({"reason": "r"}, say=say, summon=summon, **KW)
    assert outcome == "uncertain"
    summon.assert_awaited_once()
    say.assert_not_awaited()


async def test_uncertain_on_the_retry_stops_without_the_notice():
    summon = AsyncMock(side_effect=["failed", "uncertain"])
    say = AsyncMock()
    outcome = await deliver_or_fallback({"reason": "r"}, say=say, summon=summon, **KW)
    assert outcome == "uncertain"
    assert summon.await_count == 2
    say.assert_not_awaited()


# --- El double-dispatch del rollover: el turn_id del PRIMER intento es
# determinístico por (trigger, persona, channel), no aleatorio, para que dos
# réplicas del host colapsen en un turno (bug 2026-07-20). ---

KW_TRIGGER = {**KW, "trigger_message_id": "999888777"}


async def test_two_replicas_same_trigger_and_persona_mint_the_same_first_id():
    # Dos invocaciones independientes (dos réplicas del host en el rollover) con
    # el MISMO trigger+persona deben acuñar el MISMO turn_id → el ticket durable
    # del gateway las dedupea.
    summon_a = AsyncMock(return_value="delivered")
    summon_b = AsyncMock(return_value="delivered")
    say = AsyncMock()
    await deliver_or_fallback({"reason": "r"}, say=say, summon=summon_a, invited_by="host", **KW_TRIGGER)
    await deliver_or_fallback({"reason": "r"}, say=say, summon=summon_b, invited_by="host", **KW_TRIGGER)
    assert summon_a.await_args.kwargs["turn_id"] == summon_b.await_args.kwargs["turn_id"]


async def test_fanout_same_trigger_different_persona_stays_distinct():
    # El MISMO mensaje que menciona a dos personas NO se debe dedupear: cada
    # persona responde. El persona_id entra en el seed.
    summon_i = AsyncMock(return_value="delivered")
    summon_v = AsyncMock(return_value="delivered")
    say = AsyncMock()
    await deliver_or_fallback({"reason": "r"}, say=say, summon=summon_i, **{**KW_TRIGGER, "persona_id": "insult"})
    await deliver_or_fallback({"reason": "r"}, say=say, summon=summon_v, **{**KW_TRIGGER, "persona_id": "vultur"})
    assert summon_i.await_args.kwargs["turn_id"] != summon_v.await_args.kwargs["turn_id"]


async def test_no_trigger_falls_back_to_a_unique_id():
    # Un turno sin mensaje disparador (proactivo) no tiene qué dedupear → uuid4,
    # distinto en cada invocación.
    summon_a = AsyncMock(return_value="delivered")
    summon_b = AsyncMock(return_value="delivered")
    say = AsyncMock()
    await deliver_or_fallback({"reason": "r"}, say=say, summon=summon_a, **KW)  # KW no trae trigger
    await deliver_or_fallback({"reason": "r"}, say=say, summon=summon_b, **KW)
    assert summon_a.await_args.kwargs["turn_id"] != summon_b.await_args.kwargs["turn_id"]


async def test_declared_failure_retries_fresh_even_with_a_trigger():
    # Con trigger, el PRIMER id es determinístico; un `failed` declarado debe
    # reintentar con un id NUEVO (no el determinístico) para que el segundo
    # intento legítimo corra y no se dedupee contra el primero.
    summon = AsyncMock(side_effect=["failed", "delivered"])
    say = AsyncMock()
    await deliver_or_fallback({"reason": "r"}, say=say, summon=summon, **KW_TRIGGER)
    first, second = summon.await_args_list
    assert first.kwargs["turn_id"] != second.kwargs["turn_id"]
