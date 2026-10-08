"""The `task_tracker` — the agent declares a plan and walks it, so a consumer
can render a live checklist instead of a spinner.

Vendored from fi-core's `task_tracker` (backlog #45), for decision #1's reason:
fi-core is not on PyPI and the droplet must not depend on a repo another agent
edits. The tool NAMES and the shapes are kept identical to upstream, because a
consumer's event translator keys on them and must not need a fork to read AIRE.

Two adaptations are the whole reason this is not a verbatim copy:

- **No session id, anywhere.** AIRE's registry builds one tracker per session
  (`build_tracker_server` closes over it), so the scope is structural instead of
  an argument the model passes. Upstream needs `session_id`, `list_for_session`
  and `SessionMismatch` because its tracker is a process-wide singleton keyed by
  a value the MODEL supplies — a scope the wire can name is a scope the wire can
  cross, and here it cannot name one at all.
- **No TTL store.** Upstream evicts because it outlives every session. This one
  is owned by a pooled client and dies with it, which is a tighter bound than
  any TTL and needs no clock to enforce.

A plan is a WITHIN-TURN artifact: declared, walked and settled inside one
response. Losing it when its client is evicted costs nothing.

The modules: `models` (the shapes, and what a settled plan IS), `specs` (where
untrusted JSON stops being that), `reshape` (pure shape math), `errors` (the
refusals, as types), `plans` (the rules about who may mutate what, and when).
"""

from .errors import (DependencyUnmet, PlanAlreadyTerminal, PlanNotFound,
                     StepAlreadyTerminal, StepIndexInvalid)
from .models import Plan, PlanStatus, Step, StepStatus
from .plans import TaskTracker

__all__ = ["DependencyUnmet", "Plan", "PlanAlreadyTerminal", "PlanNotFound", "PlanStatus",
           "Step", "StepAlreadyTerminal", "StepIndexInvalid", "StepStatus", "TaskTracker"]
