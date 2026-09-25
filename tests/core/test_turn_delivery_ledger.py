"""La cola de entrega deja cada etapa en la fila del boleto, y reanuda por etapa.

Positiva: con `turn_id` el turno registra runner_done → markers_done → sending
→ delivered (con los ids de Discord) ANTES del store, y el assistant se guarda
con el id del primer chunk. Resistencia: sin `turn_id` no se toca ningún ledger
y el store sigue llevando el id; un ledger que falla no impide ni el store ni el
`True`; una reanudación desde `runner_done` NO vuelve a llamar al runner; desde
`markers_done` tampoco enruta marcadores; y una fila en `sending` produce
`uncertain` sin un solo `send`.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from khimeras_shared.tickets import LedgerRow
from persona_gateway.gateway import PersonaClient
from shared.personas import Persona


class _Typing:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _client(reply_text: str, calls: list[str]) -> PersonaClient:
    persona = Persona(persona_id="insult", display_name="Insult", persona_file="insult.md", token_env="DISCORD_TOKEN")
    memory = MagicMock()

    async def _store(*_a, **_k):
        calls.append("store")

    async def _advance(turn_id, stage, *, text=None, tail=None):
        calls.append(f"stage:{stage}")

    async def _delivered(turn_id, ids, *, partial=False):
        calls.append(f"delivered:{ids}:{partial}")

    memory.store = AsyncMock(side_effect=_store)
    memory.get_recent = AsyncMock(return_value=[])
    memory.advance_invite_turn = AsyncMock(side_effect=_advance)
    memory.mark_invite_turn_delivered = AsyncMock(side_effect=_delivered)
    agent_client = MagicMock()
    agent_client.chat = AsyncMock(return_value=SimpleNamespace(text=reply_text, model_used="claude"))
    client = PersonaClient(persona, memory, agent_client, intents=discord.Intents.none())
    client._turns._markers.route = AsyncMock(side_effect=lambda text, **_k: text)
    return client


def _channel(ids=(11, 12)):
    channel = MagicMock(spec=discord.TextChannel)
    channel.send = AsyncMock(side_effect=[MagicMock(id=i) for i in ids] + [MagicMock(id=99)] * 5)
    channel.typing = MagicMock(return_value=_Typing())
    return channel


async def _run(client: PersonaClient, channel, **kw) -> bool:
    return await client._turns.run_and_deliver(
        channel=channel,
        channel_id="1489180895264116736",
        user_id="907264175246569543",
        guild_id="G1",
        channel_name="general",
        messages=[{"role": "user", "content": "hola"}],
        bot_user_id="1488415576551325906",
        **kw,
    )


def _row(stage: str, text: str | None = None, attempts: int = 2) -> LedgerRow:
    return LedgerRow(
        ticket_id="t1",
        status="running",
        attempts=attempts,
        payload={"channel_id": "1489180895264116736"},
        stale=True,
        extra={"stage": stage, "stage_text": text, "tail": {"user_id": "907264175246569543", "model_used": "claude"}},
    )


@pytest.mark.asyncio
async def test_every_stage_is_recorded_and_delivery_lands_before_the_store():
    calls: list[str] = []
    client = _client("Ya llegó, carnal.", calls)
    channel = _channel()
    assert await _run(client, channel, turn_id="t1") is True
    assert calls == ["stage:runner_done", "stage:markers_done", "stage:sending", "delivered:[11]:False", "store"]
    assert client.memory.store.await_args.kwargs["discord_message_id"] == "11"
    assert client.agent_client.chat.await_args.kwargs["job_id"] == "t1"


@pytest.mark.asyncio
async def test_without_a_turn_id_no_ledger_is_touched_but_the_store_still_carries_the_id():
    calls: list[str] = []
    client = _client("Ya llegó, carnal.", calls)
    assert await _run(client, _channel()) is True
    assert calls == ["store"]
    assert client.memory.store.await_args.kwargs["discord_message_id"] == "11"
    # Sin ledger igual nace un job_id aquí, para cruzar el turno con el runner en KQL.
    job_id = client.agent_client.chat.await_args.kwargs["job_id"]
    assert isinstance(job_id, str) and len(job_id) == 32


@pytest.mark.asyncio
async def test_a_failing_ledger_never_blocks_the_store_or_the_delivery():
    calls: list[str] = []
    client = _client("Ya llegó, carnal.", calls)
    client.memory.advance_invite_turn = AsyncMock(side_effect=RuntimeError("pg caído"))
    client.memory.mark_invite_turn_delivered = AsyncMock(side_effect=RuntimeError("pg caído"))
    assert await _run(client, _channel(), turn_id="t1") is True
    assert calls == ["store"]


@pytest.mark.asyncio
async def test_resuming_from_runner_done_never_calls_the_runner_again():
    calls: list[str] = []
    client = _client("NO DEBE USARSE", calls)
    channel = _channel()
    assert await _run(client, channel, turn_id="t1", resume_from=_row("runner_done", "texto de la fila")) is True
    client.agent_client.chat.assert_not_awaited()
    client._turns._markers.route.assert_awaited_once()
    assert channel.send.await_args_list[0].args[0].startswith("texto de la fila")
    assert calls == ["stage:markers_done", "stage:sending", "delivered:[11]:False", "store"]
    assert client.memory.store.await_args.kwargs["for_user_id"] == "907264175246569543"


@pytest.mark.asyncio
async def test_resuming_from_markers_done_never_routes_markers_again():
    calls: list[str] = []
    client = _client("NO DEBE USARSE", calls)
    channel = _channel()
    assert await _run(client, channel, turn_id="t1", resume_from=_row("markers_done", "listo para enviar")) is True
    client.agent_client.chat.assert_not_awaited()
    client._turns._markers.route.assert_not_awaited()
    assert calls == ["stage:sending", "delivered:[11]:False", "store"]


@pytest.mark.asyncio
async def test_a_row_in_sending_is_declared_uncertain_without_a_single_send():
    calls: list[str] = []
    client = _client("NO DEBE USARSE", calls)
    client.respond_to_invite = AsyncMock()
    outcome = await client.dispatch_invite(
        channel_id="1489180895264116736",
        guild_id="G1",
        channel_name="general",
        reason="ven",
        fallback=False,
        turn_id="t1",
        resume_from=_row("sending"),
    )
    assert outcome == "uncertain"
    client.respond_to_invite.assert_not_awaited()
    assert calls == ["stage:uncertain"]


@pytest.mark.asyncio
async def test_a_partial_send_is_still_a_delivery_with_the_pieces_that_landed():
    from persona_gateway.delivery import send_chunked

    channel = MagicMock(spec=discord.TextChannel)
    channel.send = AsyncMock(side_effect=[MagicMock(id=1), discord.HTTPException(MagicMock(status=500), "boom")])
    sent = await send_chunked(channel, "primera parte[SEND]segunda parte")
    assert [m.id for m in sent] == [1] and sent.partial is True

    channel.send = AsyncMock(side_effect=discord.HTTPException(MagicMock(status=500), "boom"))
    with pytest.raises(discord.HTTPException):
        await send_chunked(channel, "nada salió")
