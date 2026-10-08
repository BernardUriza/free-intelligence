"""The vendored plan state machine (backlog #45).

These pin the RULES, not the shapes: what a settled step refuses, what a plan is
once its steps stop moving, and the two adaptations that make this not a verbatim
copy of fi-core — no session id anywhere, and no TTL.
"""

import pytest

from aire.engine.tracker import (DependencyUnmet, PlanAlreadyTerminal,
                                 PlanNotFound, PlanStatus, StepAlreadyTerminal,
                                 StepIndexInvalid, StepStatus, TaskTracker)


@pytest.fixture()
def t() -> TaskTracker:
    return TaskTracker()


def test_a_checklist_with_no_rows_is_refused(t):
    """Zero steps is a UI bug, never a useful state."""
    with pytest.raises(ValueError):
        t.declare([])


def test_a_plan_walks_to_completed(t):
    plan = t.declare(["buscar", "responder"])
    t.start(plan.plan_id, 0)
    t.end(plan.plan_id, 0, StepStatus.DONE, summary="encontrado")
    assert t.get(plan.plan_id).status is PlanStatus.RUNNING, "one step left"
    t.start(plan.plan_id, 1)
    t.end(plan.plan_id, 1, StepStatus.DONE)
    assert t.get(plan.plan_id).status is PlanStatus.COMPLETED


def test_a_settled_step_is_immutable(t):
    plan = t.declare(["uno"])
    t.end(plan.plan_id, 0, StepStatus.DONE)
    for call in (lambda: t.end(plan.plan_id, 0, StepStatus.FAILED),
                 lambda: t.start(plan.plan_id, 0),
                 lambda: t.note(plan.plan_id, 0, "tarde")):
        with pytest.raises(StepAlreadyTerminal):
            call()


def test_a_step_waits_for_what_it_depends_on(t):
    plan = t.declare(["fetch", {"label": "parse", "depends_on": [0]}])
    with pytest.raises(DependencyUnmet):
        t.start(plan.plan_id, 1)
    t.end(plan.plan_id, 0, StepStatus.DONE)
    assert t.start(plan.plan_id, 1).status is StepStatus.RUNNING


def test_a_dependency_may_only_point_backwards(t):
    """One rule forbids cycles structurally, with no DAG validator to get wrong."""
    with pytest.raises(ValueError):
        t.declare([{"label": "a", "depends_on": [1]}, "b"])


def test_starting_twice_does_not_restart_the_clock(t):
    plan = t.declare(["uno"])
    first = t.start(plan.plan_id, 0)
    assert t.start(plan.plan_id, 0) == first


def test_a_step_never_started_gets_no_invented_duration(t):
    """Some models skip start_step. A fabricated duration is worse than none."""
    plan = t.declare(["uno"])
    assert t.end(plan.plan_id, 0, StepStatus.DONE).duration_ms is None


def test_a_started_step_is_timed(t):
    plan = t.declare(["uno"])
    t.start(plan.plan_id, 0)
    assert t.end(plan.plan_id, 0, StepStatus.DONE).duration_ms is not None


def test_failure_outranks_cancellation(t):
    plan = t.declare(["a", "b"])
    t.end(plan.plan_id, 0, StepStatus.CANCELLED)
    t.end(plan.plan_id, 1, StepStatus.FAILED)
    assert t.get(plan.plan_id).status is PlanStatus.FAILED


def test_one_done_step_means_the_plan_completed_not_cancelled(t):
    plan = t.declare(["a", "b"])
    t.end(plan.plan_id, 0, StepStatus.DONE)
    t.end(plan.plan_id, 1, StepStatus.CANCELLED)
    assert t.get(plan.plan_id).status is PlanStatus.COMPLETED


def test_notes_append_and_never_overwrite(t):
    plan = t.declare(["uno"])
    t.note(plan.plan_id, 0, "página 1")
    step = t.note(plan.plan_id, 0, "página 2")
    assert step.notes == ("página 1", "página 2")
    assert t.note(plan.plan_id, 0, "").notes == ("página 1", "página 2"), "empty note is a no-op"


def test_an_insert_carries_the_dependencies_that_crossed_it(t):
    """Without renumbering, an insert silently repoints a dependency at whatever
    step inherited the index."""
    plan = t.declare(["fetch", {"label": "parse", "depends_on": [0]}])
    after = t.insert(plan.plan_id, 0, "validate")
    assert [s.label for s in after.steps] == ["fetch", "validate", "parse"]
    assert after.steps[2].depends_on == (0,), "parse still waits on fetch, not on validate"


def test_insert_at_minus_one_prepends(t):
    plan = t.declare(["uno"])
    assert [s.label for s in t.insert(plan.plan_id, -1, "cero").steps] == ["cero", "uno"]


def test_replan_refuses_to_step_over_something_still_running(t):
    plan = t.declare(["a", "b"])
    t.start(plan.plan_id, 0)
    with pytest.raises(StepAlreadyTerminal):
        t.replan(plan.plan_id, 1, ["c"])


def test_replan_drops_the_timings_of_the_steps_it_removed(t):
    """A clock kept for a removed step would later stamp its duration onto
    whatever step inherited the index."""
    plan = t.declare(["a", "b"])
    t.end(plan.plan_id, 0, StepStatus.DONE)
    t.start(plan.plan_id, 1)
    t.replan(plan.plan_id, 1, ["nuevo"])
    assert t.end(plan.plan_id, 1, StepStatus.DONE).duration_ms is None


def test_finalize_skips_what_never_ran(t):
    plan = t.declare(["a", "b"])
    t.end(plan.plan_id, 0, StepStatus.DONE)
    final = t.finalize(plan.plan_id)
    assert final.steps[1].status is StepStatus.SKIPPED
    assert final.status is PlanStatus.COMPLETED
    assert t.finalize(plan.plan_id) == final, "idempotent"


def test_a_settled_plan_cannot_be_reshaped(t):
    plan = t.declare(["a"])
    t.finalize(plan.plan_id)
    for call in (lambda: t.insert(plan.plan_id, 0, "b"),
                 lambda: t.replan(plan.plan_id, 0, ["b"])):
        with pytest.raises(PlanAlreadyTerminal):
            call()


def test_a_completed_plan_cannot_be_cancelled_but_a_running_one_can(t):
    done = t.declare(["a"])
    t.end(done.plan_id, 0, StepStatus.DONE)
    with pytest.raises(PlanAlreadyTerminal):
        t.cancel(done.plan_id)
    live = t.declare(["a"])
    cancelled = t.cancel(live.plan_id, "cambié de idea")
    assert cancelled.status is PlanStatus.CANCELLED
    assert cancelled.steps[0].error == "cambié de idea"
    assert t.cancel(live.plan_id) == cancelled, "idempotent"


def test_an_index_outside_the_plan_is_refused(t):
    plan = t.declare(["uno"])
    with pytest.raises(StepIndexInvalid):
        t.start(plan.plan_id, 5)


def test_an_unknown_plan_is_refused(t):
    with pytest.raises(PlanNotFound):
        t.get("nope")


def test_two_trackers_share_nothing(t):
    """The registry builds one per session, which is why no tool takes a session
    id: the scope is structural, and a scope the wire can name it can cross."""
    plan = t.declare(["uno"])
    with pytest.raises(PlanNotFound):
        TaskTracker().get(plan.plan_id)
