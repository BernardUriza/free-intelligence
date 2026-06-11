"""Universal animal-liberation values corpus — detector + loader + injection.

Phase-A values overlay shared between Insult and ALICE (2026-05-22). The
corpus activates by TOPIC, not by user, and is identical for both bots.

Detector design is precision-biased: it must fire on animal-use / veganism
talk (including the food-contamination shape from Bernard's pizza incident)
but NOT on neutral animal mentions. Each behavior gets a positive AND a
resistance case per .claude/rules/robustness.md.
"""

from __future__ import annotations

import types

from insult.cogs.chat.capability_ports import PresetEngineResult
from insult.cogs.chat.stages import _build_behavioral_guidance
from insult.core.presets import PresetMode, PresetSelection
from shared.corpus import (
    animal_liberation_guidance,
    detect_animal_topic,
    load_animal_liberation_values,
)

# --- detector: positive cases ----------------------------------------------


def test_detect_fires_on_veganism_vocab():
    assert detect_animal_topic("veganism is a moral principle, not a diet")
    assert detect_animal_topic("eso es puro welfarism, no abolitionism")
    assert detect_animal_topic("el especismo es un marco de dominación")


def test_detect_fires_on_food_contamination_shape():
    """The exact shape of the 2026-05-22 pizza incident."""
    assert detect_animal_topic("Es la pizza supuestamente vegetariana")
    assert detect_animal_topic("me pusieron jamón sin que lo pidiera")
    assert detect_animal_topic("el pedido se vendía como sin origen animal")


# --- detector: resistance cases (must NOT fire) ----------------------------


def test_detect_does_not_fire_on_neutral_animal_mention():
    """A pet is not an animal-use debate."""
    assert not detect_animal_topic("tengo un perro muy lindo")
    assert not detect_animal_topic("mi gato se subió al techo")


def test_detect_does_not_fire_on_unrelated_topic():
    assert not detect_animal_topic("hoy programé un rato y fui al gym")
    assert not detect_animal_topic("necesito barrer y trapear el departamento")


def test_detect_empty_and_none_are_false():
    assert not detect_animal_topic("")
    assert not detect_animal_topic(None)


# --- guidance gate + loader ------------------------------------------------


def test_guidance_returns_frame_on_topic():
    g = animal_liberation_guidance("pedí vegano y me llegó con carne")
    assert "abolition" in g.lower()
    # safety floor must always be present in the frame
    assert "SAFETY OVERRIDES" in g


def test_guidance_empty_off_topic():
    assert animal_liberation_guidance("hola qué tal todo") == ""


def test_loader_strips_authoring_comment():
    text = load_animal_liberation_values()
    assert not text.lstrip().startswith("<!--")
    assert "Frame — animal liberation" in text


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


def test_corpus_injected_into_guidance_when_on_topic():
    out = _build_behavioral_guidance(_ctx("me dieron carne en mi pizza vegana"))
    assert "abolition" in out.lower()


def test_corpus_absent_from_guidance_when_off_topic():
    """Resistance: an off-topic turn must not drag the animal frame into
    every reply."""
    out = _build_behavioral_guidance(_ctx("oye qué opinas de mi código"))
    assert "abolition" not in out.lower()
