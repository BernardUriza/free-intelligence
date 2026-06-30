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


def _client_factory(*, resp: _FakeResp | None = None, raise_exc: Exception | None = None):
    class _FakeClient:
        def __init__(self, *a, **k) -> None: ...

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a) -> bool:
            return False

        async def post(self, url, json, headers):
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
async def test_non_json_body_yields_error(monkeypatch) -> None:
    _configure(monkeypatch)
    monkeypatch.setattr(
        external_engine.httpx, "AsyncClient", _client_factory(resp=_FakeResp(200, ValueError("not json")))
    )
    evs = await _collect(
        external_engine.stream_external_turn(persona_id="vultur", user_text="hi", session_uuid="s", user_id="u")
    )
    assert evs == [{"type": "error", "message": "external engine returned a non-JSON body"}]
