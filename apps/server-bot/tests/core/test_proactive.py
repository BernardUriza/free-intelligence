"""La proactividad decide CUÁNDO se puede hablar sin que nadie te hable.

Resucita `tests/core/test_proactive.py`, que la purga `2f8d9ad` borró (481
líneas) junto con el módulo que probaba. El sistema quedó incapaz de arrancar
una sola conversación por sí mismo y nadie se enteró durante tres semanas,
porque un silencio no dispara ninguna alarma.

Cada compuerta se prueba con su caso positivo Y su resistencia: la que importa
no es "sabe hablar", es "sabe CALLARSE" — sobre un canal vivo, de madrugada, y
cuando ya habló tres veces sin que nadie contestara.
"""

from __future__ import annotations

import pytest

from persona_core.proactive import (
    ACTIVE_THRESHOLD,
    BASE_INTERVAL_HOURS,
    COOLING_THRESHOLD,
    MAX_INTERVAL_HOURS,
    ConversationState,
    compute_backoff_interval,
    get_conversation_state,
    should_send_now,
    should_world_scan,
)

NOW = 1_800_000_000.0


class TestConversationState:
    def test_a_channel_nobody_ever_wrote_in_is_idle(self):
        assert get_conversation_state(None, now=NOW) is ConversationState.IDLE

    def test_someone_speaking_right_now_is_active(self):
        assert get_conversation_state(NOW - 60, now=NOW) is ConversationState.ACTIVE

    def test_just_under_the_active_threshold_is_still_active(self):
        assert get_conversation_state(NOW - (ACTIVE_THRESHOLD - 1), now=NOW) is ConversationState.ACTIVE

    def test_past_the_active_threshold_it_is_cooling_not_idle(self):
        """RESISTENCIA: 16 minutos de silencio NO es una invitación a hablar —
        la conversación acaba de terminar y merece asentarse."""
        assert get_conversation_state(NOW - (ACTIVE_THRESHOLD + 1), now=NOW) is ConversationState.COOLING_DOWN

    def test_past_the_cooling_threshold_it_is_idle(self):
        assert get_conversation_state(NOW - (COOLING_THRESHOLD + 1), now=NOW) is ConversationState.IDLE


class TestBackoff:
    def test_the_first_proactive_waits_the_base_interval(self):
        assert compute_backoff_interval(0) == BASE_INTERVAL_HOURS

    @pytest.mark.parametrize(
        ("unanswered", "hours"),
        [(0, 2.0), (1, 4.0), (2, 8.0), (3, 16.0)],
    )
    def test_each_ignored_proactive_doubles_the_wait(self, unanswered: int, hours: float):
        assert compute_backoff_interval(unanswered) == hours

    def test_the_wait_is_capped_so_it_never_goes_silent_forever(self):
        assert compute_backoff_interval(50) == MAX_INTERVAL_HOURS

    def test_a_negative_count_cannot_shorten_the_wait(self):
        """RESISTENCIA: un contador corrupto no debe convertirse en una licencia
        para hablar más seguido que el intervalo base."""
        assert compute_backoff_interval(-5) == BASE_INTERVAL_HOURS


class TestShouldSendNow:
    def test_it_speaks_when_every_gate_is_open(self):
        assert should_send_now(
            hour=14,
            last_proactive_ts=None,
            last_user_message_ts=NOW - (COOLING_THRESHOLD + 1),
            now=NOW,
            roll=0.0,
        )

    @pytest.mark.parametrize("hour", [3, 4, 5, 6])
    def test_it_stays_quiet_at_dawn(self, hour: int):
        """RESISTENCIA: 3-7am es silencio absoluto. Vultur ya despertó a Bernard
        a las 3am dos noches seguidas (765f125) y eso no se repite."""
        assert not should_send_now(
            hour=hour,
            last_proactive_ts=None,
            last_user_message_ts=NOW - (COOLING_THRESHOLD + 1),
            now=NOW,
            roll=0.0,
        )

    @pytest.mark.parametrize("hour", [2, 7])
    def test_the_quiet_window_does_not_bleed_past_its_edges(self, hour: int):
        assert should_send_now(
            hour=hour,
            last_proactive_ts=None,
            last_user_message_ts=NOW - (COOLING_THRESHOLD + 1),
            now=NOW,
            roll=0.0,
        )

    def test_it_never_interrupts_a_live_conversation(self):
        """RESISTENCIA: la falla más cara de un bot proactivo es meterse a media
        conversación humana."""
        assert not should_send_now(
            hour=14,
            last_proactive_ts=None,
            last_user_message_ts=NOW - 60,
            now=NOW,
            roll=0.0,
        )

    def test_it_lets_a_just_ended_conversation_settle(self):
        assert not should_send_now(
            hour=14,
            last_proactive_ts=None,
            last_user_message_ts=NOW - (ACTIVE_THRESHOLD + 60),
            now=NOW,
            roll=0.0,
        )

    def test_it_respects_the_backoff_after_being_ignored(self):
        """Tres proactivos sin respuesta → 16h de espera. A las 5h todavía no."""
        assert not should_send_now(
            hour=14,
            last_proactive_ts=NOW - (5 * 3600),
            last_user_message_ts=NOW - (COOLING_THRESHOLD + 1),
            unanswered_count=3,
            now=NOW,
            roll=0.0,
        )

    def test_it_speaks_again_once_the_backoff_elapsed(self):
        assert should_send_now(
            hour=14,
            last_proactive_ts=NOW - (17 * 3600),
            last_user_message_ts=NOW - (COOLING_THRESHOLD + 1),
            unanswered_count=3,
            now=NOW,
            roll=0.0,
        )

    def test_an_unlucky_roll_keeps_it_quiet_even_with_every_gate_open(self):
        """La probabilidad es la última compuerta: que sea lícito hablar no
        significa que toque. Sin esto la proactividad es un metrónomo."""
        assert not should_send_now(
            hour=14,
            last_proactive_ts=None,
            last_user_message_ts=NOW - (COOLING_THRESHOLD + 1),
            now=NOW,
            roll=0.99,
        )

    def test_quiet_hours_beat_everything_else(self):
        """RESISTENCIA: ninguna compuerta posterior puede reabrir la madrugada."""
        assert not should_send_now(
            hour=4,
            last_proactive_ts=NOW - (100 * 3600),
            last_user_message_ts=None,
            unanswered_count=0,
            now=NOW,
            roll=0.0,
        )


class TestWorldScan:
    def test_a_low_roll_goes_looking_at_the_world(self):
        assert should_world_scan(roll=0.0)

    def test_a_high_roll_just_says_hi(self):
        assert not should_world_scan(roll=0.99)

    def test_socialising_is_the_majority_mode(self):
        """El reparto del original: ~30% investiga, ~70% socializa. Si alguien
        invierte la constante, esto lo caza."""
        assert should_world_scan(roll=0.29)
        assert not should_world_scan(roll=0.31)
