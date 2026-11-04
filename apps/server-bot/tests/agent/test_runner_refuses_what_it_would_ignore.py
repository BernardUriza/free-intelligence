"""A request the runner cannot honor is refused, never answered with a 200 that lies.

2026-11-04, one probe, three lies: `model` on /v1/turn was dropped and Haiku ran;
`claude-opus-5-5` on /v1/judge came back as HTTP 200 with the CLI's error as `text`;
an unknown `persona_id` answered with Insult's DNA.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI, HTTPException

from persona_runner.api import judge as judge_api
from persona_runner.api import ops as ops_api
from persona_runner.api import turn as turn_api
from persona_runner.core import config
from persona_runner.core.schemas import JudgeRequest, JudgeResponse
from persona_runner.engine import aire_route, persona_files, runtime_personas
from persona_runner.routing import router_runtime

BODY = {"system_prompt": "s", "user_text": "u"}


@pytest.fixture(autouse=True)
def _personas(monkeypatch, tmp_path):
    (tmp_path / "vultur.md").write_text("# Vultur")
    monkeypatch.setattr(config, "PERSONAS_DIR", tmp_path)
    monkeypatch.setattr(config, "RUNNER_AUTH_TOKEN", "t")
    judge_api.reset_judge_semaphore()
    yield
    judge_api.reset_judge_semaphore()


def _client() -> httpx.AsyncClient:
    app = FastAPI()
    app.include_router(judge_api.router)
    app.include_router(turn_api.router)
    app.include_router(ops_api.router)
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://t", headers={"Authorization": "Bearer t"}
    )


@pytest.mark.asyncio
async def test_a_model_this_runner_does_not_serve_is_a_422_that_names_the_ones_it_does(monkeypatch):
    called = AsyncMock()
    monkeypatch.setattr(aire_route, "judge_via_aire", called)
    async with _client() as http:
        resp = await http.post("/v1/judge", json={**BODY, "model": "claude-opus-5-5"})
    assert resp.status_code == 422
    assert router_runtime.CRISIS_MODEL in resp.json()["detail"]
    called.assert_not_awaited()


@pytest.mark.asyncio
async def test_a_served_model_reaches_the_judge(monkeypatch):
    called = AsyncMock(return_value=JudgeResponse(text="ok", model=router_runtime.CRISIS_MODEL, output_tokens=3))
    monkeypatch.setattr(aire_route, "judge_via_aire", called)
    async with _client() as http:
        resp = await http.post("/v1/judge", json={**BODY, "model": router_runtime.CRISIS_MODEL})
    assert resp.status_code == 200
    called.assert_awaited_once()


@pytest.mark.asyncio
async def test_a_judge_without_a_model_is_still_admitted(monkeypatch):
    called = AsyncMock(return_value=JudgeResponse(text="ok", model="m", output_tokens=3))
    monkeypatch.setattr(aire_route, "judge_via_aire", called)
    async with _client() as http:
        assert (await http.post("/v1/judge", json=BODY)).status_code == 200


@pytest.mark.asyncio
async def test_an_unknown_field_on_the_judge_is_a_422():
    async with _client() as http:
        assert (await http.post("/v1/judge", json={**BODY, "effort": "max"})).status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/v1/turn", "/v1/turn/jobs"])
async def test_an_unknown_persona_is_a_422_instead_of_the_default_personas_voice(path, monkeypatch):
    served = AsyncMock()
    monkeypatch.setattr(turn_api, "serve_turn", served)
    body = {"channel_id": "c", "user_id": "u", "user_text": "x", "persona_id": "nope_zzz"}
    async with _client() as http:
        resp = await http.post(path, json=body)
    assert resp.status_code == 422
    assert "nope_zzz" in resp.json()["detail"]
    served.assert_not_awaited()


def test_personas_that_exist_pass_the_door(monkeypatch, tmp_path):
    persona_files.require_known_persona(None)
    persona_files.require_known_persona("vultur")
    monkeypatch.setattr(runtime_personas, "path_for", lambda pid: tmp_path / "x.md" if pid == "radon" else None)
    persona_files.require_known_persona("radon")


@pytest.mark.parametrize("evil", ["../../etc/passwd", "UPPER", "nope_zzz"])
def test_the_door_refuses_what_the_fallback_would_have_swallowed(evil):
    with pytest.raises(HTTPException) as exc:
        persona_files.require_known_persona(evil)
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_the_clis_own_error_is_a_502_not_a_reply(monkeypatch):
    error = "API Error: 400 Claude Code 2.1.215 does not support this model"
    backend = AsyncMock()
    backend.run_turn.return_value = SimpleNamespace(text=error, model="<synthetic>", usage={})
    monkeypatch.setattr(aire_route, "judge_backend_for", lambda _c: backend)
    with pytest.raises(HTTPException) as exc:
        await aire_route.judge_via_aire(JudgeRequest(**BODY))
    assert exc.value.status_code == 502
    assert "does not support" in exc.value.detail


@pytest.mark.asyncio
async def test_health_publishes_the_ids_the_judge_admits():
    async with _client() as http:
        models = (await http.get("/health")).json()["models"]
    assert models["crisis"] == router_runtime.CRISIS_MODEL
    assert models["depth"] == router_runtime.DEPTH_MODEL
    assert models["judge_default"] == config.JUDGE_DEFAULT_MODEL
