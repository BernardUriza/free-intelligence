"""Tests for insult.core.snooze — emoji→delta mapping for reminder snooze."""

from personas.insult.core.snooze import SNOOZE_DELTAS_SECONDS, SNOOZE_EMOJIS, snooze_delta_for_emoji


def test_clock_emoji_maps_to_10_minutes():
    assert snooze_delta_for_emoji("⏰") == 600


def test_skip_emoji_maps_to_one_hour():
    # Both with and without variation selector
    assert snooze_delta_for_emoji("⏭️") == 3600
    assert snooze_delta_for_emoji("⏭") == 3600


def test_calendar_emoji_maps_to_one_day():
    assert snooze_delta_for_emoji("📅") == 86400


def test_unknown_emoji_returns_none():
    assert snooze_delta_for_emoji("✅") is None
    assert snooze_delta_for_emoji("🔥") is None
    assert snooze_delta_for_emoji("") is None


def test_snooze_emojis_tuple_matches_keys():
    """SNOOZE_EMOJIS is the canonical display order — every entry must be a key
    in SNOOZE_DELTAS_SECONDS so the listener can map all three back."""
    for emoji in SNOOZE_EMOJIS:
        assert emoji in SNOOZE_DELTAS_SECONDS


def test_no_overlap_with_ack_emoji():
    """The ack flow (#5) reserves ✅. Snooze must not steal it."""
    assert "✅" not in SNOOZE_DELTAS_SECONDS
    assert "✅" not in SNOOZE_EMOJIS
