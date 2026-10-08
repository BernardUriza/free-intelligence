"""The 2026-08-03 lesson: a dead credential must reach /health as a real verdict.

The SDK-prose sniffer this file used to pin died with the local SDK host — on
the AIRE route a dead droplet credential arrives as the door's structured
`credentials_exhausted` code, and the wiring test lives with the route
(tests/agent/test_aire_route.py). What stays pinned here is the state the
/health endpoint reads.
"""

from __future__ import annotations

from persona_runner.engine import auth_failure

REVOKED = "AIRE turn terminal: credentials pool exhausted"


def test_failure_state_round_trip():
    auth_failure.clear_failure()
    assert auth_failure.last_failure() is None
    auth_failure.mark_failure(REVOKED)
    recorded = auth_failure.last_failure()
    assert recorded is not None and "exhausted" in recorded["detail"]
    auth_failure.clear_failure()
    assert auth_failure.last_failure() is None


def test_mark_truncates_detail():
    auth_failure.mark_failure("x" * 999)
    recorded = auth_failure.last_failure()
    assert recorded is not None and len(recorded["detail"]) == 200
    auth_failure.clear_failure()
