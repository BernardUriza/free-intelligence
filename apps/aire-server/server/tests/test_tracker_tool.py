"""The door's half of the tracker (backlog #45): what the model can ask for,
what it gets back, and what a broken rule looks like from inside a paid turn.

The names matter as much as the behavior: a consumer's event translator keys on
`declare_plan` / `start_step` / …, so a rename here makes the live plan invisible
on this door alone while every test about the state machine still passes.
"""

import json

import pytest

from aire.engine.tools import REGISTRY, UnknownTool, clean_tools, resolve
from aire.engine.tracker import TaskTracker
from aire.engine.tracker_tool import (TOOLS, SERVER_NAME, build_tools,
                                      build_tracker_server)

UPSTREAM_NAMES = {"declare_plan", "start_step", "complete_step", "fail_step", "cancel_step",
                  "note_step", "insert_step", "replan", "cancel_plan", "finalize_plan"}


def _handlers() -> dict:
    """One session's tools, reached exactly as the server reaches them."""
    return {t.name: t.handler for t in build_tools(TaskTracker())}


async def _call(handlers, name, **args):
    return await handlers[name](args)


def _body(result) -> str:
    return result["content"][0]["text"]


def _json(result):
    return json.loads(_body(result))


def test_the_tool_names_are_upstreams_exactly():
    assert {name for name, _, _, _ in TOOLS} == UPSTREAM_NAMES


def test_no_tool_takes_a_session_id():
    """The scope is structural. A session id on the wire is a scope the model
    could name, and therefore one it could cross."""
    assert all("session_id" not in schema for _, _, schema, _ in TOOLS)


def test_the_registry_ships_it_and_the_wire_can_name_it():
    assert REGISTRY["task_tracker"] is build_tracker_server
    assert clean_tools(["task_tracker"]) == ["task_tracker"]
    servers, allowed = resolve(["task_tracker"], "pk", "/tmp")
    assert servers["task_tracker"]["name"] == SERVER_NAME
    assert allowed == ["mcp__task_tracker"]


def test_the_wire_still_cannot_define_a_server():
    with pytest.raises(UnknownTool):
        clean_tools([{"command": "rm", "args": ["-rf", "/"]}])


@pytest.mark.asyncio
async def test_a_plan_is_declared_walked_and_settled():
    h = _handlers()
    plan = _json(await _call(h, "declare_plan", steps=["buscar", "responder"]))
    assert plan["status"] == "declared" and len(plan["steps"]) == 2
    pid = plan["plan_id"]
    await _call(h, "start_step", plan_id=pid, step_index=0)
    done = _json(await _call(h, "complete_step", plan_id=pid, step_index=0, summary="listo"))
    assert done["status"] == "done" and done["summary"] == "listo"
    final = _json(await _call(h, "finalize_plan", plan_id=pid))
    assert final["status"] == "completed"


@pytest.mark.asyncio
async def test_a_broken_rule_comes_back_as_text_the_model_can_act_on():
    """Not an exception: this runs inside a turn the caller already paid for, and
    every one of these is something the model itself can correct."""
    h = _handlers()
    pid = _json(await _call(h, "declare_plan", steps=["uno"]))["plan_id"]
    await _call(h, "complete_step", plan_id=pid, step_index=0, summary="")
    late = await _call(h, "complete_step", plan_id=pid, step_index=0, summary="otra vez")
    assert late["is_error"] is True and "already" in _body(late)


@pytest.mark.asyncio
async def test_an_unknown_plan_says_what_to_do_about_it():
    h = _handlers()
    out = await _call(h, "start_step", plan_id="ghost", step_index=0)
    assert out["is_error"] is True and "declare one first" in _body(out)


@pytest.mark.asyncio
async def test_an_empty_checklist_is_refused_at_the_tool():
    h = _handlers()
    out = await _call(h, "declare_plan", steps=[])
    assert out["is_error"] is True


@pytest.mark.asyncio
async def test_a_garbage_index_is_refused_not_coerced():
    """The model sometimes sends a word where an index belongs. Coercing it to 0
    would start the WRONG step and report success — a silent wrong answer instead
    of one sentence the model can act on."""
    h = _handlers()
    pid = _json(await _call(h, "declare_plan", steps=["uno", "dos"]))["plan_id"]
    out = await _call(h, "start_step", plan_id=pid, step_index="segundo")
    assert out["is_error"] is True and "segundo" in _body(out)
    assert _json(await _call(h, "start_step", plan_id=pid, step_index=1))["status"] == "running"


@pytest.mark.asyncio
async def test_an_omitted_after_index_still_prepends():
    """-1 is a real default for a field the model may legitimately omit; the
    refusal above is for a value it got WRONG, which is a different thing."""
    h = _handlers()
    pid = _json(await _call(h, "declare_plan", steps=["uno"]))["plan_id"]
    plan = _json(await _call(h, "insert_step", plan_id=pid, step="cero"))
    assert [s["label"] for s in plan["steps"]] == ["cero", "uno"]


@pytest.mark.asyncio
async def test_two_sessions_cannot_see_each_others_plans():
    a, b = _handlers(), _handlers()
    pid = _json(await _call(a, "declare_plan", steps=["uno"]))["plan_id"]
    out = await _call(b, "start_step", plan_id=pid, step_index=0)
    assert out["is_error"] is True and "no plan" in _body(out)
