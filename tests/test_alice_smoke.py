"""Smoke tests for ALICE — imports + pure-function paths.

Full integration (Postgres + OpenAI + Discord) tests live separately
once ALICE has prod traffic. v0.1.0 ships with this minimum bar:

1. All ALICE modules import cleanly (no syntax errors, no missing deps).
2. `_chunk_text` splits long text on paragraph boundaries.
3. `_full_jitter` and `_parse_retry_after` behave as specified.
4. `INVOKE_ALICE_TOOL` schema is well-formed (Anthropic tool_use shape).
5. The FastAPI `/invite` endpoint rejects unauthorized requests.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


def test_alice_package_imports_cleanly():
    """All ALICE modules load without ImportError."""
    import alice
    from alice import bot, config  # noqa: F401
    from alice.api import server  # noqa: F401
    from alice.cogs import chat  # noqa: F401
    from alice.core import llm, memory, persona_loader  # noqa: F401

    assert alice.__version__ == "0.1.0"


def test_insult_to_alice_bridge_imports_cleanly():
    """Insult's side of the bridge loads."""
    from insult.core.alice_tool import INVOKE_ALICE_TOOL, execute_invoke_alice  # noqa: F401


# ---------------------------------------------------------------------------
# alice.core.llm — retry helpers (pure functions)
# ---------------------------------------------------------------------------


def test_full_jitter_within_cap():
    """Backoff never exceeds the configured cap, never goes negative."""
    from alice.core.llm import _MAX_BACKOFF_SECONDS, _full_jitter

    for attempt in range(1, 10):
        val = _full_jitter(attempt)
        assert 0 <= val <= _MAX_BACKOFF_SECONDS


def test_parse_retry_after_returns_none_when_header_missing():
    from alice.core.llm import _parse_retry_after

    err = MagicMock()
    err.response = MagicMock()
    err.response.headers = {}
    assert _parse_retry_after(err) is None


def test_parse_retry_after_caps_absurd_values():
    """A retry-after of 9999s is bogus; we ignore it so the bot doesn't freeze."""
    from alice.core.llm import _parse_retry_after

    err = MagicMock()
    err.response = MagicMock()
    err.response.headers = {"retry-after": "9999"}
    assert _parse_retry_after(err) is None  # outside [0, 60] sanity window


def test_parse_retry_after_honored_in_range():
    from alice.core.llm import _parse_retry_after

    err = MagicMock()
    err.response = MagicMock()
    err.response.headers = {"retry-after": "12"}
    assert _parse_retry_after(err) == 12.0


# ---------------------------------------------------------------------------
# alice.cogs.chat — _chunk_text (pure function)
# ---------------------------------------------------------------------------


def test_chunk_text_short_returns_single_chunk():
    from shared.text import chunk_paragraph_aware

    out = chunk_paragraph_aware("short message", max_chars=1900)
    assert out == ["short message"]


def test_chunk_text_breaks_on_paragraph():
    """Long text splits on `\\n\\n` boundary when one exists below the cap."""
    from shared.text import chunk_paragraph_aware

    text = ("a" * 500) + "\n\n" + ("b" * 500) + "\n\n" + ("c" * 500)
    out = chunk_paragraph_aware(text, max_chars=600)
    assert len(out) >= 2
    # No chunk exceeds the cap.
    assert all(len(c) <= 600 for c in out)


def test_chunk_text_falls_back_to_hard_split_when_no_break_exists():
    from shared.text import chunk_paragraph_aware

    text = "x" * 5000
    out = chunk_paragraph_aware(text, max_chars=1900)
    assert len(out) == 3
    assert all(len(c) <= 1900 for c in out)


# ---------------------------------------------------------------------------
# insult.core.alice_tool — schema shape
# ---------------------------------------------------------------------------


def test_invoke_alice_tool_schema_is_anthropic_shaped():
    """Tool def must have name, description, input_schema with `reason` required."""
    from insult.core.alice_tool import INVOKE_ALICE_TOOL

    assert INVOKE_ALICE_TOOL["name"] == "invoke_alice"
    assert "description" in INVOKE_ALICE_TOOL
    schema = INVOKE_ALICE_TOOL["input_schema"]
    assert schema["type"] == "object"
    assert "reason" in schema["properties"]
    assert "reason" in schema["required"]


# ---------------------------------------------------------------------------
# alice.api.server — /invite auth
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invite_rejects_missing_bearer():
    """No Authorization header → 401."""
    from fastapi.testclient import TestClient

    from alice.api.server import build_app

    container = _build_test_container(token="real-token-xyz")
    app = build_app(container)
    client = TestClient(app)

    resp = client.post("/invite", json={"channel_id": "c", "reason": "x" * 30})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_invite_rejects_wrong_bearer():
    from fastapi.testclient import TestClient

    from alice.api.server import build_app

    container = _build_test_container(token="real-token-xyz")
    app = build_app(container)
    client = TestClient(app)

    resp = client.post(
        "/invite",
        json={"channel_id": "c", "reason": "x" * 30},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_invite_accepts_valid_token_and_schedules_task():
    from fastapi.testclient import TestClient

    from alice.api.server import build_app

    cog_mock = MagicMock()
    cog_mock.respond_to_invite = AsyncMock(return_value="ok")

    container = _build_test_container(token="real-token-xyz")
    container.bot._alice_chat_cog = cog_mock

    app = build_app(container)
    client = TestClient(app)

    resp = client.post(
        "/invite",
        json={
            "channel_id": "1489180895264116736",
            "guild_id": "g",
            "channel_name": "general",
            "reason": "Alex está describiendo síntomas que necesitan tu mirada clínica, no la mía.",
        },
        headers={"Authorization": "Bearer real-token-xyz"},
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "invited"
    assert data["channel_id"] == "1489180895264116736"


@pytest.mark.asyncio
async def test_invite_503_when_no_token_configured():
    """Container with empty token = endpoint refuses to serve until configured."""
    from fastapi.testclient import TestClient

    from alice.api.server import build_app

    container = _build_test_container(token="")
    app = build_app(container)
    client = TestClient(app)

    resp = client.post(
        "/invite",
        json={"channel_id": "c", "reason": "x" * 30},
        headers={"Authorization": "Bearer anything"},
    )
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_health_endpoint_is_public_and_200():
    from fastapi.testclient import TestClient

    from alice.api.server import build_app

    container = _build_test_container(token="t")
    app = build_app(container)
    client = TestClient(app)

    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _build_test_container(*, token: str):
    """Construct a minimal container with mocks for unit tests."""
    from alice.config import AliceSettings

    container = MagicMock()
    container.settings = AliceSettings(insult_to_alice_token=token)
    container.bot = MagicMock()
    container.bot._alice_chat_cog = None  # tests override per case
    return container
