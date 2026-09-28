"""`run_turn` — the surface-free turn pipeline (F3, 2026-09-28).

Pins what a turn from ANY surface now carries that og118's "bald" turns lacked:
the ask and the reply stored, the guardian's guidance on the brain call, the
live thread framed into the user text, markers persisted and stripped, reactions
handed back to the surface instead of leaking as text, facts spawned. And the
resistance half: faults around the brain degrade the turn, only the brain may
fail it, and a resumed job never stores its ask twice.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from persona_core.turn.pipeline import BrainReply, BrainTurn, InboundTurn, run_turn
from shared.personas import Persona

PERSONA = Persona(persona_id="insult", display_name="Insult", persona_file="insult.md", token_env="X")


def _memory(**overrides) -> MagicMock:
    memory = MagicMock()
    memory.get_recent = AsyncMock(return_value=[{"user_name": "Bernard", "content": "hablamos de Creep"}])
    memory.store = AsyncMock()
    memory.search = AsyncMock(return_value=[])
    memory.search_facts_semantic = AsyncMock(return_value=[])
    memory.list_pending_reminders = AsyncMock(return_value=[])
    memory.build_context = MagicMock(
        side_effect=lambda rec, **kw: [{"role": "user", "content": f"{m['user_name']}: {m['content']}"} for m in rec]
    )
    for name, value in overrides.items():
        setattr(memory, name, value)
    return memory


def _turn(**overrides) -> InboundTurn:
    fields = {
        "persona": PERSONA,
        "surface": "og118",
        "channel_id": "conv-1",
        "user_id": "907264175246569543",
        "user_name": "Bernard",
        "ask": "¿y la peli qué?",
        "assistant_id": "1488415576551325906",
    }
    fields.update(overrides)
    return InboundTurn(**fields)


class _Brain:
    def __init__(self, text: str = "Respuesta.", *, raises: Exception | None = None) -> None:
        self.text = text
        self.raises = raises
        self.seen: list[BrainTurn] = []

    async def __call__(self, turn: BrainTurn) -> BrainReply:
        self.seen.append(turn)
        if self.raises:
            raise self.raises
        return BrainReply(self.text, "claude-opus-4-7")


def _patched():
    return (
        patch("persona_core.turn.context.guidance_for_turn", new=AsyncMock(return_value="GUIA-DEL-GUARDIAN")),
        patch("persona_core.turn.context.other_people_block_for_turn", new=AsyncMock(return_value=None)),
        patch("persona_core.turn.context.build_persona_corpus_block", new=AsyncMock(return_value=None)),
    )


async def _run(turn: InboundTurn, memory, brain, judge=None, bg=None):
    a, b, c = _patched()
    with a, b, c:
        return await run_turn(turn, memory=memory, brain=brain, judge=judge, bg_tasks=bg if bg is not None else set())


@pytest.mark.asyncio
async def test_a_turn_stores_the_ask_and_the_reply():
    memory = _memory()
    out = await _run(_turn(), memory, _Brain("Creep, la de Brice."))

    assert out.text == "Creep, la de Brice."
    roles = [call.args[3] for call in memory.store.await_args_list]
    assert roles == ["user", "assistant"]
    ask_row, reply_row = memory.store.await_args_list
    assert ask_row.args[:5] == ("conv-1", "907264175246569543", "Bernard", "user", "¿y la peli qué?")
    assert reply_row.args[1] == "1488415576551325906"
    assert reply_row.kwargs["for_user_id"] == "907264175246569543"
    assert reply_row.kwargs["model_used"] == "claude-opus-4-7"


@pytest.mark.asyncio
async def test_the_brain_reads_the_guardian_and_the_live_thread():
    brain = _Brain()
    await _run(_turn(), _memory(), brain)

    (seen,) = brain.seen
    assert seen.behavioral_guidance == "GUIA-DEL-GUARDIAN"
    assert "<current_time>" in seen.user_text
    assert "Bernard: hablamos de Creep" in seen.user_text, "the recent window must be framed in"
    assert seen.user_text.endswith("¿y la peli qué?"), "the ask closes the framed message"


@pytest.mark.asyncio
async def test_markers_persist_and_never_reach_the_surface():
    persist = AsyncMock(return_value=1)
    with patch("persona_core.turn.markers.persist_remembers", new=persist):
        out = await _run(_turn(), _memory(), _Brain("Anotado. [REMEMBER: le gusta el cine de terror] [REACT:👀]"))

    assert "[REMEMBER" not in out.text and "[REACT" not in out.text
    assert out.text == "Anotado."
    assert out.reactions == ["👀"], "reactions go back to the surface, not into the text"
    persist.assert_awaited_once()
    assert persist.await_args.args[1] == "907264175246569543"


@pytest.mark.asyncio
async def test_facts_are_spawned_with_the_turn_s_judge():
    judge = MagicMock()
    bg: set[asyncio.Task] = set()
    with patch("persona_core.turn.pipeline.FactExtractor") as extractor:
        await _run(_turn(), _memory(), _Brain(), judge=judge, bg=bg)
    spawn = extractor.return_value.spawn
    spawn.assert_called_once()
    judge_arg, user_id, user_name, recent = spawn.call_args.args
    assert (judge_arg, user_id, user_name) == (judge, "907264175246569543", "Bernard")
    assert recent[-1] == {"user_name": "Bernard", "content": "¿y la peli qué?"}


@pytest.mark.asyncio
async def test_a_brain_failure_is_the_surface_s_to_report():
    with pytest.raises(RuntimeError, match="aire down"):
        await _run(_turn(), _memory(), _Brain(raises=RuntimeError("aire down")))


@pytest.mark.asyncio
async def test_memory_faults_degrade_the_turn_never_kill_it():
    memory = _memory(
        get_recent=AsyncMock(side_effect=ConnectionError("pg blip")),
        store=AsyncMock(side_effect=ConnectionError("pg blip")),
    )
    out = await _run(_turn(), memory, _Brain("Sigo aquí."))
    assert out.text == "Sigo aquí."


@pytest.mark.asyncio
async def test_a_resumed_job_does_not_store_its_ask_twice():
    memory = _memory()
    await _run(_turn(resumed=True), memory, _Brain())
    roles = [call.args[3] for call in memory.store.await_args_list]
    assert roles == ["assistant"]


@pytest.mark.asyncio
async def test_an_empty_turn_names_its_reason():
    with patch("persona_core.turn.markers.persist_remembers", new=AsyncMock(return_value=1)):
        out = await _run(_turn(), _memory(), _Brain("[REMEMBER: algo]"))
    assert out.text == ""
    assert out.empty_reason == "markers_only"


@pytest.mark.asyncio
async def test_pacing_markers_never_reach_memory():
    memory = _memory()
    out = await _run(_turn(), memory, _Brain("uno [SEND] dos"))
    assert out.text == "uno\ndos"
    assert memory.store.await_args_list[-1].args[4] == "uno\ndos"


# --- The persona's reaction is memory too (v4.47.0) --------------------------
# A turn that was only a `[REACT:]` used to store nothing: og118 persisted the
# gesture, the persona's memory showed the user's message unanswered. Now the
# assistant row lands with empty content and its emoji — a non-text event, the
# way Rasa records every bot action.


@pytest.mark.asyncio
async def test_a_reaction_only_turn_is_stored_as_an_answer():
    memory = _memory()
    out = await _run(_turn(), memory, _Brain("[REACT:👀]"))

    assert out.text == "" and out.reactions == ["👀"] and out.empty_reason == "reactions_only"
    ask_row, reply_row = memory.store.await_args_list
    assert reply_row.args[3] == "assistant"
    assert reply_row.args[4] == "", "no invented text: the gesture is the answer"
    assert reply_row.kwargs["reactions"] == ["👀"]


@pytest.mark.asyncio
async def test_a_text_turn_stores_its_reactions_with_the_words():
    memory = _memory()
    await _run(_turn(), memory, _Brain("Vives en GDL. [REACT:🔥]"))

    reply_row = memory.store.await_args_list[-1]
    assert reply_row.args[4] == "Vives en GDL."
    assert reply_row.kwargs["reactions"] == ["🔥"]


@pytest.mark.asyncio
async def test_a_turn_with_nothing_to_remember_still_stores_no_reply():
    """Resistance: markers-only has no words and no gesture — no assistant row."""
    memory = _memory()
    with patch("persona_core.turn.markers.persist_remembers", new=AsyncMock(return_value=1)):
        await _run(_turn(), memory, _Brain("[REMEMBER: algo]"))
    roles = [call.args[3] for call in memory.store.await_args_list]
    assert roles == ["user"]


@pytest.mark.asyncio
async def test_a_plain_reply_stores_no_reactions():
    memory = _memory()
    await _run(_turn(), memory, _Brain("Sin gesto."))
    assert memory.store.await_args_list[-1].kwargs["reactions"] is None


# --- Synthetic traffic is tagged and never mined (v4.47.1) -------------------
# 2026-09-28: a wire probe ran under Bernard's principal and landed in his
# memory, and his fact store already held facts mined from earlier probes.


@pytest.mark.asyncio
async def test_a_probe_turn_is_stored_tagged_and_never_mined():
    memory = _memory()
    with patch("persona_core.turn.pipeline.FactExtractor") as extractor:
        out = await _run(_turn(origin="probe", user_id="probe-claude"), memory, _Brain("Vivo. [REACT:👀]"))

    assert out.text == "Vivo."
    extractor.assert_not_called()
    assert [c.kwargs["origin"] for c in memory.store.await_args_list] == ["probe", "probe"]


@pytest.mark.asyncio
async def test_a_person_turn_is_stored_untagged_and_mined():
    """Resistance: the tag never leaks onto a real turn, and extraction still runs."""
    memory = _memory()
    with patch("persona_core.turn.pipeline.FactExtractor") as extractor:
        await _run(_turn(), memory, _Brain("Hola."))

    extractor.return_value.spawn.assert_called_once()
    assert [c.kwargs["origin"] for c in memory.store.await_args_list] == [None, None]
