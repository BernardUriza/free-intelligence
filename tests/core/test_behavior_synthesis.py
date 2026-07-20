"""Tests for khimeras_shared.behavior.synthesis — cross-domain synthesis detector."""

import dataclasses

import pytest

from khimeras_shared.behavior.synthesis import (
    _MIN_MESSAGE_LENGTH,
    SynthesisSignal,
    detect_synthesis,
)

# ═══════════════════════════════════════════════════════════════════════════
# Minimum length gate
# ═══════════════════════════════════════════════════════════════════════════


class TestMinLengthGate:
    def test_short_message_with_strong_content_never_activates(self):
        msg = "racism and sexism"
        assert len(msg) < _MIN_MESSAGE_LENGTH
        assert detect_synthesis(msg).activated is False

    def test_short_message_reports_zero_hits(self):
        signal = detect_synthesis("same logic here")
        assert signal.strong_hits == 0
        assert signal.weak_hits == 0
        assert signal.counter_hits == 0
        assert signal.matched_terms == []

    def test_boundary_exactly_min_length_is_evaluated(self):
        msg = "same logic".ljust(_MIN_MESSAGE_LENGTH, ".")
        signal = detect_synthesis(msg)
        assert signal.activated is True
        assert signal.strong_hits == 1

    def test_boundary_one_below_min_length_is_suppressed(self):
        msg = "same logic".ljust(_MIN_MESSAGE_LENGTH - 1, ".")
        assert detect_synthesis(msg).activated is False

    def test_empty_string_not_activated(self):
        signal = detect_synthesis("")
        assert signal.activated is False
        assert signal.matched_terms == []

    def test_none_raises_typeerror(self):
        with pytest.raises(TypeError):
            detect_synthesis(None)


# ═══════════════════════════════════════════════════════════════════════════
# STRONG patterns — one match activates
# ═══════════════════════════════════════════════════════════════════════════


class TestStrongPatterns:
    def test_dos_caras_de_la_misma_moneda(self):
        signal = detect_synthesis("el apartheid y el especismo son dos caras de la misma moneda")
        assert signal.activated is True
        assert signal.strong_hits >= 1

    def test_misma_logica(self):
        signal = detect_synthesis("el neoliberalismo y la autoayuda operan con la misma lógica de fondo")
        assert signal.activated is True
        assert signal.strong_hits >= 1

    def test_same_logic_english(self):
        signal = detect_synthesis("colonialism and factory farming follow the same logic of domination")
        assert signal.activated is True
        assert signal.strong_hits >= 1

    def test_es_esencialmente_lo_mismo(self):
        signal = detect_synthesis("explotar animales y explotar trabajadores es esencialmente lo mismo")
        assert signal.activated is True
        assert signal.strong_hits >= 1

    def test_paralelo_entre_two_domains(self):
        signal = detect_synthesis("hay un paralelo entre apartheid y especismo que nadie quiere ver")
        assert signal.activated is True
        assert signal.strong_hits >= 1
        assert any("paralelo entre" in t for t in signal.matched_terms)

    def test_spanish_ismo_pair_with_article(self):
        signal = detect_synthesis("El veganismo y el feminismo comparten preguntas sobre quién importa")
        assert signal.activated is True
        assert signal.strong_hits >= 1
        assert any("veganismo y el feminismo" in t for t in signal.matched_terms)

    def test_english_short_ism_pair(self):
        signal = detect_synthesis("racism and sexism operate through the same mechanisms of exclusion")
        assert signal.activated is True
        assert any("racism and sexism" in t for t in signal.matched_terms)

    def test_discriminacion_racial(self):
        signal = detect_synthesis("la discriminacion racial y la discriminacion por especie se tocan aqui")
        assert signal.activated is True
        assert signal.strong_hits >= 1

    def test_mundane_long_message_does_not_activate(self):
        signal = detect_synthesis("Hoy fui al mercado y compré verduras para la cena de mañana en casa")
        assert signal.activated is False
        assert signal.strong_hits == 0
        assert signal.weak_hits == 0


# ═══════════════════════════════════════════════════════════════════════════
# WEAK patterns — two required, one is a near-miss
# ═══════════════════════════════════════════════════════════════════════════


class TestWeakPatterns:
    def test_two_weak_signals_activate(self):
        signal = detect_synthesis("El capitalismo es como una religion secular de nuestra era moderna")
        assert signal.activated is True
        assert signal.strong_hits == 0
        assert signal.weak_hits >= 2

    def test_single_weak_signal_does_not_activate(self):
        signal = detect_synthesis("Eso es como cuando llueve mucho en verano por aca en la ciudad")
        assert signal.activated is False
        assert signal.weak_hits == 1

    def test_repeated_same_pattern_counts_once(self):
        signal = detect_synthesis("La escuela es como una fábrica y la oficina es como una cárcel gris")
        assert signal.weak_hits == 1
        assert signal.activated is False

    def test_theorist_plus_citation_framing_activates(self):
        signal = detect_synthesis("segun Foucault escribe sobre el poder y los cuerpos dóciles en la cárcel")
        assert signal.activated is True
        assert signal.strong_hits == 0
        assert signal.weak_hits >= 2

    def test_theorist_name_alone_does_not_activate(self):
        signal = detect_synthesis("Foucault ya lo habia dicho sobre el panoptico y la vigilancia moderna")
        assert signal.activated is False
        assert signal.weak_hits == 1
        assert any("Foucault" in t for t in signal.matched_terms)

    def test_english_citation_framing_activates(self):
        signal = detect_synthesis("como Singer argues, the boundary of moral concern is arbitrary here")
        assert signal.activated is True
        assert signal.weak_hits >= 2


# ═══════════════════════════════════════════════════════════════════════════
# COUNTER patterns — levity suppresses weak fires, never strong ones
# ═══════════════════════════════════════════════════════════════════════════


class TestCounters:
    def test_jaja_suppresses_weak_only_fire(self):
        signal = detect_synthesis("El capitalismo es como una religion secular de nuestra era jajaja")
        assert signal.activated is False
        assert signal.weak_hits >= 2
        assert signal.counter_hits >= 1

    def test_lol_suppresses_weak_only_fire(self):
        signal = detect_synthesis("El capitalismo es como una religion secular de nuestra era lol")
        assert signal.activated is False
        assert signal.counter_hits >= 1

    def test_emoji_suppresses_weak_only_fire(self):
        signal = detect_synthesis("El capitalismo es como una religion secular de nuestra era 😂")
        assert signal.activated is False
        assert signal.counter_hits >= 1

    def test_counter_does_not_suppress_strong_fire(self):
        signal = detect_synthesis("el apartheid y el especismo son dos caras de la misma moneda jajaja")
        assert signal.activated is True
        assert signal.strong_hits >= 1
        assert signal.counter_hits >= 1

    def test_serious_weak_message_without_levity_still_activates(self):
        signal = detect_synthesis("El capitalismo es como una religion secular de nuestra era moderna")
        assert signal.counter_hits == 0
        assert signal.activated is True


# ═══════════════════════════════════════════════════════════════════════════
# SynthesisSignal shape
# ═══════════════════════════════════════════════════════════════════════════


class TestSynthesisSignal:
    def test_matched_terms_capped_at_40_chars(self):
        msg = "es" + " " * 25 + "fundamentalmente" + " " * 15 + "lo mismo, insisto"
        signal = detect_synthesis(msg)
        assert signal.activated is True
        assert signal.matched_terms
        assert all(len(term) <= 40 for term in signal.matched_terms)

    def test_matched_terms_include_strong_and_weak(self):
        signal = detect_synthesis("El veganismo y el feminismo comparten la lógica de la exclusión moral")
        assert signal.strong_hits >= 1
        assert signal.weak_hits >= 1
        assert len(signal.matched_terms) == signal.strong_hits + signal.weak_hits

    def test_reason_reports_all_counts(self):
        signal = detect_synthesis("el apartheid y el especismo son dos caras de la misma moneda jajaja")
        assert f"strong={signal.strong_hits}" in signal.reason
        assert f"weak={signal.weak_hits}" in signal.reason
        assert f"counters={signal.counter_hits}" in signal.reason

    def test_reason_caps_terms_at_five(self):
        signal = SynthesisSignal(True, 3, 4, 0, ["a", "b", "c", "d", "e", "f", "g"])
        assert "'e'" in signal.reason
        assert "'f'" not in signal.reason
        assert "'g'" not in signal.reason

    def test_signal_is_frozen(self):
        signal = detect_synthesis("")
        with pytest.raises(dataclasses.FrozenInstanceError):
            signal.activated = True


# ═══════════════════════════════════════════════════════════════════════════
# Known bug — Spanish short -ismo pairs
# ═══════════════════════════════════════════════════════════════════════════


class TestSpanishShortIsmPairBug:
    @pytest.mark.xfail(
        strict=True,
        reason=(
            "El patrón STRONG de pares -ismo en español exige 4+ chars antes de "
            "'ismo', excluyendo racismo/sexismo — el comentario adyacente en "
            "synthesis.py declara que los -ismos cortos (rac/sex/age) son "
            "vocabulario teórico genuino y el patrón inglés SÍ acepta "
            "'racism and sexism'. Falso negativo del caso canónico en español."
        ),
    )
    def test_racismo_y_sexismo_should_activate(self):
        signal = detect_synthesis("El racismo y el sexismo comparten mecanismos que excluyen a grupos enteros")
        assert signal.activated is True
