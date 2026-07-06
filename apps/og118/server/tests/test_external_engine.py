"""external_engine — the external_http_engine proxy (ENGINE-BINDING-ADR-1).

The happy path is live-verified (Oxígeno → Vultur). These cover the failure
branches the live test never exercised: unconfigured, transport error, non-200,
empty body — and the hard invariant that the bearer token NEVER reaches a
client-facing error message.
"""

from __future__ import annotations

import httpx
import pytest

import external_engine


class _FakeResp:
    def __init__(self, status: int, payload: object) -> None:
        self.status_code = status
        self._payload = payload

    def json(self) -> object:
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def _client_factory(*, resp: _FakeResp | None = None, raise_exc: Exception | None = None, sent: dict | None = None):
    class _FakeClient:
        def __init__(self, *a, **k) -> None: ...

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a) -> bool:
            return False

        async def post(self, url, json, headers):
            if sent is not None:
                sent.update(json)
            if raise_exc is not None:
                raise raise_exc
            return resp

    return _FakeClient


async def _collect(agen) -> list[dict]:
    return [ev async for ev in agen]


def _configure(monkeypatch, *, url="https://engine.example", token="SECRET-TOKEN-XYZ"):
    monkeypatch.setattr(external_engine, "RUNNER_URL", url)
    monkeypatch.setattr(external_engine, "RUNNER_TOKEN", token)


@pytest.mark.asyncio
async def test_unconfigured_yields_clean_error(monkeypatch) -> None:
    _configure(monkeypatch, url="", token="")
    evs = await _collect(
        external_engine.stream_external_turn(persona_id="vultur", user_text="hi", session_uuid="s", user_id="u")
    )
    assert evs == [{"type": "error", "message": "external engine not configured (OG118_EXTERNAL_RUNNER_URL/TOKEN unset)"}]


@pytest.mark.asyncio
async def test_happy_path_yields_text(monkeypatch) -> None:
    _configure(monkeypatch)
    monkeypatch.setattr(
        external_engine.httpx, "AsyncClient", _client_factory(resp=_FakeResp(200, {"text": "  Soy Vultur.  "}))
    )
    evs = await _collect(
        external_engine.stream_external_turn(persona_id="vultur", user_text="hi", session_uuid="s", user_id="u")
    )
    assert evs == [{"type": "text", "text": "Soy Vultur."}]


@pytest.mark.asyncio
async def test_transport_error_is_secret_free(monkeypatch) -> None:
    _configure(monkeypatch, token="SECRET-TOKEN-XYZ")
    monkeypatch.setattr(
        external_engine.httpx, "AsyncClient", _client_factory(raise_exc=httpx.ConnectError("boom"))
    )
    evs = await _collect(
        external_engine.stream_external_turn(persona_id="vultur", user_text="hi", session_uuid="s", user_id="u")
    )
    assert len(evs) == 1 and evs[0]["type"] == "error"
    assert "unreachable" in evs[0]["message"]
    assert "SECRET-TOKEN-XYZ" not in evs[0]["message"]


@pytest.mark.asyncio
async def test_non_200_reports_status_not_token(monkeypatch) -> None:
    _configure(monkeypatch, token="SECRET-TOKEN-XYZ")
    monkeypatch.setattr(
        external_engine.httpx, "AsyncClient", _client_factory(resp=_FakeResp(503, {}))
    )
    evs = await _collect(
        external_engine.stream_external_turn(persona_id="vultur", user_text="hi", session_uuid="s", user_id="u")
    )
    assert evs[0]["type"] == "error" and "503" in evs[0]["message"]
    assert "SECRET-TOKEN-XYZ" not in evs[0]["message"]


@pytest.mark.asyncio
async def test_empty_answer_yields_error(monkeypatch) -> None:
    _configure(monkeypatch)
    monkeypatch.setattr(
        external_engine.httpx, "AsyncClient", _client_factory(resp=_FakeResp(200, {"text": "   "}))
    )
    evs = await _collect(
        external_engine.stream_external_turn(persona_id="vultur", user_text="hi", session_uuid="s", user_id="u")
    )
    assert evs == [{"type": "error", "message": "external engine returned an empty answer"}]


@pytest.mark.asyncio
async def test_channel_id_is_the_conversation_id(monkeypatch) -> None:
    """OG118-CONTINUITY: the engine keys its long-lived session by channel_id
    (session_uuid is ignored by persona_runner). A hardcoded channel would pool
    EVERY user's conversations into one Claude session — the conversation id
    must be the channel."""
    _configure(monkeypatch)
    sent: dict = {}
    monkeypatch.setattr(
        external_engine.httpx,
        "AsyncClient",
        _client_factory(resp=_FakeResp(200, {"text": "ok"}), sent=sent),
    )
    await _collect(
        external_engine.stream_external_turn(persona_id="vultur", user_text="hi", session_uuid="conv-abc", user_id="u")
    )
    assert sent["channel_id"] == "conv-abc"
    assert sent["session_uuid"] == "conv-abc"


@pytest.mark.asyncio
async def test_no_session_falls_back_to_channel_zero(monkeypatch) -> None:
    _configure(monkeypatch)
    sent: dict = {}
    monkeypatch.setattr(
        external_engine.httpx,
        "AsyncClient",
        _client_factory(resp=_FakeResp(200, {"text": "ok"}), sent=sent),
    )
    await _collect(
        external_engine.stream_external_turn(persona_id="vultur", user_text="hi", session_uuid=None, user_id="u")
    )
    assert sent["channel_id"] == "0"
    assert "session_uuid" not in sent


@pytest.mark.asyncio
async def test_history_is_forwarded_capped(monkeypatch) -> None:
    """The replayed thread rides the payload (capped) so a fresh engine session —
    reaped slot, replica restart, element switched mid-conversation — can be
    seeded with the turns it never saw."""
    _configure(monkeypatch)
    sent: dict = {}
    monkeypatch.setattr(
        external_engine.httpx,
        "AsyncClient",
        _client_factory(resp=_FakeResp(200, {"text": "ok"}), sent=sent),
    )
    history = [{"role": "user", "content": f"m{i}"} for i in range(30)]
    history.append({"role": "system", "content": "dropped: role not allowlisted"})
    await _collect(
        external_engine.stream_external_turn(
            persona_id="vultur", user_text="hi", session_uuid="s", user_id="u", history=history
        )
    )
    assert len(sent["history"]) == external_engine.HISTORY_MAX_MESSAGES - 1
    assert sent["history"][-1] == {"role": "user", "content": "m29"}
    assert all(m["role"] in {"user", "assistant"} for m in sent["history"])


def test_cap_history_char_budget_keeps_newest() -> None:
    big = "x" * external_engine.HISTORY_MAX_CHARS
    history = [
        {"role": "user", "content": big},
        {"role": "assistant", "content": "newest"},
    ]
    assert external_engine.cap_history(history) == [{"role": "assistant", "content": "newest"}]


def test_cap_history_empty_and_none() -> None:
    assert external_engine.cap_history(None) == []
    assert external_engine.cap_history([]) == []


@pytest.mark.asyncio
async def test_non_json_body_yields_error(monkeypatch) -> None:
    _configure(monkeypatch)
    monkeypatch.setattr(
        external_engine.httpx, "AsyncClient", _client_factory(resp=_FakeResp(200, ValueError("not json")))
    )
    evs = await _collect(
        external_engine.stream_external_turn(persona_id="vultur", user_text="hi", session_uuid="s", user_id="u")
    )
    assert evs == [{"type": "error", "message": "external engine returned a non-JSON body"}]
