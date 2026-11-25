"""The food tools: stated state and basis, no identity, only for the persona that declares them."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from persona_core.nutrients import store
from persona_runner.api import mcp_http
from persona_runner.core.schemas import RESERVED_TOOL_NAMES
from persona_runner.engine import aire_route
from persona_runner.mcp_tools import TOOL_PACKS
from persona_runner.mcp_tools.nutrients import food_lookup, nutrient_compare, nutrient_rank
from persona_runner.mcp_tools.tooldef import build_input_schema
from shared.personas.registry import PERSONAS


def _id(name: str) -> int:
    return next(f.fdc_id for f in store.foods().values() if f.name == name)


def _text(out: dict) -> str:
    return out["content"][0]["text"]


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("RUNNER_MCP_TOKEN", "tok-1")
    app = FastAPI()
    app.include_router(mcp_http.router)
    return TestClient(app)


def _rpc(client, method, params=None, path="/mcp/packs/food_data", bearer="tok-1"):
    return client.post(
        path,
        headers={"Authorization": f"Bearer {bearer}"},
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}},
    )


async def test_lookup_lists_candidates_with_their_state():
    out = _text(await food_lookup.handler({"query": "guayaba"}))
    assert "fdc_id" in out and "estado: crudo" in out and "Guavas, common, raw" in out


async def test_lookup_of_nothing_says_so_without_a_number():
    assert "no tienes el dato" in _text(await food_lookup.handler({"query": "unicornio"}))
    assert (await food_lookup.handler({"query": " "})).get("is_error")


async def test_compare_states_basis_source_and_warns_when_states_differ():
    same = _text(await nutrient_compare.handler({"fdc_ids": [_id("Lentils, raw")], "nutrients": ["hierro"]}))
    assert "por 100g" in same and "USDA" in same and "OJO" not in same
    ids = [_id("Lentils, raw"), _id("Lentils, mature seeds, cooked, boiled, without salt")]
    mixed = _text(await nutrient_compare.handler({"fdc_ids": ids, "nutrients": ["hierro"]}))
    assert "OJO" in mixed


async def test_compare_does_the_division_so_the_model_never_does():
    ids = [_id("Lentils, mature seeds, cooked, boiled, without salt")]
    ids.append(_id("Beans, black, mature seeds, cooked, boiled, without salt"))
    both = _text(await nutrient_compare.handler({"fdc_ids": ids, "nutrients": ["hierro"]}))
    assert "3.33 | 2.1 -> el mayor es 1.59 veces el menor" in both
    alone = _text(await nutrient_compare.handler({"fdc_ids": ids[:1], "nutrients": ["hierro"]}))
    assert "veces" not in alone
    zero = _text(await nutrient_compare.handler({"fdc_ids": ids, "nutrients": ["b12"]}))
    assert "veces" not in zero


async def test_compare_names_what_was_not_measured():
    out = _text(await nutrient_compare.handler({"fdc_ids": [_id("Lentils, raw")], "nutrients": ["hierro", "yodo"]}))
    assert "Sin dato en todos: yodo" in out


@pytest.mark.parametrize(
    "args",
    [
        {"fdc_ids": []},
        {"fdc_ids": [1]},
        {"fdc_ids": ["x"]},
        {"fdc_ids": list(range(1, 9))},
        {"fdc_ids": [173044], "nutrients": ["magia"]},
        {"fdc_ids": [173044], "basis": "porcion"},
    ],
)
async def test_compare_refuses_what_it_cannot_answer(args):
    assert (await nutrient_compare.handler(args)).get("is_error")


async def test_rank_is_capped_and_refuses_an_unknown_state():
    cap = store.rules()["search"]["max_rank"]
    out = _text(await nutrient_rank.handler({"nutrient": "hierro", "limit": 500}))
    assert out.count("fdc_id") == cap
    assert (await nutrient_rank.handler({"nutrient": "hierro", "state": "gaseoso"})).get("is_error")
    assert (await nutrient_rank.handler({"nutrient": "hierro", "limit": "muchos"})).get("is_error")


def test_only_frugivoro_mounts_the_food_pack(monkeypatch):
    monkeypatch.setenv("RUNNER_MCP_BASE", "https://r.example.com/")
    monkeypatch.setenv("RUNNER_MCP_TOKEN", "tok-9")
    (spec,) = aire_route.pack_tool_specs("frugivoro")
    assert (spec.name, spec.url) == ("food_data", "https://r.example.com/mcp/packs/food_data")
    assert "tok-9" not in repr(spec)
    assert all(aire_route.pack_tool_specs(p) == [] for p in PERSONAS if p != "frugivoro")
    assert aire_route.pack_tool_specs("nadie") == []


def test_packs_are_declared_reserved_and_leave_room_for_the_caller():
    for persona in PERSONAS.values():
        assert set(persona.tool_packs) <= set(TOOL_PACKS)
        # AIRE refuses a turn with more than four remote servers: memory + packs + two from the caller.
        assert 1 + len(persona.tool_packs) + 2 <= 4
    assert set(TOOL_PACKS) <= RESERVED_TOOL_NAMES


def test_insult_is_not_told_about_a_pack_it_does_not_mount():
    dna = (Path(__file__).parents[2] / "shared" / "personas" / "insult.md").read_text(encoding="utf-8")
    assert not [t.name for tools in TOOL_PACKS.values() for t in tools if t.name in dna]


def test_no_pack_tool_takes_an_identity():
    identity = {"user_id", "channel_id", "principal_id", "author_id", "agent_id"}
    for tools in TOOL_PACKS.values():
        for tool in tools:
            assert not identity & set(build_input_schema(tool)["properties"])


def test_the_pack_door_serves_only_its_own_tools(client):
    assert _rpc(client, "initialize").json()["result"]["serverInfo"]["name"] == "food_data"
    listed = {t["name"] for t in _rpc(client, "tools/list").json()["result"]["tools"]}
    assert listed == {"food_lookup", "nutrient_compare", "nutrient_rank"}
    ok = _rpc(client, "tools/call", {"name": "food_lookup", "arguments": {"query": "guayaba"}}).json()
    assert ok["result"]["isError"] is False
    memory = _rpc(client, "tools/call", {"name": "get_user_facts", "arguments": {}}).json()
    assert memory["result"]["isError"] is True


def test_the_pack_door_is_closed_without_the_bearer_and_for_an_unknown_pack(client):
    assert _rpc(client, "ping", bearer="wrong").status_code == 404
    assert _rpc(client, "ping", path="/mcp/packs/otro").status_code == 404
