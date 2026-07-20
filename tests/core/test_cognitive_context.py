"""Las 5 mejoras cognitivas del turn context (2026-07-20) — regresiones.

1. El prefijo basura "?: " está muerto: `format_context(build_context(...))`
   doble-frameaba y cada línea de contexto llegaba al modelo como
   "?: [hace 2h] Alex: …". Un solo framer canónico: `build_context`.
2. Identidad propia: los turnos del PROPIO bot van marcados "Nombre (tú):" y
   conservan role=assistant; los de un hermano se reencuadran a user — por
   persona (`self_name`), ya no hardcodeado a Insult.
3. Los excerpts viejos viajan por el seam `relevant_memory` del wire, nunca
   dentro del hilo vivo replay (donde el runner los enmarca como
   "lo que se acaba de decir").
4. Recall semántico de facts por turno: `search_facts_semantic` cableado
   (capacidad construida-y-muerta, la clase [SEND]).
5. Stopwords españolas fuera del keyword search: "para qué era la receta"
   ya no OR-explota con "para".

Mutator rule: caso positivo + caso de resistencia por mejora.
"""

from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord

from khimeras_shared.memory.context import build_context, format_relevant_block
from khimeras_shared.memory.repositories.messages import search_terms
from persona_gateway.gateway import PersonaClient
from persona_gateway.turn_context import TurnContextBuilder
from shared.personas import Persona

NOW = time.time()


# --- 1 + 2. framer canónico: sin basura, con identidad -----------------------


def _rows() -> list[dict]:
    return [
        {"role": "user", "user_name": "Bernard", "content": "hola vultur", "timestamp": NOW - 120},
        {"role": "assistant", "user_name": "Vultur Analytica", "content": "qué quieres", "timestamp": NOW - 60},
        {"role": "assistant", "user_name": "Insult", "content": "aquí apesta", "timestamp": NOW - 30},
    ]


def test_no_junk_prefix_on_any_context_line():
    for entry in build_context(_rows(), self_name="Vultur Analytica"):
        assert not entry["content"].startswith("?: "), entry


def test_own_turns_keep_assistant_role_and_carry_tu_mark():
    ctx = build_context(_rows(), self_name="Vultur Analytica")
    own = ctx[1]
    assert own["role"] == "assistant"
    assert own["content"] == "Vultur Analytica (tú): qué quieres"


def test_sibling_bot_turns_reframe_to_user_without_tu_mark():
    ctx = build_context(_rows(), self_name="Vultur Analytica")
    sibling = ctx[2]
    assert sibling["role"] == "user"
    assert sibling["content"] == "Insult: aquí apesta"
    assert "(tú)" not in sibling["content"]


def test_human_turns_stay_untouched():
    ctx = build_context(_rows(), self_name="Vultur Analytica")
    assert ctx[0] == {"role": "user", "content": "Bernard: hola vultur"}


def test_old_rows_keep_the_relative_time_prefix():
    rows = [{"role": "user", "user_name": "Alex", "content": "jaja", "timestamp": NOW - 7200}]
    ctx = build_context(rows, self_name="Insult")
    assert ctx[0]["content"].startswith("[hace 2h] Alex:")


# --- 3. los excerpts viejos son un bloque etiquetado, deduplicado ------------


def test_relevant_block_labels_and_timestamps_excerpts():
    relevant = [{"role": "user", "user_name": "Alex", "content": "renté el depa", "timestamp": NOW - 86400 * 3}]
    block = format_relevant_block(relevant, recent=[])
    assert block is not None
    assert block.startswith("Fragmentos más viejos")
    assert "[hace 3 días] Alex: renté el depa" in block


def test_relevant_block_dedupes_rows_already_in_recent():
    row = {"role": "user", "user_name": "Alex", "content": "renté el depa", "timestamp": NOW - 86400}
    assert format_relevant_block([row], recent=[{"content": "renté el depa"}]) is None


def test_relevant_block_empty_is_none():
    assert format_relevant_block([], recent=[]) is None
    assert format_relevant_block(None, recent=[]) is None


# --- 4. recall semántico de facts + 3. el seam en el wire ---------------------


def _builder(memory) -> TurnContextBuilder:
    persona = Persona(
        persona_id="vultur",
        display_name="Vultur Analytica",
        persona_file="vultur.md",
        token_env="VULTUR_DISCORD_TOKEN",
    )
    return TurnContextBuilder(persona, memory)


def _memory(**overrides) -> MagicMock:
    memory = MagicMock()
    memory.get_facts = AsyncMock(return_value=[])
    memory.search = AsyncMock(return_value=[])
    memory.search_facts_semantic = AsyncMock(return_value=[])
    memory.list_pending_reminders = AsyncMock(return_value=[])
    memory.get_channel_participants = AsyncMock(return_value=[])
    memory.build_context = MagicMock(side_effect=lambda rec, **kw: list(rec))
    for name, value in overrides.items():
        setattr(memory, name, value)
    return memory


async def test_semantic_fact_hits_ride_relevant_memory():
    memory = _memory(
        search_facts_semantic=AsyncMock(return_value=[{"fact": "su hermana estudia enfermería"}]),
    )
    builder = _builder(memory)
    turn = await builder.build(
        channel_id="C1",
        recent=[],
        relevant_query="qué estudia mi hermana",
        guidance_user_id="U1",
        guidance_message="qué estudia mi hermana",
        corpus_query="qué estudia mi hermana",
        exclude_user_id="U1",
    )
    memory.search_facts_semantic.assert_awaited_once()
    assert turn.relevant_memory is not None
    assert "su hermana estudia enfermería" in turn.relevant_memory


async def test_semantic_fact_fault_degrades_to_none_never_mute():
    memory = _memory(search_facts_semantic=AsyncMock(side_effect=RuntimeError("pgvector down")))
    builder = _builder(memory)
    turn = await builder.build(
        channel_id="C1",
        recent=[],
        relevant_query="qué onda",
        guidance_user_id="U1",
        guidance_message="qué onda",
        corpus_query="qué onda",
        exclude_user_id="U1",
    )
    assert turn.relevant_memory is None


async def test_no_subject_user_skips_fact_recall():
    memory = _memory()
    builder = _builder(memory)
    await builder.build(
        channel_id="C1",
        recent=[],
        relevant_query="tema",
        guidance_user_id=None,
        guidance_message="tema",
        corpus_query="tema",
        exclude_user_id="B1",
    )
    memory.search_facts_semantic.assert_not_awaited()


async def test_turn_runner_forwards_relevant_memory_to_the_wire():
    persona = Persona(
        persona_id="insult",
        display_name="Insult",
        persona_file="insult.md",
        token_env="DISCORD_TOKEN",
    )
    memory = MagicMock()
    memory.store = AsyncMock()
    agent_client = MagicMock()
    agent_client.chat = AsyncMock(return_value=SimpleNamespace(text="va", model_used="claude"))
    client = PersonaClient(persona, memory, agent_client, intents=discord.Intents.none())

    class _Typing:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

    channel = MagicMock()
    channel.send = AsyncMock(return_value=MagicMock(id=1))
    channel.typing = MagicMock(return_value=_Typing())
    await client._run_and_deliver(
        channel=channel,
        channel_id="C1",
        user_id="U1",
        guild_id=None,
        channel_name="general",
        messages=[{"role": "user", "content": "hola"}],
        relevant_memory="Fragmentos más viejos: dato clave",
    )
    assert agent_client.chat.await_args.kwargs.get("relevant_memory") == "Fragmentos más viejos: dato clave"


# --- 5. stopwords españolas fuera del keyword search --------------------------


def test_stopwords_are_dropped_discriminating_words_survive():
    assert search_terms("para qué era la receta de mi hermana") == ["receta", "hermana"]


def test_all_stopword_query_yields_no_terms():
    assert search_terms("pero como para que esto") == []


def test_accented_and_uppercase_forms_are_dropped():
    assert search_terms("Cuándo PORQUE También peli") == ["peli"]
