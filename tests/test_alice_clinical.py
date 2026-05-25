"""Tests for ALICE's Clinical Reflection Layer routing (the backend clínico).

The safety-critical invariant: the clinical reflection is metacognitive and goes
ONLY to the clinician-only channel — NEVER to the patient's channel. These tests
drive `AliceChatCog._post_clinical_reflection` directly with mocks (no Azure, no
Discord) to lock that invariant and the CRITICAL-risk header.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import discord
import pytest
from fi_core.cognitive import PSYCHIATRY, PatientContext

from alice.cogs.chat import AliceChatCog
from alice.core.clinical_reflection import ClinicalReflection

CLINIC_CHANNEL_ID = "999"


def _triage(*symptoms: str):
    return PSYCHIATRY.urgency_classifier().classify(PatientContext(symptoms=list(symptoms)))


def _make_cog(clinical_channel, *, reflection_text="**Lectura clínica**\nx", triage=None):
    clinical = MagicMock()
    clinical.reflect = AsyncMock(
        return_value=ClinicalReflection(
            text=reflection_text,
            model="gpt-4.1",
            input_tokens=100,
            output_tokens=20,
            latency_ms=500,
            triage=triage,
        )
    )
    bot = MagicMock()
    bot.get_channel = MagicMock(return_value=clinical_channel)
    cog = AliceChatCog(
        bot=bot,
        memory=MagicMock(),
        llm=MagicMock(),
        persona=MagicMock(),
        clinical=clinical,
        clinical_channel_id=CLINIC_CHANNEL_ID,
    )
    return cog, bot


async def test_reflection_posts_to_clinician_channel_only():
    """The reflection is sent to the configured clinician channel, by its ID."""
    sent: list[str] = []
    channel = MagicMock(spec=discord.abc.Messageable)
    channel.send = AsyncMock(side_effect=lambda c: sent.append(c))
    cog, bot = _make_cog(channel, triage=_triage("ansiedad"))

    await cog._post_clinical_reflection([{"role": "user", "content": "tengo ansiedad"}], origin="#sala")

    bot.get_channel.assert_called_once_with(int(CLINIC_CHANNEL_ID))
    assert sent, "expected the reflection to be posted"
    assert "Reflexión clínica" in sent[0]


async def test_critical_triage_adds_risk_header():
    """An active-crisis triage prepends the CRITICAL risk banner."""
    sent: list[str] = []
    channel = MagicMock(spec=discord.abc.Messageable)
    channel.send = AsyncMock(side_effect=lambda c: sent.append(c))
    cog, _ = _make_cog(channel, triage=_triage("plan suicida"))

    await cog._post_clinical_reflection([{"role": "user", "content": "tengo un plan"}], origin="#sala")

    assert sent and "RIESGO CRÍTICO" in sent[0]
    assert "CRITICAL" in sent[0]


async def test_no_leak_when_clinician_channel_unavailable():
    """If the clinician channel can't be resolved, the reflection is dropped — never
    rerouted to the patient. A leak would break the whole dual-layer design."""
    cog, bot = _make_cog(None)  # get_channel returns None
    bot.fetch_channel = AsyncMock(side_effect=discord.HTTPException(MagicMock(), "not found"))

    # Must not raise, and must not post anywhere.
    await cog._post_clinical_reflection([{"role": "user", "content": "hola"}], origin="#sala")
    bot.fetch_channel.assert_awaited_once()


async def test_reflection_failure_is_swallowed():
    """A backend failure in the clinical layer never crashes the turn."""
    cog, _ = _make_cog(MagicMock(spec=discord.abc.Messageable))
    cog.clinical.reflect = AsyncMock(side_effect=RuntimeError("codex boom"))

    # Should log and return, not raise.
    await cog._post_clinical_reflection([{"role": "user", "content": "hola"}], origin="#sala")


def test_clinical_layer_disabled_without_channel():
    """No clinician channel configured -> the cog holds no reflector wiring."""
    cog = AliceChatCog(
        bot=MagicMock(),
        memory=MagicMock(),
        llm=MagicMock(),
        persona=MagicMock(),
    )
    assert cog.clinical is None
    assert cog.clinical_channel_id == ""


def test_psychiatry_triage_differentiates_severity():
    """The fi-core PSYCHIATRY domain separates crisis from distress from non-clinical."""
    assert _triage("plan suicida").level.value == "CRITICAL"
    assert _triage("ideación suicida pasiva").level.value == "HIGH"
    assert _triage("ataque de pánico").level.value == "MEDIUM"
    assert _triage("contratos con inconsistencias").level.value == "LOW"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
