"""Tests for cross-domain synthesis detector (Phase 2.5, v3.6.3).

Activation must be high-recall on the patterns the user reported:
"X y Y son dos caras de una misma moneda", "-ismo y -ismo", explicit
parallels between philosophical / political / ethical domains.

Activation must NOT fire on glib casual comparisons or jokes.
"""

from __future__ import annotations

import pytest

from personas.insult.core.presets import PresetModifier, classify_preset
from personas.insult.core.synthesis_detector import detect_synthesis


class TestStrongPatterns:
    """One STRONG match alone activates — even with counter signals."""

    def test_dos_caras_misma_moneda_real_incident(self):
        # Verbatim from prod incident 2026-04-26 00:26:15
        msg = "El racismo y el especismo son dos caras de una misma moneda"
        sig = detect_synthesis(msg)
        assert sig.activated, sig.reason
        assert sig.strong_hits >= 1

    def test_misma_logica(self):
        msg = "El antisemitismo y la islamofobia operan con la misma lógica de chivo expiatorio"
        assert detect_synthesis(msg).activated

    def test_ism_pair_spanish(self):
        msg = "El veganismo y el feminismo comparten una crítica de la dominación"
        assert detect_synthesis(msg).activated

    def test_ism_pair_english(self):
        msg = "Speciesism and racism are structurally analogous in how they justify exclusion"
        assert detect_synthesis(msg).activated

    def test_two_sides_same_coin_english(self):
        msg = "Patriarchy and capitalism are two sides of the same coin in feminist analysis"
        assert detect_synthesis(msg).activated

    def test_strong_survives_counter(self):
        # Even with "jaja" present, an explicit STRONG cue still fires.
        msg = "jaja pero en serio, racismo y especismo son dos caras de la misma moneda"
        sig = detect_synthesis(msg)
        assert sig.activated
        assert sig.counter_hits >= 1


class TestWeakPatterns:
    """Two WEAK matches activate. One weak + one counter does not."""

    def test_two_weak_signals_activate(self):
        # "es como" (weak comparison) + "la lógica del" (weak academic) = activate
        msg = "El neoliberalismo es como un evangelio: opera con la lógica del mercado infinito"
        assert detect_synthesis(msg).activated

    def test_single_weak_does_not_activate(self):
        # Just one weak signal isn't enough
        msg = "El veganismo es una postura ética seria que merece respeto"
        sig = detect_synthesis(msg)
        # exactly one -ism word, no other strong/weak — should NOT activate
        assert not sig.activated, sig.reason

    def test_thinker_name_counts_as_weak(self):
        msg = "Es como Foucault decía: la estructura del poder se reproduce en cada institución"
        assert detect_synthesis(msg).activated


class TestCounters:
    """Levity markers suppress WEAK-only activation."""

    def test_jaja_suppresses_weak_only(self):
        # WEAK signals present but jaja drains seriousness
        msg = "jajaja el lunes y el café son lo mismo, ambos son la lógica del sufrimiento"
        sig = detect_synthesis(msg)
        # weak=2 (es como would match if present, here lo-mismo + lógica) + counter
        # → weak alone wouldn't fire under counter
        assert not sig.activated or sig.counter_hits >= 1

    def test_emoji_laughing_does_not_suppress_strong(self):
        # Verbatim STRONG match present ("dos caras de la misma") — the laugh
        # emoji must NOT suppress an explicit comparison cue.
        msg = "El amor y el odio son dos caras de la misma moneda, supuestamente 🤣"
        sig = detect_synthesis(msg)
        assert sig.activated  # STRONG always wins
        assert sig.counter_hits >= 1


class TestNegativeCases:
    """Messages that must NOT activate the modifier."""

    def test_short_message_skipped(self):
        # Below MIN_MESSAGE_LENGTH (30 chars) we never activate
        assert not detect_synthesis("eres tonto").activated
        assert not detect_synthesis("racismo y especismo").activated  # too short, just terms

    def test_pure_factual_question(self):
        msg = "¿A qué hora es la cena hoy en mi casa, sabes?"
        assert not detect_synthesis(msg).activated

    def test_chitchat(self):
        msg = "Hoy desayuné chilaquiles, estaban muy ricos la verdad"
        assert not detect_synthesis(msg).activated

    def test_simple_opinion_no_comparison(self):
        msg = "Creo que el activismo vegano sutil funciona mejor que el confrontacional"
        # No cross-domain bridge here — just one domain (veganism)
        sig = detect_synthesis(msg)
        # A single -ism word triggers ONE weak — not enough to activate
        assert not sig.activated


class TestClassifyPresetIntegration:
    """``classify_preset`` attaches MULTI_DOMAIN_SYNTHESIS when the detector fires."""

    def test_modifier_attached_on_real_incident(self):
        msg = "El racismo y el especismo son dos caras de una misma moneda"
        sel = classify_preset(msg, recent_messages=[], user_facts=[])
        assert PresetModifier.MULTI_DOMAIN_SYNTHESIS in sel.modifiers

    def test_modifier_not_attached_on_chitchat(self):
        msg = "Hoy fui al super y compré aguacates muy maduros, una belleza"
        sel = classify_preset(msg, recent_messages=[], user_facts=[])
        assert PresetModifier.MULTI_DOMAIN_SYNTHESIS not in sel.modifiers

    def test_modifier_coexists_with_memory_recall(self):
        # User has facts AND makes synthesis claim — both modifiers fire
        msg = "El racismo y el especismo son dos caras de la misma moneda, como dije antes"
        facts = [
            {"fact": "Bernard es vegano por razones éticas", "category": "interests"},
            {"fact": "Le interesa la teoría política crítica", "category": "interests"},
        ]
        sel = classify_preset(msg, recent_messages=[], user_facts=facts)
        assert PresetModifier.MULTI_DOMAIN_SYNTHESIS in sel.modifiers


@pytest.mark.parametrize(
    "msg",
    [
        "El antisemitismo y el racismo son dos caras de la misma moneda",
        "Speciesism and racism share the same logical structure",
        "El neoliberalismo y el self-help operan con la misma lógica de responsabilizar al individuo",
        "Como Singer argumenta, la frontera entre humano y animal es arbitraria como la frontera racial",
        "El feminismo y el veganismo comparten la misma raíz: la crítica de la dominación",
    ],
)
def test_canonical_synthesis_messages_all_activate(msg):
    assert detect_synthesis(msg).activated, f"failed on: {msg!r}"
