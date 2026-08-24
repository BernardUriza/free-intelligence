"""The tracker's refusals, as types.

Each one is a rule the state machine enforces, and the tool adapter turns every
one into an `is_error` text result the MODEL reads and can correct — never a
crash inside a paid turn. They keep upstream's base classes so the meaning is
the same one fi-core's consumers already know.

`SessionMismatch` has no counterpart here on purpose: AIRE's registry builds one
tracker per session (`build_tracker_server` closes over it), so there is no
second session's plan to confuse this one with. Upstream needs the check because
its tracker is a process-wide singleton keyed by a session id the MODEL passes;
here the scope is structural, and a check the wire cannot influence is not a
check at all.
"""

from __future__ import annotations


class PlanNotFound(KeyError):
    """No plan by that id — expired with its client, or never declared."""


class StepIndexInvalid(IndexError):
    """The step index is outside the plan."""


class StepAlreadyTerminal(RuntimeError):
    """A settled step is immutable: a late complete/fail/note cannot regress it."""


class PlanAlreadyTerminal(RuntimeError):
    """The plan has settled; it can no longer be reshaped."""


class DependencyUnmet(RuntimeError):
    """A step whose `depends_on` are not all DONE cannot start."""
