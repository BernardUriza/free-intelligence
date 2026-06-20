"""Canary probe runner — success criterion is verified by ID + nonce, never content.

The runner accepts a CANARY_OK reply ONLY when all three hold: author is the
Insult bot user id, channel is the canary channel, and the nonce echoes the one
the probe posted. An impostor bot, the wrong channel, or a stale nonce all fail.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import scripts.canary_probe as canary_probe
from scripts.canary_probe import EXIT_OK, EXIT_TIMEOUT, reply_matches, run_probe

INSULT_ID = "1490000000000000009"
CANARY_CHANNEL = "1490000000000000001"


def _matches(*, author_id, channel_id, content, expected_nonce="n1"):
    return reply_matches(
        author_id=author_id,
        channel_id=channel_id,
        content=content,
        expected_nonce=expected_nonce,
        insult_bot_user_id=INSULT_ID,
        canary_channel_id=CANARY_CHANNEL,
    )


def test_accepts_insult_reply_with_matching_nonce():
    assert _matches(author_id=int(INSULT_ID), channel_id=int(CANARY_CHANNEL), content="CANARY_OK n1") is True


def test_rejects_wrong_author_even_with_right_content():
    assert _matches(author_id=999, channel_id=int(CANARY_CHANNEL), content="CANARY_OK n1") is False


def test_rejects_wrong_channel():
    assert _matches(author_id=int(INSULT_ID), channel_id=999, content="CANARY_OK n1") is False


def test_rejects_stale_nonce():
    assert _matches(author_id=int(INSULT_ID), channel_id=int(CANARY_CHANNEL), content="CANARY_OK other") is False


def test_rejects_non_canary_content():
    assert _matches(author_id=int(INSULT_ID), channel_id=int(CANARY_CHANNEL), content="hello") is False


# --- REST-only transport: the probe must never open a Discord Gateway session ---


def test_probe_is_rest_only_no_gateway():
    """The poster token is reused from a live bot (Vultur); a second Gateway
    IDENTIFY would flap it. The runner must touch ONLY the REST API."""
    src = Path(canary_probe.__file__).read_text(encoding="utf-8")
    assert "client.start" not in src
    assert "discord.Client" not in src
    assert "discord.Intents" not in src
    assert "aiohttp" in src
    assert "/channels/" in src  # REST message endpoints


class _FakeResp:
    def __init__(self, status, json_data=None, text_data=""):
        self.status = status
        self._json = json_data if json_data is not None else {}
        self._text = text_data

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def json(self):
        return self._json

    async def text(self):
        return self._text


class _FakeSession:
    def __init__(self, post_resp, get_responses):
        self._post = post_resp
        self._gets = list(get_responses)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    def post(self, _url, **_kw):
        return self._post

    def get(self, _url, **_kw):
        return self._gets.pop(0) if self._gets else _FakeResp(200, [])


class _FixedUUID:
    hex = "deadbeefcafe99"  # [:12] -> "deadbeefcafe"


def _patch(monkeypatch, *, post_resp, get_responses):
    monkeypatch.setattr(canary_probe.uuid, "uuid4", lambda: _FixedUUID())
    monkeypatch.setattr(canary_probe, "_POLL_INTERVAL_SECONDS", 0.0)
    monkeypatch.setattr(
        canary_probe.aiohttp,
        "ClientSession",
        lambda *a, **k: _FakeSession(post_resp, get_responses),
    )


@pytest.mark.asyncio
async def test_run_probe_ok_when_insult_echoes_nonce(monkeypatch):
    nonce = "deadbeefcafe"
    _patch(
        monkeypatch,
        post_resp=_FakeResp(201, {"id": "100"}),
        get_responses=[
            _FakeResp(
                200,
                [{"author": {"id": INSULT_ID}, "channel_id": CANARY_CHANNEL, "content": f"CANARY_OK {nonce}"}],
            )
        ],
    )
    code = await run_probe(token="t", channel_id=CANARY_CHANNEL, insult_bot_user_id=INSULT_ID, timeout_seconds=5)
    assert code == EXIT_OK


@pytest.mark.asyncio
async def test_run_probe_timeout_when_no_reply(monkeypatch):
    _patch(
        monkeypatch,
        post_resp=_FakeResp(201, {"id": "100"}),
        get_responses=[_FakeResp(200, [])],  # then the session yields empty pages
    )
    code = await run_probe(token="t", channel_id=CANARY_CHANNEL, insult_bot_user_id=INSULT_ID, timeout_seconds=0.05)
    assert code == EXIT_TIMEOUT
