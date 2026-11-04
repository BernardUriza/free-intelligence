"""The wire contract of /v1/turn: a field nobody reads is an error, never a silent no-op."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from persona_runner.core.schemas import TurnRequest

BASE = {"channel_id": "c", "user_id": "u", "user_text": "hola"}


def test_an_unknown_field_is_rejected_instead_of_silently_dropped():
    """2026-11-04: a probe sent `model` to pin Opus, got a 200, and ran on Haiku."""
    with pytest.raises(ValidationError, match="model"):
        TurnRequest(**BASE, model="claude-opus-4-7")


def test_the_gateway_payload_still_validates():
    TurnRequest(
        **BASE,
        job_id="j1",
        persona_id="insult",
        attachments=[{"type": "image"}],
        behavioral_guidance="g",
        session_uuid="s",
    )


def test_the_og118_payload_still_validates():
    TurnRequest(
        **BASE,
        persona_id="yodo",
        surface="og118",
        job_id="j2",
        session_uuid="s",
        pipeline="runner",
        history=[{"role": "user", "content": "x"}],
    )


def test_the_probe_payload_still_validates():
    TurnRequest(
        channel_id="probe-x",
        user_id="probe-claude",
        user_name="probe-claude",
        user_text="hola",
        surface="og118",
        pipeline="runner",
        origin="probe",
        persona_id="frugivoro",
    )
