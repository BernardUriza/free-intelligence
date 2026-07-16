"""ReflectionWorker — gustos auto-seleccionados permanentes (slice 4).

Mutator rule: positivo (pase due con material → judge corre, facts se guardan
con provenance=self_declared, el gate avanza) + resistencia (gate no vencido /
material flaco / judge caído / sin judge client → nada se escribe y el gate
solo avanza cuando el juicio REALMENTE corrió).
"""

from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from persona_gateway.config import CONFIG
from persona_gateway.workers.reflection import ReflectionWorker
from shared.personas import Persona


def _persona() -> Persona:
    return Persona(
        persona_id="vultur",
        display_name="Vultur Analytica",
        persona_file="vultur.md",
        token_env="VULTUR_DISCORD_TOKEN",
    )


def _memory(*, last_reflected: float | None, turns: int) -> MagicMock:
    memory = MagicMock()
    memory.get_last_reflected_at = AsyncMock(return_value=last_reflected)
    memory.recent_assistant_turns = AsyncMock(
        return_value=[{"channel_id": "C1", "content": f"turno {i}", "timestamp": 1.0} for i in range(turns)]
    )
    memory.get_agent_self_facts = AsyncMock(return_value=[])
    memory.add_agent_self_fact = AsyncMock(return_value=7)
    memory.mark_reflected = AsyncMock()
    return memory


async def test_due_pass_stores_self_declared_facts_and_advances_gate():
    """Un pase vencido con material suficiente guarda los gustos del juez con
    provenance=self_declared y avanza el gate durable."""
    memory = _memory(last_reflected=None, turns=CONFIG.reflection_min_turns)
    worker = ReflectionWorker(_persona(), memory)
    judged = [{"fact": "Considera a Lynch el estándar de densidad honesta", "category": "gustos"}]
    with patch(
        "persona_gateway.workers.reflection.reflect_self_facts",
        new=AsyncMock(return_value=judged),
    ) as mock_reflect:
        await worker.drain(judge_client=MagicMock())
    mock_reflect.assert_awaited_once()
    memory.add_agent_self_fact.assert_awaited_once_with("vultur", judged[0]["fact"], "gustos", "self_declared")
    memory.mark_reflected.assert_awaited_once()


async def test_zero_survivors_still_advances_gate_but_writes_nothing():
    """Cero hechos es un veredicto válido: el gate avanza (el juicio corrió),
    ningún fact se escribe."""
    memory = _memory(last_reflected=None, turns=CONFIG.reflection_min_turns)
    worker = ReflectionWorker(_persona(), memory)
    with patch(
        "persona_gateway.workers.reflection.reflect_self_facts",
        new=AsyncMock(return_value=[]),
    ):
        await worker.drain(judge_client=MagicMock())
    memory.add_agent_self_fact.assert_not_awaited()
    memory.mark_reflected.assert_awaited_once()


async def test_gate_not_due_skips_judge_entirely():
    """RESISTENCIA: reflexión reciente → ni judge ni escrituras ni gate."""
    memory = _memory(last_reflected=time.time(), turns=CONFIG.reflection_min_turns)
    worker = ReflectionWorker(_persona(), memory)
    with patch("persona_gateway.workers.reflection.reflect_self_facts", new=AsyncMock()) as mock_reflect:
        await worker.drain(judge_client=MagicMock())
    mock_reflect.assert_not_awaited()
    memory.mark_reflected.assert_not_awaited()


async def test_thin_material_does_not_burn_the_gate():
    """RESISTENCIA: una persona callada no gasta su pase semanal en material
    flaco — el gate queda intacto para cuando haya vivido algo."""
    memory = _memory(last_reflected=None, turns=CONFIG.reflection_min_turns - 1)
    worker = ReflectionWorker(_persona(), memory)
    with patch("persona_gateway.workers.reflection.reflect_self_facts", new=AsyncMock()) as mock_reflect:
        await worker.drain(judge_client=MagicMock())
    mock_reflect.assert_not_awaited()
    memory.mark_reflected.assert_not_awaited()


async def test_judge_failure_leaves_gate_untouched_for_retry():
    """RESISTENCIA: falla de transporte → sin gate, sin facts; reintenta al
    siguiente drain."""
    memory = _memory(last_reflected=None, turns=CONFIG.reflection_min_turns)
    worker = ReflectionWorker(_persona(), memory)
    with patch(
        "persona_gateway.workers.reflection.reflect_self_facts",
        new=AsyncMock(side_effect=RuntimeError("runner caído")),
    ):
        await worker.drain(judge_client=MagicMock())
    memory.add_agent_self_fact.assert_not_awaited()
    memory.mark_reflected.assert_not_awaited()


async def test_no_judge_client_is_a_noop():
    """RESISTENCIA: judge_client=None (leído en vivo) apaga la reflexión sin
    tocar la base."""
    memory = _memory(last_reflected=None, turns=CONFIG.reflection_min_turns)
    worker = ReflectionWorker(_persona(), memory)
    await worker.drain(judge_client=None)
    memory.get_last_reflected_at.assert_not_awaited()


def test_parse_reflection_survives_garbage_and_caps():
    """El parser regresa [] ante basura y respeta max_facts."""
    from khimeras_shared.self_reflection import parse_reflection

    assert parse_reflection("no soy json", 3) == []
    assert parse_reflection('{"fact": "dict, no lista"}', 3) == []
    many = '[{"fact": "a", "category": "gustos"}, {"fact": "b"}, {"fact": "c"}, {"fact": "d"}]'
    parsed = parse_reflection(many, 2)
    assert len(parsed) == 2
    assert parsed[1] == {"fact": "b", "category": "general"}


def test_reflection_material_lists_existing_and_turns():
    """El material del juez incluye los facts existentes y los turnos vividos."""
    from khimeras_shared.self_reflection import build_reflection_material

    material = build_reflection_material(
        [{"category": "gustos", "fact": "Ama el cine lento"}],
        [{"content": "El plano secuencia es un fetiche cuando no narra"}],
    )
    assert "Ama el cine lento" in material
    assert "fetiche" in material


def test_reflection_judge_response_shape():
    """El motor consume utility_call y parsea la respuesta del juez (loop real
    con SimpleNamespace, sin red)."""
    import asyncio

    from khimeras_shared.self_reflection import reflect_self_facts

    judge = MagicMock()
    judge.utility_call = AsyncMock(
        return_value=SimpleNamespace(text='[{"fact": "Prefiere el silencio al score", "category": "gustos"}]')
    )
    loop = asyncio.new_event_loop()
    try:
        facts = loop.run_until_complete(
            reflect_self_facts(judge, "Vultur Analytica", [], [{"content": "x" * 10}], max_facts=3)
        )
    finally:
        loop.close()
    assert facts == [{"fact": "Prefiere el silencio al score", "category": "gustos"}]
    system_prompt = judge.utility_call.await_args.args[0]
    assert "Vultur Analytica" in system_prompt
    assert "{persona_name}" not in system_prompt
