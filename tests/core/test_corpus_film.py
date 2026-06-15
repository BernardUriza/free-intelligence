"""Film-criticism (Vultur) corpus — detector + loader + injection + RAG gate.

Phase-A method overlay shared between Insult and ALICE (2026-06-01). The frame
activates by TOPIC, not by user, and is identical for both bots; each expresses
it in its own register. The theory RAG (Braudy & Cohen / Language of Film
Criticism) is retrieved per-turn underneath the frame.

Detector design is precision-biased: it must fire on film / film-craft talk but
NOT on neutral mentions. Each behavior gets a positive AND a resistance case per
.claude/rules/robustness.md.
"""

from __future__ import annotations

import types

from khimeras_shared.corpus import (
    detect_film_topic,
    film_criticism_guidance,
    load_film_criticism_values,
)
from personas.insult.cogs.chat.capability_ports import PresetEngineResult
from personas.insult.cogs.chat.stages import _build_behavioral_guidance
from personas.insult.core import deep_memory
from personas.insult.core.presets import PresetMode, PresetSelection

# --- detector: positive cases ----------------------------------------------


def test_detect_fires_on_film_craft_vocab():
    assert detect_film_topic("el plano secuencia final de la película es puro fetichismo formal")
    assert detect_film_topic("¿qué opinas del montaje de esta cinta?")
    assert detect_film_topic("la dirección de fotografía de la película es cinematográfica")


def test_detect_fires_on_analysis_axis():
    assert detect_film_topic("ese cineasta repite el mismo tropo en cada largometraje")
    assert detect_film_topic("quiero una reseña de la película, no la nota de prensa")
    assert detect_film_topic("el guionista no entiende el ritmo diegético")


def test_detect_fires_on_shot_types():
    """Long take and shot vocabulary are core criticism terms (regression:
    'Tarkovsky usa el plano largo' was a false negative pre-fix)."""
    assert detect_film_topic("Tarkovsky usa el plano largo como tedio disfrazado de profundidad")
    assert detect_film_topic("ese plano cenital no aporta nada")
    assert detect_film_topic("the long take here is pure fetish")


# --- detector: resistance cases (must NOT fire) ----------------------------


def test_detect_does_not_fire_on_neutral_mentions():
    """A pet, a gym session, a chore — none is a film-criticism turn."""
    assert not detect_film_topic("tengo un perro muy lindo")
    assert not detect_film_topic("hoy fui al gym y programé un rato")
    assert not detect_film_topic("necesito barrer y trapear el departamento")


def test_detect_does_not_fire_on_casual_actor_or_outing():
    """'actor' alone and 'fui al cine' are not analysis — must stay silent."""
    assert not detect_film_topic("ese actor es buena persona la verdad")
    assert not detect_film_topic("ayer fui al cine con mis amigos y la pasé bien")


def test_detect_empty_and_none_are_false():
    assert not detect_film_topic("")
    assert not detect_film_topic(None)


# --- guidance gate + loader ------------------------------------------------


def test_guidance_returns_frame_on_topic():
    g = film_criticism_guidance("desglosa el montaje de esta película")
    assert "índice de farsa" in g.lower()
    # safety floor must always be present in the frame
    assert "SAFETY OVERRIDES" in g


def test_guidance_empty_off_topic():
    assert film_criticism_guidance("hola qué tal todo") == ""


def test_loader_strips_authoring_comment():
    text = load_film_criticism_values()
    assert not text.lstrip().startswith("<!--")
    assert "Method — film as a body on the table" in text


# --- injection into the behavioral guidance (Insult path) ------------------


def _ctx(text: str):
    sel = PresetSelection(mode=PresetMode.DEFAULT_ABRASIVE, reason="fallback")
    # The preset fragment arrives pre-rendered from the Preset Engine; its
    # content is irrelevant to the corpus gating these tests exercise.
    result = PresetEngineResult(
        selection=sel,
        classifier_source="regex",
        classifier_ms=0,
        vulnerable_overlay=False,
        guidance_block="",
    )
    return types.SimpleNamespace(preset=sel, preset_result=result, flow_guidance="", text=text)


def test_frame_injected_into_guidance_when_on_topic():
    out = _build_behavioral_guidance(_ctx("destrózame el plano secuencia final de esta película"))
    assert "índice de farsa" in out.lower()


def test_frame_absent_from_guidance_when_off_topic():
    """Resistance: an off-topic turn must not drag the Vultur frame into
    every reply."""
    out = _build_behavioral_guidance(_ctx("oye qué opinas de mi código"))
    assert "índice de farsa" not in out.lower()


# --- RAG retrieval gate (build_film_references_block) -----------------------


async def test_film_references_block_none_on_trivial_query():
    """Too-short queries are not worth an embed call — gate returns None
    without touching the DB."""
    assert await deep_memory.build_film_references_block("cine") is None
    assert await deep_memory.build_film_references_block("") is None
    assert await deep_memory.build_film_references_block(None) is None


async def test_query_corpus_empty_when_embed_unavailable(monkeypatch):
    """When the embedder yields no vector, query_corpus degrades to [] rather
    than raising — corpus absence is a valid answer, never an error."""

    async def _no_embed(_text):
        return None

    monkeypatch.setattr(deep_memory, "embed_text", _no_embed)
    assert await deep_memory.query_corpus("montaje de la película de Tarkovsky") == []


async def test_film_references_block_none_when_no_hits(monkeypatch):
    """A non-trivial query that retrieves nothing yields None (caller injects
    nothing rather than padding the turn)."""

    async def _no_hits(_query, **_kw):
        return []

    monkeypatch.setattr(deep_memory, "query_corpus", _no_hits)
    out = await deep_memory.build_film_references_block("analiza la estructura narrativa de esta película larga")
    assert out is None
