"""Tests for the pure activity-text builder and status mapping."""

from __future__ import annotations

import discord

from personas.insult.core.siesta.presence.discord import build_activity_text, status_for
from personas.insult.core.siesta.state import AWAKE, SiestaPhase, SiestaSnapshot


def test_build_text_empty_when_awake():
    assert build_activity_text(AWAKE) == ""


def test_build_text_includes_progress_when_known():
    snap = SiestaSnapshot(phase=SiestaPhase.LIGHT, total_users=4, processed_users=1)
    text = build_activity_text(snap)
    assert "🛌" in text
    assert "1/4" in text
    assert "25%" in text


def test_build_text_falls_back_to_phase_label_without_total():
    snap = SiestaSnapshot(phase=SiestaPhase.REM)
    text = build_activity_text(snap)
    assert "🛌" in text
    # No counts suffix when total is 0.
    assert "/" not in text
    assert "%" not in text


def test_build_text_within_discord_custom_status_cap():
    # Discord caps custom status at 128 chars. Our format must not exceed it
    # even with a worst-case 999/999 (100%) and the longest phase label.
    snap = SiestaSnapshot(
        phase=SiestaPhase.REM,  # longest label
        total_users=999,
        processed_users=999,
    )
    assert len(build_activity_text(snap)) <= 128


def test_status_idle_during_active_siesta():
    snap = SiestaSnapshot(phase=SiestaPhase.LIGHT, total_users=2, processed_users=0)
    assert status_for(snap) is discord.Status.idle


def test_status_online_when_awake():
    assert status_for(AWAKE) is discord.Status.online
