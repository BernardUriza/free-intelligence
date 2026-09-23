#!/usr/bin/env python3
"""The CD's "did the deploy actually SERVE?" gate for a min=1 Container App.

    python3 scripts/cd_wait_revision.py <app> <resource-group> <expected-image> [timeout_s]

Waits until the revision that carries ``expected-image`` is ``Healthy`` +
``RunningAtMaxScale`` (or ``Running``) with 100% traffic, and no OLDER revision is
still running beside it. Exit 0 then. Exit 1 the moment that revision reports
``Failed`` / ``Degraded`` / ``Unhealthy`` (crash loop — no point waiting), when no
revision carries the image after a short grace (the deploy step failed silently),
or when the deadline passes without the new revision serving.

Why this exists (2026-09-17 → 09-18): fourteen consecutive `persona-gateway`
revisions died at boot (`TypeError: Config.__init__() ... 'install_signal_handlers'`),
ACA kept the previous replica alive holding the Discord websocket, and the CD said
**success** fourteen times — its check grepped `persona_gateway_starting` in the
last 30 log lines, a line the gateway prints BEFORE it can crash. A check that
cannot fail proves nothing (`.claude/rules/router-observability.md`); the only
detector was a stale version tag in #general. This gate reads the revision's own
state, which is what a crash loop actually changes.

Scope: apps with min=1 (persona-gateway, khimeras-host). `persona-runner` runs
min=0 and is verified by the CD's real `/health` + `/v1/turn` probes instead —
a `ScaledToZero` revision is normal there and would be a false red here.
"""

from __future__ import annotations

import json
import subprocess  # nosec B404 — the CD calls `az` on the GitHub runner; no untrusted input reaches argv
import sys
import time
from collections.abc import Callable

DEFAULT_TIMEOUT_S = 420
DEFAULT_POLL_S = 15
# How long a deploy step may take to materialize a revision carrying the new
# image before "no revision carries it" means the `az containerapp update`
# silently failed (its step is continue-on-error for the not-yet-provisioned era).
NO_CARRIER_GRACE_S = 90

SERVING_STATES = {"RunningAtMaxScale", "Running"}
FATAL_RUNNING_STATES = {"Failed", "Degraded"}
# An OLD revision in one of these is still holding replicas (and, for a Discord
# bot, the websocket): the swap is not done. Deprovisioning / ScaledToZero /
# Failed old revisions are on their way out and do not block.
OLD_STILL_RUNNING_STATES = {"Running", "RunningAtMaxScale", "Activating", "Processing"}


def az_list_revisions(app: str, rg: str) -> list[dict]:
    out = subprocess.run(  # nosec B603 B607 — fixed argv, values come from the workflow's own env
        ["az", "containerapp", "revision", "list", "-n", app, "-g", rg, "-o", "json"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return json.loads(out)


def az_dump_revision_logs(app: str, rg: str, revision: str) -> str:
    try:
        return subprocess.run(  # nosec B603 B607
            ["az", "containerapp", "logs", "show", "-n", app, "-g", rg, "--revision", revision, "--tail", "40"],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        ).stdout
    except (OSError, subprocess.SubprocessError) as e:  # best-effort evidence, never masks the verdict
        return f"(could not fetch logs: {type(e).__name__}: {e})"


def _props(rev: dict) -> dict:
    return rev.get("properties", rev)


def _image(rev: dict) -> str:
    containers = _props(rev).get("template", {}).get("containers") or [{}]
    return containers[0].get("image", "")


def _summary(rev: dict) -> str:
    p = _props(rev)
    return (
        f"{rev.get('name')} health={p.get('healthState')} running={p.get('runningState')} "
        f"provisioning={p.get('provisioningState')} traffic={p.get('trafficWeight')} replicas={p.get('replicas')}"
    )


def wait_for_revision(
    app: str,
    rg: str,
    expected_image: str,
    *,
    timeout_s: int = DEFAULT_TIMEOUT_S,
    poll_s: int = DEFAULT_POLL_S,
    list_revisions: Callable[[str, str], list[dict]] = az_list_revisions,
    dump_logs: Callable[[str, str, str], str] = az_dump_revision_logs,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
    log: Callable[[str], None] = print,
) -> int:
    """Return 0 when the revision carrying ``expected_image`` serves, 1 otherwise.
    Every collaborator is injectable so the verdict logic is testable without Azure."""
    start = clock()
    last_seen = "(no revision observed yet)"
    while True:
        elapsed = clock() - start
        try:
            revisions = list_revisions(app, rg)
        except Exception as e:  # az hiccup: keep polling until the deadline
            log(f"WARN {app}: az revision list failed ({type(e).__name__}: {str(e)[:200]}), retrying")
            revisions = None

        if revisions is not None:
            carriers = [r for r in revisions if _image(r) == expected_image]
            others = [r for r in revisions if _image(r) != expected_image]
            if not carriers:
                last_seen = "no revision carries the image; live: " + "; ".join(_summary(r) for r in revisions)
                if elapsed > NO_CARRIER_GRACE_S:
                    log(
                        f"FAIL {app}: after {int(elapsed)}s no revision carries {expected_image} — the deploy step did not take"
                    )
                    log(last_seen)
                    return 1
            else:
                new = max(carriers, key=lambda r: _props(r).get("createdTime") or "")
                p = _props(new)
                last_seen = _summary(new)
                log(f"{app}: {last_seen} (t+{int(elapsed)}s)")
                if (
                    p.get("runningState") in FATAL_RUNNING_STATES
                    or p.get("healthState") == "Unhealthy"
                    or p.get("provisioningState") == "Failed"
                ):
                    log(f"FAIL {app}: revision {new.get('name')} is not coming up — crash loop or provisioning failure")
                    log(dump_logs(app, rg, new.get("name", "")))
                    return 1
                blocking_old = [
                    r
                    for r in others
                    if _props(r).get("active") and _props(r).get("runningState") in OLD_STILL_RUNNING_STATES
                ]
                serving = (
                    p.get("healthState") == "Healthy"
                    and p.get("runningState") in SERVING_STATES
                    and int(p.get("trafficWeight") or 0) == 100
                )
                if serving and not blocking_old:
                    log(
                        f"OK {app}: revision {new.get('name')} serves {expected_image} — Healthy, {p.get('runningState')}, 100% traffic, no older replica running"
                    )
                    return 0
                if serving and blocking_old:
                    log(
                        f"{app}: new revision serves but older replicas still run: "
                        + "; ".join(_summary(r) for r in blocking_old)
                    )

        if elapsed + poll_s > timeout_s:
            log(f"FAIL {app}: {timeout_s}s passed and the revision carrying {expected_image} never served")
            log(f"last seen: {last_seen}")
            return 1
        sleep(poll_s)


def main(argv: list[str]) -> int:
    if len(argv) < 4:
        print("usage: cd_wait_revision.py <app> <resource-group> <expected-image> [timeout_s]", file=sys.stderr)
        return 2
    app, rg, image = argv[1], argv[2], argv[3]
    timeout_s = int(argv[4]) if len(argv) > 4 else DEFAULT_TIMEOUT_S
    return wait_for_revision(app, rg, image, timeout_s=timeout_s)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
