"""When a cold replica is READY: its turn pipeline is warm, or the cap ran out.

`/health` answers 200 the moment uvicorn binds — it is the liveness probe and
must stay that way. Readiness is a different question: may the ingress hand this
replica a turn? On a cold start the answer used to be "as soon as the port
accepts", which is ~13 s before `warm_at_boot` finishes the pool + embedding
model. The first turn then waited for that load inside its own budget.

The readiness probe of `persona-runner` (declared in
`scripts/cd_runner_template.py`, applied by the CD) asks `GET /ready`, which
answers 503 until `gate` marks the replica ready; the startup probe asks
`/health` (did the process come up?), because a startup probe that runs out
restarts the container. Two rules keep this from ever becoming the outage it
is meant to prevent:

- **The cap.** Readiness never waits on a downstream forever. If the warmup
  hangs (Postgres, the model download), the replica goes ready anyway after
  `READY_CAP_S` and serves turns the way it did before this module existed —
  lazy load, or bare without memory. A probe that blocks on a dependency turns
  a dependency blip into a restart loop (testing.md, anti-pattern 11).
- **One way.** Once ready, always ready. `/ready` never flips back, so the
  readiness probe cannot pull a serving replica out of rotation over a
  downstream that came and went.

Measured 2026-10-03 over 12 boots (KQL, 30 days): `turn_pipeline_warm_ready`
lands 12.9-14.7 s after the lifespan starts. The cap is 3x the worst of them.
"""

from __future__ import annotations

import asyncio
import time

import structlog

log = structlog.get_logger()

# 3x the slowest warmup measured (14.7 s). Without the cap a hung warmup would
# keep the readiness probe red forever and the ingress would hold every turn
# until its 240 s cut — pinned by tests/arch/test_runner_startup_probe.py.
READY_CAP_S = 45.0

_ready = False
_reason = ""
_started = time.monotonic()


def is_ready() -> bool:
    return _ready


def state() -> dict:
    return {"ready": _ready, "reason": _reason or None}


def mark_ready(reason: str) -> None:
    """Idempotent: the first reason wins, later calls are no-ops."""
    global _ready, _reason
    if _ready:
        return
    _ready, _reason = True, reason
    log.info("agent_runner_ready", reason=reason, since_boot_ms=int((time.monotonic() - _started) * 1000))


def reset() -> None:
    """Back to not-ready (tests, and the start of each lifespan)."""
    global _ready, _reason, _started
    _ready, _reason, _started = False, "", time.monotonic()


async def gate(warm: asyncio.Task, cap_s: float = READY_CAP_S) -> None:
    """Mark ready when `warm` ends (however it ends) or when `cap_s` runs out.

    `warm` is shielded: hitting the cap stops the WAIT, never the warmup, which
    keeps loading in the background exactly as before.
    """
    try:
        await asyncio.wait_for(asyncio.shield(warm), timeout=cap_s)
    except TimeoutError:
        mark_ready("cap")
        return
    except asyncio.CancelledError:
        raise
    except Exception:
        # warm_at_boot never raises by contract; if it ever does, the replica
        # still serves — a failed warmup is a slower first turn, not a dead one.
        log.exception("agent_runner_ready_warm_raised")
        mark_ready("warm_failed")
        return
    mark_ready("warm")
