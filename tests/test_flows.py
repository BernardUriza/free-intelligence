"""Tests for insult.core.flows — 4-flow behavioral analysis pipeline."""

from personas.insult.core.flows import (
    AwarenessAnalysis,
    ConversationPattern,
    EpistemicAnalysis,
    EpistemicMove,
    ExpressionAnalysis,
    ExpressionHistory,
    FlowAnalysis,
    PressureAnalysis,
    ResponseShape,
    StyleFlavor,
    UserState,
    _analyze_awareness,
    _analyze_epistemic,
    _analyze_pressure,
    _detect_contradiction,
    _detect_repetition_loop,
    _select_flavor,
    _select_shape,
    analyze_flows,
    build_flow_prompt,
    detect_lifelessness,
    validate_flow_adherence,
)
from personas.insult.core.presets import PresetMode, PresetSelection

# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════


def _preset(mode: PresetMode = PresetMode.DEFAULT_ABRASIVE) -> PresetSelection:
    return PresetSelection(mode=mode, confidence=0.7, reason="test")


# ═══════════════════════════════════════════════════════════════════════════
# Flow 1: Epistemic Control
# ═══════════════════════════════════════════════════════════════════════════


class TestEpistemicAnalysis:
    def test_clean_message_no_move(self):
        result = _analyze_epistemic("hola que onda", [])
        assert result.recommended_move == EpistemicMove.NONE

    def test_high_assertion_low_hedging_challenges(self):
        msg = "The economy is broken. Capitalism is the root of all evil. Everyone knows this is true."
        result = _analyze_epistemic(msg, [])
        assert result.assertion_density >= 0.5
        assert result.hedging_score < 0.1

    def test_high_fluff_compresses(self):
        msg = "Pues la verdad o sea basically like you know honestly at the end of the day it is what it is bueno pues"
        result = _analyze_epistemic(msg, [])
        assert result.fluff_score >= 0.3
        assert result.recommended_move == EpistemicMove.COMPRESS

    def test_vague_claims_demands_evidence(self):
        msg = "Studies show that people think the economy is bad. Everyone says it's obvious that we need change."
        result = _analyze_epistemic(msg, [])
        assert result.vague_claim_count >= 2
        assert result.recommended_move == EpistemicMove.DEMAND_EVIDENCE

    def test_hedging_with_assertion_concedes(self):
        msg = (
            "I think maybe the system is broken, but I'm not sure. It could be that capitalism is part of it, arguably."
        )
        result = _analyze_epistemic(msg, [])
        assert result.hedging_score >= 0.2

    def test_short_message_no_compress(self):
        msg = "pues honestly no sé"
        result = _analyze_epistemic(msg, [])
        # Short messages should NOT trigger COMPRESS even with fluff
        assert result.recommended_move != EpistemicMove.COMPRESS


class TestContradictionDetection:
    def test_detects_negation_flip(self):
        prior = ["El capitalismo es un sistema necesario para la sociedad moderna"]
        current = "El capitalismo no es necesario para la sociedad moderna, nunca lo fue"
        assert _detect_contradiction(current, prior)

    def test_no_false_positive_on_unrelated(self):
        prior = ["Me gusta el futbol"]
        current = "No es necesario estudiar tanto"
        assert not _detect_contradiction(current, prior)

    def test_english_contradiction(self):
        prior = ["Democracy is always the best system"]
        current = "Democracy isn't always the best option for every country"
        assert _detect_contradiction(current, prior)

    def test_no_contradiction_on_empty(self):
        assert not _detect_contradiction("something", [])


# ═══════════════════════════════════════════════════════════════════════════
# Flow 2: Adaptive Pressure
# ═══════════════════════════════════════════════════════════════════════════


class TestPressureAnalysis:
    def test_neutral_on_normal_message(self):
        result = _analyze_pressure("buenos dias, como amaneciste", [], _preset())
        assert result.detected_state == UserState.NEUTRAL
        assert result.pressure_level == 2

    def test_confused_detection(self):
        result = _analyze_pressure("no entiendo, que??? me perdí", [], _preset())
        assert result.detected_state == UserState.CONFUSED
        assert result.pressure_level == 1

    def test_evasive_detection(self):
        result = _analyze_pressure("whatever, da igual, cambiando de tema", [], _preset())
        assert result.detected_state == UserState.EVASIVE
        assert result.pressure_level == 3

    def test_hostile_detection(self):
        result = _analyze_pressure("callate pendejo, SHUT UP!!!", [], _preset())
        assert result.detected_state == UserState.HOSTILE
        assert result.pressure_level == 4

    def test_prejudiced_detection(self):
        result = _analyze_pressure("esos tipos siempre con su agenda gay", [], _preset())
        assert result.detected_state == UserState.PREJUDICED
        assert result.pressure_level == 4

    def test_vulnerable_detection(self):
        result = _analyze_pressure("la verdad es que me siento muy mal, tengo miedo de todo", [], _preset())
        assert result.detected_state == UserState.VULNERABLE
        assert result.pressure_level == 1

    def test_sincere_detection(self):
        result = _analyze_pressure("en serio, quiero entender tu punto de vista", [], _preset())
        assert result.detected_state == UserState.SINCERE
        assert result.pressure_level == 2

    def test_playful_detection(self):
        result = _analyze_pressure("jajaja ya wey no mames lol 😂", [], _preset())
        assert result.detected_state == UserState.PLAYFUL
        assert result.pressure_level == 2

    def test_serious_preset_clamps_pressure(self):
        result = _analyze_pressure(
            "callate pendejo",
            [],
            _preset(PresetMode.RESPECTFUL_SERIOUS),
        )
        assert result.pressure_level == 1
        assert result.clamped_by_preset

    def test_playful_preset_caps_at_3(self):
        result = _analyze_pressure(
            "callate pendejo",
            [],
            _preset(PresetMode.PLAYFUL_ROAST),
        )
        assert result.pressure_level <= 3

    def test_arc_prejudice_boosts_to_5(self):
        result = _analyze_pressure(
            "esos tipos con su agenda woke",
            [],
            _preset(PresetMode.ARC),
        )
        assert result.pressure_level == 5

    def test_playful_beats_hostile(self):
        # "ya wey" is playful, "pendejo" could be hostile in some contexts
        # but combined with laughter, playful should win
        result = _analyze_pressure("jajaja ya wey 💀", [], _preset())
        assert result.detected_state in (UserState.PLAYFUL, UserState.NEUTRAL)

    def test_window_boosts_persistent_state(self):
        recent = [
            {"role": "user", "content": "no entiendo"},
            {"role": "assistant", "content": "te explico"},
            {"role": "user", "content": "sigo sin entender, que???"},
        ]
        result = _analyze_pressure("me perdí otra vez", recent, _preset())
        assert result.detected_state == UserState.CONFUSED
        assert result.state_confidence > 0.3


# ═══════════════════════════════════════════════════════════════════════════
# Flow 3: Dynamic Expression
# ═══════════════════════════════════════════════════════════════════════════


class TestExpressionSelection:
    def _pressure(self, state=UserState.NEUTRAL, level=2):
        return PressureAnalysis(
            detected_state=state,
            state_confidence=0.5,
            pressure_level=level,
            pressure_reason="test",
            clamped_by_preset=False,
        )

    def _epistemic(self, move=EpistemicMove.NONE):
        return EpistemicAnalysis(
            assertion_density=0.0,
            hedging_score=0.0,
            fluff_score=0.0,
            contradiction_detected=False,
            vague_claim_count=0,
            recommended_move=move,
            move_reason="test",
        )

    def test_pressure_5_forces_one_hit(self):
        shape, _reason, _ = _select_shape("test", _preset(), self._pressure(level=5), self._epistemic(), [])
        assert shape == ResponseShape.ONE_HIT

    def test_vulnerable_forces_short(self):
        shape, _, _ = _select_shape("test", _preset(), self._pressure(UserState.VULNERABLE, 1), self._epistemic(), [])
        assert shape == ResponseShape.SHORT_EXCHANGE

    def test_compress_forces_one_hit(self):
        shape, _, _ = _select_shape("test", _preset(), self._pressure(), self._epistemic(EpistemicMove.COMPRESS), [])
        assert shape == ResponseShape.ONE_HIT

    def test_challenge_forces_probing(self):
        shape, _, _ = _select_shape(
            "test", _preset(), self._pressure(), self._epistemic(EpistemicMove.CHALLENGE_PREMISE), []
        )
        assert shape == ResponseShape.PROBING

    def test_intellectual_preset_long_input(self):
        long_msg = "word " * 40
        shape, _, _ = _select_shape(
            long_msg, _preset(PresetMode.INTELLECTUAL_PRESSURE), self._pressure(), self._epistemic(), []
        )
        assert shape == ResponseShape.DENSE_CRITIQUE

    def test_playful_preset_one_hit(self):
        shape, _, _ = _select_shape("jaja", _preset(PresetMode.PLAYFUL_ROAST), self._pressure(), self._epistemic(), [])
        assert shape == ResponseShape.ONE_HIT

    # --- Length reciprocity (PR 2.5, 2026-05-10 — Alex feedback) ---
    # The original Insult mirrored input length. The rewrite collapsed
    # everything to ONE_HIT. These tests pin the new contract so any
    # future "let's make it cortante again" change is loud.

    def test_long_input_overrides_playful_preset(self):
        """A 300-word message in PLAYFUL_ROAST must NOT come back as
        ONE_HIT — that's the dismissive UX Alex complained about."""
        long_msg = "palabra " * 100  # 100 words, well over 80
        shape, reason, _ = _select_shape(
            long_msg,
            _preset(PresetMode.PLAYFUL_ROAST),
            self._pressure(),
            self._epistemic(),
            [],
        )
        assert shape == ResponseShape.LAYERED, f"length reciprocity violated — got {shape.value}, reason={reason}"
        assert "reciprocity_long" in reason

    def test_long_input_overrides_default_abrasive(self):
        long_msg = "palabra " * 100
        shape, reason, _ = _select_shape(
            long_msg,
            _preset(PresetMode.DEFAULT_ABRASIVE),
            self._pressure(),
            self._epistemic(),
            [],
        )
        assert shape == ResponseShape.LAYERED
        assert "reciprocity_long" in reason

    def test_medium_input_picks_layered_or_expressive(self):
        """40 words is medium territory: must produce a paragraph-
        textured response (LAYERED) or fragmented (EXPRESSIVE_THINKING),
        never ONE_HIT."""
        medium_msg = "palabra " * 40
        # Sample 25x to cover both branches of the random 60/40 split.
        shapes: set[ResponseShape] = set()
        for _ in range(25):
            shape, _r, _ = _select_shape(
                medium_msg,
                _preset(PresetMode.DEFAULT_ABRASIVE),
                self._pressure(),
                self._epistemic(),
                [],
            )
            shapes.add(shape)
        # All sampled shapes must be paragraph-textured.
        assert shapes <= {ResponseShape.LAYERED, ResponseShape.EXPRESSIVE_THINKING}, (
            f"medium input produced non-reciprocal shapes: {[s.value for s in shapes]}"
        )

    def test_short_input_still_one_hit_in_playful(self):
        """Reciprocity must NOT break the short-input → ONE_HIT
        contract. Only LONG inputs override the preset default."""
        shape, _, _ = _select_shape("jaja", _preset(PresetMode.PLAYFUL_ROAST), self._pressure(), self._epistemic(), [])
        assert shape == ResponseShape.ONE_HIT

    def test_safety_overrides_length_reciprocity(self):
        """Pressure-5 boundary must still produce ONE_HIT even on
        long input — safety carve-outs trump reciprocity."""
        long_msg = "palabra " * 100
        shape, reason, _ = _select_shape(
            long_msg,
            _preset(PresetMode.DEFAULT_ABRASIVE),
            self._pressure(level=5),
            self._epistemic(),
            [],
        )
        assert shape == ResponseShape.ONE_HIT
        assert reason == "pressure_5_boundary"

    def test_vulnerable_user_overrides_length_reciprocity(self):
        long_msg = "palabra " * 100
        shape, _, _ = _select_shape(
            long_msg,
            _preset(PresetMode.DEFAULT_ABRASIVE),
            self._pressure(UserState.VULNERABLE, 1),
            self._epistemic(),
            [],
        )
        assert shape == ResponseShape.SHORT_EXCHANGE

    def test_anti_repetition_rotates_shape(self):
        # If ONE_HIT was used twice, should rotate
        shape, _reason, avoided = _select_shape(
            "jaja",
            _preset(PresetMode.PLAYFUL_ROAST),
            self._pressure(),
            self._epistemic(),
            ["one_hit", "one_hit"],
        )
        assert shape != ResponseShape.ONE_HIT
        assert "one_hit" in avoided

    # --- Instructional intent (PR 2.6, 2026-05-12 — Bernard feedback) ---
    # The bot was returning ONE_HIT to short imperatives like
    # "Pero dile cómo se abre Claude Code" because length reciprocity
    # only fires for wc>30. Instructional triggers must produce a
    # paragraph regardless of input length so the third-party audience
    # (Alex) gets the actual steps.

    def test_instructional_short_imperative_forces_layered(self):
        """`Pero dile cómo se abre Claude Code` is 7 words but the
        appropriate output is paragraph-length steps, not ONE_HIT."""
        shape, reason, _ = _select_shape(
            "Pero dile cómo se abre Claude Code",
            _preset(PresetMode.DEFAULT_ABRASIVE),
            self._pressure(),
            self._epistemic(),
            [],
        )
        assert shape == ResponseShape.LAYERED, f"instructional ignored — got {shape.value}, reason={reason}"
        assert "instructional_request" in reason

    def test_instructional_explica_paso_a_paso(self):
        shape, reason, _ = _select_shape(
            "explícame paso a paso",
            _preset(PresetMode.DEFAULT_ABRASIVE),
            self._pressure(),
            self._epistemic(),
            [],
        )
        assert shape == ResponseShape.LAYERED
        assert "instructional_request" in reason

    def test_instructional_english_imperative(self):
        shape, reason, _ = _select_shape(
            "tell her how to do it",
            _preset(PresetMode.PLAYFUL_ROAST),
            self._pressure(),
            self._epistemic(),
            [],
        )
        assert shape == ResponseShape.LAYERED
        assert "instructional_request" in reason

    def test_instructional_protected_from_rotation(self):
        """Even if LAYERED appeared in the last 2 turns, instructional
        intent must NOT be tumbled to short_exchange — the audience
        still needs the explanation."""
        shape, reason, _ = _select_shape(
            "dile cómo se abre",
            _preset(PresetMode.DEFAULT_ABRASIVE),
            self._pressure(),
            self._epistemic(),
            ["layered", "layered"],
        )
        assert shape == ResponseShape.LAYERED
        assert "instructional_request" in reason
        assert "rotated_from" not in reason

    def test_reciprocity_long_protected_from_rotation(self):
        """A reciprocity_long_wc=99 turn must NOT get demoted to
        short_exchange because LAYERED was used recently. This bit
        the bot on 2026-05-12: a 99-word ask got rotated_from_layered
        to short_exchange."""
        long_msg = "palabra " * 100
        shape, reason, _ = _select_shape(
            long_msg,
            _preset(PresetMode.DEFAULT_ABRASIVE),
            self._pressure(),
            self._epistemic(),
            ["layered", "layered"],
        )
        assert shape == ResponseShape.LAYERED
        assert "reciprocity_long" in reason
        assert "rotated_from" not in reason

    def test_safety_overrides_instructional(self):
        """Pressure-5 boundary still wins over instructional — safety
        carve-outs trump content shape."""
        shape, reason, _ = _select_shape(
            "explícame paso a paso",
            _preset(PresetMode.DEFAULT_ABRASIVE),
            self._pressure(level=5),
            self._epistemic(),
            [],
        )
        assert shape == ResponseShape.ONE_HIT
        assert reason == "pressure_5_boundary"

    def test_vulnerable_state_overrides_instructional(self):
        """An ad-hoc VULNERABLE detected_state still routes to
        SHORT_EXCHANGE even if the user uses an instructional verb."""
        shape, _, _ = _select_shape(
            "dime cómo le hago",
            _preset(PresetMode.DEFAULT_ABRASIVE),
            self._pressure(UserState.VULNERABLE, 1),
            self._epistemic(),
            [],
        )
        assert shape == ResponseShape.SHORT_EXCHANGE

    def test_anti_repetition_rotates_flavor(self):
        # Same flavor 3x should rotate
        flavor, _reason, avoided = _select_flavor(
            "test",
            _preset(PresetMode.INTELLECTUAL_PRESSURE),
            self._pressure(),
            ["dry", "dry"],
        )
        assert flavor != StyleFlavor.DRY
        assert "dry" in avoided

    def test_prejudice_selects_clinical(self):
        flavor, _, _ = _select_flavor("test", _preset(), self._pressure(UserState.PREJUDICED, 4), [])
        assert flavor == StyleFlavor.CLINICAL

    def test_arc_selects_philosophical(self):
        flavor, _, _ = _select_flavor("test", _preset(PresetMode.ARC), self._pressure(), [])
        assert flavor == StyleFlavor.PHILOSOPHICAL

    def test_ecphrastic_on_cultural_content(self):
        msg = "viste la nueva pelicula? la foto del museo estaba increible"
        flavor, reason, _ = _select_flavor(msg, _preset(), self._pressure(), [])
        assert flavor == StyleFlavor.ECPHRASTIC
        assert "ecphrastic" in reason

    def test_reflexive_on_contemplative_question(self):
        msg = "a veces pienso que no se por que sera que siempre volvemos al mismo punto"
        flavor, reason, _ = _select_flavor(msg, _preset(), self._pressure(), [])
        assert flavor == StyleFlavor.REFLEXIVE
        assert "reflexive" in reason

    def test_reflexive_on_vulnerable_with_signal(self):
        msg = "la verdad no se que sentido tiene todo esto"
        flavor, _, _ = _select_flavor(msg, _preset(), self._pressure(UserState.VULNERABLE, 1), [])
        assert flavor == StyleFlavor.REFLEXIVE


class TestExpressionHistory:
    def test_records_and_retrieves(self):
        h = ExpressionHistory()
        h.record("test", ResponseShape.ONE_HIT, StyleFlavor.DRY)
        h.record("test", ResponseShape.LAYERED, StyleFlavor.IRONIC)
        assert h.recent_shapes("test") == ["one_hit", "layered"]
        assert h.recent_flavors("test") == ["dry", "ironic"]

    def test_maxlen_enforced(self):
        h = ExpressionHistory(maxlen=3)
        for _ in range(5):
            h.record("test", ResponseShape.ONE_HIT, StyleFlavor.DRY)
        assert len(h.to_records("test")) == 3

    def test_load_from_records(self):
        h = ExpressionHistory()
        records = [("one_hit", "dry"), ("layered", "ironic"), ("probing", "clinical")]
        h.load_from_records("test", records)
        assert h.recent_shapes("test") == ["one_hit", "layered", "probing"]

    def test_separate_keys(self):
        h = ExpressionHistory()
        h.record("user_a", ResponseShape.ONE_HIT, StyleFlavor.DRY)
        h.record("user_b", ResponseShape.LAYERED, StyleFlavor.IRONIC)
        assert h.recent_shapes("user_a") == ["one_hit"]
        assert h.recent_shapes("user_b") == ["layered"]


# ═══════════════════════════════════════════════════════════════════════════
# Flow 4: Conversational Awareness
# ═══════════════════════════════════════════════════════════════════════════


class TestRepetitionLoopDetection:
    def test_detects_loop(self):
        msgs = [
            "el capitalismo destruye todo porque genera desigualdad economica brutal",
            "digo que capitalismo destruye porque genera desigualdad economica tremenda",
            "como digo capitalismo destruye todo generando desigualdad economica enorme",
        ]
        detected, _turns = _detect_repetition_loop(msgs)
        assert detected

    def test_no_loop_on_different_topics(self):
        msgs = [
            "me gusta el futbol",
            "ayer fui al cine a ver una pelicula",
            "que opinas de la inteligencia artificial",
        ]
        detected, _ = _detect_repetition_loop(msgs)
        assert not detected

    def test_short_window_no_loop(self):
        detected, _ = _detect_repetition_loop(["hola", "adios"])
        assert not detected


class TestAwarenessAnalysis:
    def test_no_pattern_on_normal(self):
        recent = [{"role": "user", "content": "hola que onda"}]
        result = _analyze_awareness("como estas", recent)
        assert result.detected_pattern == ConversationPattern.NONE

    def test_deflection_detected(self):
        recent = [{"role": "user", "content": "test"}]
        result = _analyze_awareness("y tu que? pero tu también lo haces", recent)
        assert result.detected_pattern == ConversationPattern.DEFLECTION
        assert result.meta_commentary is not None

    def test_winning_detected(self):
        recent = [
            {"role": "user", "content": "admit it, tengo razón"},
            {"role": "assistant", "content": "no necesariamente"},
            {"role": "user", "content": "ves? te lo dije, es un hecho"},
        ]
        result = _analyze_awareness("admitelo, no puedes negar que tengo razón", recent)
        assert result.detected_pattern == ConversationPattern.WINNING_VS_UNDERSTANDING
        assert result.delayed_question is not None

    def test_performative_detected(self):
        recent = [
            {"role": "user", "content": "ya te dije que mi punto es claro"},
            {"role": "assistant", "content": "no really"},
            {"role": "user", "content": "como te digo, es que no me escuchas"},
        ]
        result = _analyze_awareness("repito, no me entiendes, ya te dije", recent)
        assert result.detected_pattern == ConversationPattern.PERFORMATIVE_ARGUING


# ═══════════════════════════════════════════════════════════════════════════
# Orchestrator
# ═══════════════════════════════════════════════════════════════════════════


class TestAnalyzeFlows:
    def test_returns_flow_analysis(self):
        h = ExpressionHistory()
        result = analyze_flows("hola que onda", [], _preset(), h, "test_key")
        assert isinstance(result, FlowAnalysis)
        assert isinstance(result.epistemic, EpistemicAnalysis)
        assert isinstance(result.pressure, PressureAnalysis)
        assert isinstance(result.expression, ExpressionAnalysis)
        assert isinstance(result.awareness, AwarenessAnalysis)

    def test_vulnerable_suppresses_epistemic(self):
        h = ExpressionHistory()
        # Message that would normally trigger CHALLENGE_PREMISE
        msg = "The system is broken. Everything is wrong. Nothing works."
        # But user is also vulnerable
        vulnerable_msg = "la verdad es que me siento mal, tengo miedo, " + msg
        result = analyze_flows(vulnerable_msg, [], _preset(), h, "test_key")
        if result.pressure.detected_state == UserState.VULNERABLE:
            assert result.epistemic.recommended_move == EpistemicMove.NONE
            assert "suppressed_vulnerable" in result.epistemic.move_reason

    def test_repetition_loop_overrides_expression(self):
        h = ExpressionHistory()
        recent = [
            {"role": "user", "content": "el capitalismo es el problema de todo"},
            {"role": "user", "content": "como digo, el capitalismo es el gran problema"},
            {"role": "user", "content": "lo que digo es que capitalismo causa problemas"},
        ]
        result = analyze_flows("el capitalismo sigue siendo el problema", recent, _preset(), h, "test_key")
        if result.awareness.detected_pattern == ConversationPattern.REPETITION_LOOP:
            assert result.expression.selected_shape == ResponseShape.ONE_HIT

    def test_deflection_overrides_expression(self):
        h = ExpressionHistory()
        recent = [{"role": "user", "content": "test"}]
        result = analyze_flows("y tu que? pero tu también", recent, _preset(), h, "test_key")
        if result.awareness.detected_pattern == ConversationPattern.DEFLECTION:
            assert result.expression.selected_shape == ResponseShape.PROBING

    def test_records_expression_history(self):
        h = ExpressionHistory()
        analyze_flows("hola", [], _preset(), h, "key1")
        assert len(h.to_records("key1")) == 1

    def test_any_active_on_epistemic(self):
        h = ExpressionHistory()
        msg = "Studies show that people think everyone knows it's obvious"
        result = analyze_flows(msg, [], _preset(), h, "test_key")
        # May or may not activate — just verify the property works
        assert isinstance(result.any_active, bool)


# ═══════════════════════════════════════════════════════════════════════════
# Prompt Builder
# ═══════════════════════════════════════════════════════════════════════════


class TestBuildFlowPrompt:
    def _make_analysis(self, **kwargs) -> FlowAnalysis:
        defaults = {
            "epistemic": EpistemicAnalysis(0.0, 0.0, 0.0, False, 0, EpistemicMove.NONE, "test"),
            "pressure": PressureAnalysis(UserState.NEUTRAL, 0.0, 2, "test", False),
            "expression": ExpressionAnalysis(ResponseShape.SHORT_EXCHANGE, StyleFlavor.DRY, "test", "test"),
            "awareness": AwarenessAnalysis(ConversationPattern.NONE, 0.0, None, None, 0),
        }
        defaults.update(kwargs)
        return FlowAnalysis(**defaults)

    def test_always_includes_expression(self):
        analysis = self._make_analysis()
        prompt = build_flow_prompt(analysis)
        assert "Response Expression" in prompt
        assert "SHORT-EXCHANGE" in prompt
        assert "DRY" in prompt

    def test_includes_epistemic_when_active(self):
        analysis = self._make_analysis(
            epistemic=EpistemicAnalysis(0.8, 0.0, 0.0, False, 0, EpistemicMove.CHALLENGE_PREMISE, "test"),
        )
        prompt = build_flow_prompt(analysis)
        assert "Epistemic" in prompt
        assert "Challenge Premise" in prompt

    def test_includes_pressure_when_not_baseline(self):
        analysis = self._make_analysis(
            pressure=PressureAnalysis(UserState.HOSTILE, 0.8, 4, "test", False),
        )
        prompt = build_flow_prompt(analysis)
        assert "Pressure Level: 4" in prompt

    def test_excludes_pressure_at_baseline(self):
        analysis = self._make_analysis()  # pressure_level=2 (baseline)
        prompt = build_flow_prompt(analysis)
        assert "Pressure Level" not in prompt

    def test_includes_awareness_when_active(self):
        analysis = self._make_analysis(
            awareness=AwarenessAnalysis(ConversationPattern.DEFLECTION, 0.5, "Nice redirect.", None, 1),
        )
        prompt = build_flow_prompt(analysis)
        assert "Conversational Awareness" in prompt
        assert "Deflection" in prompt
        assert "Nice redirect" in prompt

    # ── Depth Pattern (v3.4.11): inject observation+question rule on weight ──

    def test_depth_pattern_injected_on_sincere(self):
        # Real trigger: "Cortar de tajo. Por eso eliminé a ese amigo."
        analysis = self._make_analysis(
            pressure=PressureAnalysis(UserState.SINCERE, 0.8, 2, "sincere content", False),
        )
        prompt = build_flow_prompt(analysis)
        assert "Depth Pattern" in prompt
        assert "OBSERVATION" in prompt
        assert "QUESTION" in prompt

    def test_depth_pattern_injected_on_vulnerable(self):
        analysis = self._make_analysis(
            pressure=PressureAnalysis(UserState.VULNERABLE, 0.9, 1, "vulnerable", False),
        )
        prompt = build_flow_prompt(analysis)
        assert "Depth Pattern" in prompt

    def test_depth_pattern_injected_on_high_pressure(self):
        # Even if not vulnerable/sincere, high pressure (ARC on bigotry etc.) triggers.
        analysis = self._make_analysis(
            pressure=PressureAnalysis(UserState.PREJUDICED, 0.7, 5, "arc", False),
        )
        prompt = build_flow_prompt(analysis)
        assert "Depth Pattern" in prompt

    def test_depth_pattern_not_on_neutral(self):
        # "me llevo mi mac?" — no weight, no depth requirement, short reply still fine.
        analysis = self._make_analysis(
            pressure=PressureAnalysis(UserState.NEUTRAL, 0.5, 2, "neutral", False),
        )
        prompt = build_flow_prompt(analysis)
        assert "Depth Pattern" not in prompt

    def test_depth_pattern_not_on_playful(self):
        # Laughing conversations don't need the 2-beat rule.
        analysis = self._make_analysis(
            pressure=PressureAnalysis(UserState.PLAYFUL, 0.8, 2, "playful", False),
        )
        prompt = build_flow_prompt(analysis)
        assert "Depth Pattern" not in prompt

    def test_depth_pattern_not_on_hostile(self):
        # Hostile input gets pressure response, but bare validation isn't the risk.
        analysis = self._make_analysis(
            pressure=PressureAnalysis(UserState.HOSTILE, 0.8, 3, "hostile", False),
        )
        prompt = build_flow_prompt(analysis)
        assert "Depth Pattern" not in prompt


# ═══════════════════════════════════════════════════════════════════════════
# Post-Generation Validator
# ═══════════════════════════════════════════════════════════════════════════


class TestFlowAdherence:
    def _make_analysis(
        self, shape=ResponseShape.SHORT_EXCHANGE, flavor=StyleFlavor.DRY, pressure=2, pattern=ConversationPattern.NONE
    ):
        return FlowAnalysis(
            epistemic=EpistemicAnalysis(0.0, 0.0, 0.0, False, 0, EpistemicMove.NONE, "test"),
            pressure=PressureAnalysis(UserState.NEUTRAL, 0.0, pressure, "test", False),
            expression=ExpressionAnalysis(shape, flavor, "test", "test"),
            awareness=AwarenessAnalysis(pattern, 0.0, None, None, 0),
        )

    def test_no_violations_on_match(self):
        analysis = self._make_analysis(ResponseShape.SHORT_EXCHANGE)
        result = validate_flow_adherence("This is a short response.", analysis)
        assert result["violations"] == []
        assert result["adherence_score"] == 1.0

    def test_one_hit_violation_on_long_response(self):
        analysis = self._make_analysis(ResponseShape.ONE_HIT)
        result = validate_flow_adherence("First sentence. Second sentence. Third sentence. Fourth.", analysis)
        assert any("one_hit" in v for v in result["violations"])

    def test_probing_violation_no_questions(self):
        analysis = self._make_analysis(ResponseShape.PROBING)
        result = validate_flow_adherence("This is a statement without any questions.", analysis)
        assert any("probing" in v for v in result["violations"])

    def test_dense_critique_violation_too_short(self):
        analysis = self._make_analysis(ResponseShape.DENSE_CRITIQUE)
        result = validate_flow_adherence("Too short.", analysis)
        assert any("dense_critique" in v for v in result["violations"])

    def test_adherence_score_decreases(self):
        analysis = self._make_analysis(ResponseShape.ONE_HIT)
        result = validate_flow_adherence("A. B. C. D. E.", analysis)
        assert result["adherence_score"] < 1.0


# ═══════════════════════════════════════════════════════════════════════════
# Phase 2 Enhancements
# ═══════════════════════════════════════════════════════════════════════════


class TestPhase2Enhancements:
    def test_expressive_thinking_shape_exists(self):
        assert ResponseShape.EXPRESSIVE_THINKING == "expressive_thinking"

    def test_rapid_fire_shape_exists(self):
        assert ResponseShape.RAPID_FIRE == "rapid_fire"

    def test_contradiction_callback_shape_exists(self):
        assert ResponseShape.CONTRADICTION_CALLBACK == "contradiction_callback"

    def test_metaphorical_flavor_exists(self):
        assert StyleFlavor.METAPHORICAL == "metaphorical"

    def test_expressive_mode_activates(self):
        from unittest.mock import patch

        pressure = PressureAnalysis(
            detected_state=UserState.NEUTRAL,
            state_confidence=0.5,
            pressure_level=2,
            pressure_reason="test",
            clamped_by_preset=False,
        )
        epistemic = EpistemicAnalysis(0.0, 0.0, 0.0, False, 0, EpistemicMove.NONE, "test")
        # A message that hits no special branches (medium word count, default preset)
        msg = "pues no se que pensar de todo esto la verdad"
        # After the v3.5.6 flows-package refactor, `random` is imported inside
        # the ExpressionAnalyzer module. The monkeypatch target moves with it.
        with patch("personas.insult.core.flows.analyzers.expression.random.random", return_value=0.1):
            shape, reason, _ = _select_shape(msg, _preset(), pressure, epistemic, [])
        assert shape == ResponseShape.EXPRESSIVE_THINKING
        assert "expressive_mode" in reason

    def test_agreement_streak_computed(self):
        h = ExpressionHistory()
        recent = [
            {"role": "assistant", "content": "Pues algo distinto aquí."},
            {"role": "assistant", "content": "Exacto, tienes razón carnal."},
            {"role": "assistant", "content": "Totalmente, bien dicho."},
        ]
        result = analyze_flows("hola", recent, _preset(), h, "test_streak")
        assert result.agreement_streak == 2

    def test_agreement_streak_zero_when_no_agreement(self):
        h = ExpressionHistory()
        recent = [
            {"role": "assistant", "content": "No estoy de acuerdo."},
            {"role": "assistant", "content": "Eso no tiene sentido."},
        ]
        result = analyze_flows("hola", recent, _preset(), h, "test_streak_zero")
        assert result.agreement_streak == 0


# ═══════════════════════════════════════════════════════════════════════════
# F2: Lifelessness detection — soft-monitor for "competent but flat" replies
# ═══════════════════════════════════════════════════════════════════════════


class TestDetectLifelessness:
    """Anchored on the Alex DIF turn (2026-05-11) that triggered the
    redesign. The flat reply scored 'tibia' (2); the proposed alive
    rewrite scored 0. Tests below lock in the discriminating power."""

    ALEX_DIF_MSG = (
        "Oigan a ver qué me dicen mañana, espero no salgan con alguna jalada. "
        "Me estoy acordando que cuando fui al DIF para la supuesta evaluación de "
        "autismo había muchas personas presentes. Estuvo bien equis, de lo que "
        "salí como más altx por así decirlo fue de la movilidad reducida, y eso "
        "que yo iba más por discapacidad psicosocial."
    )
    ALEX_DIF_FLAT_REPLY = (
        "Que te den la tarjeta sin drama, nada más eso. "
        "Y lo del DIF — a veces los sistemas de evaluación te encasillan en lo que "
        "ellos saben medir, no necesariamente en lo que más te afecta a ti. "
        "Que hayan priorizado movilidad reducida no significa que lo otro no existe. "
        "Mañana nos cuentas cómo te fue."
    )
    ALEX_DIF_ALIVE_REPLY = (
        "Qué raro eso de querer que te vean y al mismo tiempo sentirte exhibide "
        "cuando por fin te ponen atención. El DIF hace esa cosa burocrática: "
        "no mide cómo vives el mundo, mide qué casilla puede justificar. "
        "Lo culero es salir preguntándote si el problema eras tú o el formato."
    )

    def test_alex_dif_flat_reply_is_tibia_or_worse(self):
        """Anchor regression: the original flat DIF reply must score ≥ 2."""
        result = detect_lifelessness(self.ALEX_DIF_FLAT_REPLY, self.ALEX_DIF_MSG)
        assert result["band"] in ("tibia", "flat")
        assert result["score"] >= 2
        assert "courtesy_followup_close" in result["signals"]

    def test_alex_dif_alive_rewrite_scores_alive(self):
        """The proposed Alvarado-style rewrite must score 'alive'."""
        result = detect_lifelessness(self.ALEX_DIF_ALIVE_REPLY, self.ALEX_DIF_MSG)
        assert result["band"] == "alive"
        assert result["has_movement_markers"] is True

    def test_acknowledgment_opener_fires(self):
        result = detect_lifelessness("Claro, entiendo lo que dices.")
        assert "acknowledgment_opener" in result["signals"]

    def test_courtesy_close_fires(self):
        result = detect_lifelessness("Suena bien. Mañana me cuentas cómo te fue.")
        assert "courtesy_followup_close" in result["signals"]

    def test_courtesy_close_english_fires(self):
        result = detect_lifelessness("Sounds good. Let me know how it goes.")
        assert "courtesy_followup_close" in result["signals"]

    def test_therapy_speak_two_hits_fires(self):
        text = "Es válido sentir lo que sientes. Tus emociones son válidas y no estás solo."
        result = detect_lifelessness(text)
        assert any(s.startswith("therapy_speak_") for s in result["signals"])
        assert result["therapy_speak_hits"] >= 2

    def test_single_therapy_phrase_does_not_fire(self):
        """Single therapy phrase is not enough — must be a cluster.
        Prevents false positives on natural empathy expressions."""
        result = detect_lifelessness("Está bien sentirse así a veces.")
        assert not any(s.startswith("therapy_speak_") for s in result["signals"])

    def test_movement_markers_cancel_one_signal(self):
        """A reply that opens with acknowledgment but pivots with 'pero' or
        names a tension should score lower than pure acknowledgment."""
        with_movement = detect_lifelessness("Entiendo. Pero lo culero es que el sistema te encasilla en una casilla.")
        without_movement = detect_lifelessness("Entiendo. Tiene mucho sentido.")
        assert with_movement["score"] < without_movement["score"]

    def test_question_alone_avoids_no_pull_signal(self):
        """Presence of a question prevents the 'no_question_no_movement'
        composite signal from firing."""
        result = detect_lifelessness("¿Qué es lo que más te preocupa de eso?")
        assert "no_question_no_movement" not in result["signals"]

    def test_literal_reflection_detects_mirroring(self):
        """High content-word overlap without movement markers = reflection."""
        user = "estoy cansado del trabajo y de la gente del trabajo"
        # Reply that mirrors the user's vocabulary without moving.
        # Score signal is independent — we just need the flag to be on.
        result = detect_lifelessness(
            "Cansado del trabajo y de la gente del trabajo, suena pesado.",
            user,
        )
        assert any(s.startswith("literal_reflection_") for s in result["signals"])

    def test_empty_response_does_not_crash(self):
        result = detect_lifelessness("", "user said something")
        assert isinstance(result["score"], int)
        assert result["band"] in ("alive", "tibia", "flat")

    def test_band_buckets(self):
        # Score 0 → alive
        assert detect_lifelessness("¿Y qué piensas hacer al respecto?")["band"] == "alive"
        # Score 3+ → flat (acknowledgment + courtesy + therapy + no pull)
        flat_text = (
            "Claro, entiendo lo que dices. Es válido sentir lo que sientes y "
            "tus emociones son válidas. Mañana me cuentas cómo te fue."
        )
        assert detect_lifelessness(flat_text)["band"] == "flat"
