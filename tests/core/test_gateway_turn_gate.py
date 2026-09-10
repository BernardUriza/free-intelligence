"""El gate de recepción: tras SIGTERM no entra trabajo nuevo, y lo vivo aterriza.

Por qué existe (backlog `graceful-turn-drain-on-deploy`, paso 3): un rolling
update manda SIGTERM y hoy la réplica vieja sigue recibiendo hasta que la
plataforma la mata a media pipeline. La cura obvia —subir el grace period— es la
que NO se puede aplicar sola: una réplica vieja que sigue RECIBIENDO mientras la
nueva ya conectó son dos bots con el mismo token, y el humano ve cada respuesta
dos veces. El gate es el prerequisito.

Las tres propiedades que este arnés fija, y ninguna es opcional:

1. **Positiva** — tras el SIGTERM, un turno NUEVO no arranca (ni por @mención ni
   por `/invite`).
2. **Resistencia** — un turno YA EN VUELO se deja terminar y su respuesta se
   entrega. Un gate que mata turnos vivos es PEOR que el bug que arregla: hoy se
   pierde el turno del que llegó tarde, ahí se perdería el del que ya estaba
   siendo atendido.
3. **El tope duro cierra igual** cuando el drenaje no alcanza — y el abandono
   queda CONTADO en un evento estructurado. Un abandono silencioso es peor que
   uno contado.

Los tres se verificaron en rojo saboteando el fix antes de darlos por buenos.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from persona_gateway.app import ShutdownController
from persona_gateway.boot import GatewayBootState
from persona_gateway.drain import TurnGate
from persona_gateway.gateway import PersonaClient
from shared.personas import Persona

CHANNEL_ID = "1489180895264116736"


def _client(gate: TurnGate) -> PersonaClient:
    persona = Persona(
        persona_id="insult",
        display_name="Insult",
        persona_file="insult.md",
        token_env="DISCORD_TOKEN",
    )
    memory = MagicMock()
    memory.store = AsyncMock()
    memory.get_recent = AsyncMock(return_value=[])
    agent_client = MagicMock()
    agent_client.chat = AsyncMock(return_value=SimpleNamespace(text="ok", model_used="claude"))
    return PersonaClient(persona, memory, agent_client, intents=discord.Intents.none(), gate=gate)


def _message():
    message = MagicMock(spec=discord.Message)
    message.channel = MagicMock(spec=discord.TextChannel)
    message.channel.id = int(CHANNEL_ID)
    message.channel.send = AsyncMock()
    message.add_reaction = AsyncMock()
    return message


async def _invite(client: PersonaClient, **overrides) -> str:
    return await client.dispatch_invite(
        channel_id=CHANNEL_ID,
        guild_id="G1",
        channel_name="general",
        reason="bernard2389: «explícame lo del extractor»",
        invited_by="host",
        **overrides,
    )


# --- 1. positiva: tras el SIGTERM no se acepta un turno nuevo -----------------


async def test_after_sigterm_a_new_mention_turn_never_starts():
    gate = TurnGate()
    client = _client(gate)
    message = _message()

    gate.close()  # lo que hace el handler de SIGTERM

    with patch.object(PersonaClient, "_handle", new=AsyncMock()) as handle:
        await client._dispatch(message)

    handle.assert_not_awaited()
    # Y no se le manda "…" a nadie: el turno no falló, esta réplica ya no recibe.
    message.channel.send.assert_not_awaited()


async def test_after_sigterm_a_new_invite_turn_never_starts():
    gate = TurnGate()
    client = _client(gate)

    gate.close()

    with (
        patch.object(PersonaClient, "respond_to_invite", new=AsyncMock()) as respond,
        patch("persona_gateway.gateway.resolve_messageable", new=AsyncMock()) as resolve,
    ):
        outcome = await _invite(client)

    respond.assert_not_awaited()
    resolve.assert_not_awaited()  # ni siquiera se toca Discord
    # El host lee "failed", reintenta una vez, y ese retry cae en la réplica nueva.
    assert outcome == "failed"


async def test_the_gate_is_shared_across_personas():
    """Un solo SIGTERM cierra la recepción de TODAS las personas del proceso —
    el gateway hostea N bots en un proceso y la señal llega una sola vez."""
    gate = TurnGate()
    insult, vultur = _client(gate), _client(gate)
    gate.close()
    with patch.object(PersonaClient, "respond_to_invite", new=AsyncMock()) as respond:
        assert await _invite(insult) == "failed"
        assert await _invite(vultur) == "failed"
    respond.assert_not_awaited()


# --- 2. resistencia: un turno EN VUELO se deja terminar y entregar ------------


async def test_an_inflight_turn_survives_the_whole_shutdown_and_delivers():
    """El caso que hace que valga la pena: llega el SIGTERM con un turno adentro,
    y ese turno termina y ENTREGA antes de que se cierre nada. Si esto se pone
    rojo, el gate es PEOR que el bug — hoy se pierde el turno del que llegó
    tarde; ahí se perdería el del que ya estaba siendo atendido."""
    gate = TurnGate()
    client = _client(gate)
    started = asyncio.Event()
    let_it_finish = asyncio.Event()
    delivered: list[str] = []
    closed = AsyncMock()

    async def slow_turn(**_kwargs):
        started.set()
        await let_it_finish.wait()
        delivered.append("la respuesta del humano")
        return True

    server = SimpleNamespace(should_exit=False)
    controller = ShutdownController(gate, {"insult": client}, timeout_s=5.0)
    controller.server = server

    with (
        patch.object(PersonaClient, "respond_to_invite", new=AsyncMock(side_effect=slow_turn)),
        patch.object(PersonaClient, "close", new=closed),
    ):
        turn = asyncio.create_task(_invite(client))
        await started.wait()  # el turno YA está en vuelo

        shutdown = asyncio.create_task(controller.run())  # SIGTERM aquí
        await asyncio.sleep(0.05)  # tiempo de sobra para que el drenaje corte, si cortara

        assert gate.accepting is False  # ya no entra nadie nuevo…
        assert gate.inflight == 1  # …pero el de adentro sigue vivo
        closed.assert_not_awaited()  # su sesión de Discord NO se cerró debajo
        assert server.should_exit is False  # ni uvicorn se fue
        assert delivered == []

        let_it_finish.set()
        outcome = await turn
        await shutdown

    assert delivered == ["la respuesta del humano"]  # el humano SÍ vio su respuesta
    assert outcome == "delivered"
    closed.assert_awaited_once()  # y el cierre ocurrió DESPUÉS
    assert server.should_exit is True


async def test_a_mention_turn_in_flight_is_not_cut_by_the_drain():
    gate = TurnGate()
    client = _client(gate)
    started = asyncio.Event()
    let_it_finish = asyncio.Event()
    finished: list[bool] = []

    async def slow_handle(_message):
        started.set()
        await let_it_finish.wait()
        finished.append(True)

    with patch.object(PersonaClient, "_handle", new=AsyncMock(side_effect=slow_handle)):
        turn = asyncio.create_task(client._dispatch(_message()))
        await started.wait()
        drain = asyncio.create_task(gate.drain(timeout_s=5.0))
        await asyncio.sleep(0)
        let_it_finish.set()
        abandoned = await drain
        await turn

    assert abandoned == []
    assert finished == [True]


async def test_a_turn_that_raises_still_releases_its_ticket():
    """Resistencia del ledger: si un turno explota y no devuelve la ficha, el
    drenaje espera el tope entero por un fantasma en CADA deploy."""
    gate = TurnGate()
    client = _client(gate)
    with (
        patch.object(PersonaClient, "respond_to_invite", new=AsyncMock(side_effect=RuntimeError("boom"))),
        patch("persona_gateway.gateway.resolve_messageable", new=AsyncMock(return_value=None)),
    ):
        assert await _invite(client) == "failed"
    assert gate.inflight == 0
    assert await gate.drain(timeout_s=0.01) == []


# --- 3. el tope duro cierra igual, y cuenta a los abandonados ------------------


async def test_the_hard_timeout_closes_even_with_live_turns_and_counts_them():
    gate = TurnGate()
    gate.admit("insult:invite")
    gate.admit("vultur:mention")

    abandoned = await gate.drain(timeout_s=0.05)

    assert abandoned == ["insult:invite", "vultur:mention"]  # contados, no tragados


async def test_the_controller_logs_the_abandonment_and_closes_anyway():
    """El evento estructurado es el entregable de esta rama tanto como el gate:
    sin `persona_gateway_drain_abandoned` nadie puede saber que un deploy se
    comió turnos."""
    gate = TurnGate()
    gate.admit("insult:invite")
    persona = MagicMock()
    persona.close = AsyncMock()
    server = SimpleNamespace(should_exit=False)
    boot = GatewayBootState()

    controller = ShutdownController(gate, {"insult": persona}, timeout_s=0.05, boot=boot)
    controller.server = server

    with patch("persona_gateway.app.log") as log:
        await controller.run()

    events = {call.args[0] for call in log.error.call_args_list}
    assert "persona_gateway_drain_abandoned" in events
    abandoned_call = next(c for c in log.error.call_args_list if c.args[0] == "persona_gateway_drain_abandoned")
    assert abandoned_call.kwargs["abandoned"] == 1
    assert abandoned_call.kwargs["turns"] == ["insult:invite"]

    # Y se cierra IGUAL: la promesa de drenar no puede volverse un cuelgue.
    assert server.should_exit is True
    persona.close.assert_awaited_once()
    assert boot.stopping is True


async def test_a_drain_that_crashes_still_closes_the_process():
    """Fail-safe: la falla que este objeto previene (turnos cortados) es más
    barata que la que podría introducir (un proceso que no cierra)."""
    gate = MagicMock()
    gate.inflight = 0
    gate.inflight_labels = []
    gate.drain = AsyncMock(side_effect=RuntimeError("el ledger explotó"))
    persona = MagicMock()
    persona.close = AsyncMock()
    server = SimpleNamespace(should_exit=False)

    controller = ShutdownController(gate, {"insult": persona}, timeout_s=0.05)
    controller.server = server

    await controller.run()  # no propaga

    assert server.should_exit is True
    persona.close.assert_awaited_once()


async def test_one_personas_close_failure_does_not_orphan_its_siblings():
    gate = TurnGate()
    dead = MagicMock()
    dead.close = AsyncMock(side_effect=RuntimeError("websocket ya muerto"))
    alive = MagicMock()
    alive.close = AsyncMock()

    controller = ShutdownController(gate, {"insult": dead, "vultur": alive}, timeout_s=0.01)
    await controller.run()

    alive.close.assert_awaited_once()


# --- el ledger, en aislamiento ------------------------------------------------


def test_an_open_gate_admits_and_a_closed_one_refuses():
    gate = TurnGate()
    ticket = gate.admit("insult:mention")
    assert ticket is not None
    assert gate.inflight == 1
    gate.release(ticket)
    assert gate.inflight == 0

    gate.close()
    assert gate.admit("insult:mention") is None
    assert gate.inflight == 0


def test_release_is_idempotent_and_tolerates_none():
    gate = TurnGate()
    ticket = gate.admit("insult:invite")
    gate.release(ticket)
    gate.release(ticket)  # doble release no desbalancea el ledger
    gate.release(None)
    assert gate.inflight == 0


async def test_draining_an_idle_gateway_returns_immediately():
    gate = TurnGate()
    assert await gate.drain(timeout_s=30.0) == []  # no espera el tope
    assert gate.accepting is False


@pytest.mark.parametrize("sig_name", ["SIGTERM", "SIGINT"])
async def test_the_signal_schedules_the_drain_exactly_once(sig_name):
    import signal

    gate = TurnGate()
    controller = ShutdownController(gate, {}, timeout_s=0.01)
    sig = getattr(signal, sig_name)

    controller(sig)
    assert controller.started is True
    first = controller._task

    # Se parchan las DOS: el proceso de pytest no debe quedarse sin sus propios
    # handlers sólo porque este test ejercitó el camino de "mátalo ya".
    with (
        patch("persona_gateway.app.signal.signal") as set_handler,
        patch("persona_gateway.app.signal.raise_signal") as raise_signal,
    ):
        controller(sig)  # una segunda señal fuerza el cierre, no un segundo drenaje
    assert controller._task is first
    set_handler.assert_called_once_with(sig, signal.SIG_DFL)
    raise_signal.assert_called_once_with(sig)

    await first
