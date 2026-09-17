"""The `task_tracker` in-process MCP server — the agent's plan, out loud.

The registry's third tenant (backlog #45). The model declares a checklist and
reports each step as it goes; a consumer watching the `tool_call` stream turns
those calls into a live plan the user can see, which is the difference between a
spinner and knowing what the agent is doing. The state machine is `engine/tracker/`.

SESSION-SCOPED by construction, like `memory`: `build_tracker_server` closes over
one `TaskTracker`, so a plan can never be reached from another session. Upstream
takes a `session_id` argument on every tool; here that argument does not exist,
because a scope the wire can name is a scope the wire can cross.

The tool NAMES are upstream's, exactly. A consumer's event translator keys on
them, and renaming them here would make the plan invisible on this door alone.
They are declared as a TABLE rather than ten decorated bodies: the ten differ
only in which tracker call they make, so a table is where a reader sees the whole
surface at once instead of scrolling past nine near-copies of the tenth.
"""

from __future__ import annotations

import json
from typing import Any, Callable

from ..agent_sdk import mcp_server as create_sdk_mcp_server
from ..agent_sdk import tool

from .tracker import PlanNotFound, StepStatus, TaskTracker

SERVER_NAME = "task_tracker"
_PLAN = {"plan_id": str}
_STEP = {"plan_id": str, "step_index": int}


def _reply(payload: Any, failed: bool = False) -> dict[str, Any]:
    body = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    out: dict[str, Any] = {"content": [{"type": "text", "text": body}]}
    if failed:
        out["is_error"] = True
    return out


def _int(raw: Any, absent: int | None = None) -> int:
    """An index, or a refusal the model reads. NOT a coercion to zero: a garbage
    index quietly becoming step 0 would start the wrong step and report success,
    which is worse than the error the model can actually correct. `absent` is the
    value for a field the model may legitimately omit."""
    if raw is None and absent is not None:
        return absent
    try:
        return int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"expected a step index, got {raw!r}") from exc


def _text(args: dict[str, Any], key: str) -> str:
    return str(args.get(key) or "")


def _settle(status: StepStatus, key: str) -> Callable[[TaskTracker, dict[str, Any]], Any]:
    return lambda t, a: t.end(_text(a, "plan_id"), _int(a.get("step_index")), status,
                              **{"summary" if status is StepStatus.DONE else "error": _text(a, key)})


# (name, description, schema, op) — `op` takes the session's tracker and the
# raw args and returns whatever the model should read back.
TOOLS: tuple[tuple[str, str, dict, Callable[[TaskTracker, dict[str, Any]], Any]], ...] = (
    ("declare_plan",
     "Declare the checklist you are about to work through, BEFORE starting. `steps` is a "
     "list of labels, or of objects with `label` and optional `active_form`, `depends_on` "
     "(indexes of earlier steps) and `metadata`. Returns the plan with its `plan_id`, "
     "which every later call needs.",
     {"steps": list},
     lambda t, a: t.declare(a.get("steps") or [])),
    ("start_step", "Mark a step as running, right before you begin it.", _STEP,
     lambda t, a: t.start(_text(a, "plan_id"), _int(a.get("step_index")))),
    ("complete_step", "Mark a step done, with a one-line summary of what came of it.",
     {**_STEP, "summary": str}, _settle(StepStatus.DONE, "summary")),
    ("fail_step",
     "Mark a step failed, with the error. The plan fails once every step settles.",
     {**_STEP, "error": str}, _settle(StepStatus.FAILED, "error")),
    ("cancel_step", "Mark a step cancelled — it was dropped, not attempted and failed.",
     {**_STEP, "reason": str}, _settle(StepStatus.CANCELLED, "reason")),
    ("note_step", "Append progress to a step that is taking a while, without settling it.",
     {**_STEP, "note": str},
     lambda t, a: t.note(_text(a, "plan_id"), _int(a.get("step_index")), _text(a, "note"))),
    ("insert_step",
     "Insert a step you did not foresee, right after `after_index` (-1 puts it first).",
     {**_PLAN, "after_index": int, "step": str},
     lambda t, a: t.insert(_text(a, "plan_id"), _int(a.get("after_index"), -1), a.get("step"))),
    ("replan",
     "Replace every step from `from_index` onwards. What came before must already be settled.",
     {**_PLAN, "from_index": int, "new_steps": list},
     lambda t, a: t.replan(_text(a, "plan_id"), _int(a.get("from_index")),
                           a.get("new_steps") or [])),
    ("cancel_plan", "Abandon the whole plan; every unsettled step is cancelled.",
     {**_PLAN, "reason": str},
     lambda t, a: t.cancel(_text(a, "plan_id"), _text(a, "reason"))),
    ("finalize_plan",
     "Close the plan when you are done. Anything never started is skipped, and the "
     "outcome follows from the steps.",
     _PLAN, lambda t, a: t.finalize(_text(a, "plan_id"))),
)


def _bind(plans: TaskTracker, spec: tuple) -> Any:
    """One table row into one SDK tool, with the tracker's refusals handed BACK
    TO THE MODEL as text. Every error the state machine raises is a rule the
    model broke — a settled step, an open dependency, a bad index — and the model
    is the only party that can fix it, mid-turn, in a paid turn an exception
    would have killed."""
    name, description, schema, op = spec

    async def run(args: dict[str, Any]) -> dict[str, Any]:
        try:
            return _reply(op(plans, args).as_dict())
        except PlanNotFound as exc:
            return _reply(f"no plan {exc.args[0]!r} in this session; declare one first", True)
        except (ValueError, IndexError, RuntimeError) as exc:
            return _reply(f"{type(exc).__name__}: {exc}", True)

    run.__name__ = name
    return tool(name, description, schema)(run)


def build_tools(plans: TaskTracker) -> list[Any]:
    """Every row of the table bound to one tracker. Named so the server and its
    tests reach the tools the same way — a test that rebuilt them itself could
    pass while the server shipped a different set."""
    return [_bind(plans, spec) for spec in TOOLS]


def build_tracker_server(_project_key: str, _cwd: str = "") -> Any:
    """The session-scoped `task_tracker` server. Neither the project key nor the
    casita disk is touched: a plan is in-memory state that dies with its client."""
    return create_sdk_mcp_server(name=SERVER_NAME, version="1.0.0",
                                 tools=build_tools(TaskTracker()))
