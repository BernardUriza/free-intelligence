"""The 2026-08-03 regression: a revoked token answered HTTP 200 as if it were prose.

Positive case: the exact payload the SDK produced while the personas were mute.
Resistance case: a persona legitimately TALKING about a 401 must never be caught
— the discriminator is that a real turn always bills tokens.
"""

from __future__ import annotations

import pytest

from persona_runner.engine import auth_failure


def _state(text: str, **over):
    base = {"text": text, "input_tokens": 0, "output_tokens": 0, "tool_calls": []}
    base.update(over)
    return base


REVOKED = "Failed to authenticate. API Error: 401 OAuth access token has been revoked."


def test_detects_the_exact_outage_payload():
    assert auth_failure.looks_like_credential_failure(_state(REVOKED)) is True


@pytest.mark.parametrize(
    "text",
    [
        "Failed to authenticate. API Error: 401 OAuth access token has expired.",
        "API Error: 403 authentication_error",
        "Invalid bearer token",
    ],
)
def test_detects_credential_error_variants(text):
    assert auth_failure.looks_like_credential_failure(_state(text)) is True


def test_resists_a_persona_discussing_a_401():
    """A real answer bills input tokens — that is what makes it a real answer."""
    state = _state(
        "Tu curl devolvió 401 OAuth access token has been revoked porque el token murió.",
        input_tokens=812,
        output_tokens=140,
    )
    assert auth_failure.looks_like_credential_failure(state) is False


def test_resists_a_turn_that_ran_tools():
    state = _state(REVOKED, tool_calls=[{"name": "mcp__persona_memory__facts"}])
    assert auth_failure.looks_like_credential_failure(state) is False


def test_ignores_an_ordinary_empty_or_normal_turn():
    assert auth_failure.looks_like_credential_failure(_state("")) is False
    assert auth_failure.looks_like_credential_failure(_state("Despierto. ᵛ⁴·³²·¹⁵")) is False


def test_failure_state_round_trip():
    auth_failure.clear_failure()
    assert auth_failure.last_failure() is None
    auth_failure.mark_failure(REVOKED)
    recorded = auth_failure.last_failure()
    assert recorded is not None and "revoked" in recorded["detail"]
    auth_failure.clear_failure()
    assert auth_failure.last_failure() is None
