#!/usr/bin/env python3
"""Render the `persona-runner` template the CD applies: new image + declared probes
(startup on `/health`, readiness on `/ready`).

    az containerapp show -n persona-runner -g "$RG" -o json > runner-live.json
    python3 scripts/cd_runner_template.py runner-live.json "$IMAGE" > runner-patch.json
    az containerapp update -n persona-runner -g "$RG" --yaml runner-patch.json

`az containerapp update` has no flag for probes, so until 2026-10-03 the runner
ran with NO declared probes (`probes: []` on every revision) and ACA's implicit
TCP defaults decided when a cold replica got traffic: as soon as uvicorn bound
the port, ~13 s before the turn pipeline was warm. The probes live here, in the
repo, and ride every deploy — never an `az` by hand that the next deploy forgets.

The output is a template-only PATCH (JSON is valid YAML). ARM merge-patches
objects but REPLACES arrays, so the container is sent whole: everything the
live app has (env, secretRefs, resources, volume mounts) is copied from the
`show`, and only `image`, `probes` and the grace period are set here. Secrets
and ingress live under `configuration`, which this patch never touches.

Standalone on purpose: the deploy job checks out `scripts/` only.
"""

from __future__ import annotations

import copy
import json
import sys

APP = "persona-runner"
PORT = 8080

# Measured 2026-10-03 (KQL over 30 days, 369 replicas: 109 KEDA cold starts +
# 260 rollouts):
#   "[entrypoint] booting" -> "Uvicorn running"  0-3 s (365/369), worst 7 s
#   lifespan start -> turn_pipeline_warm_ready     12.9-14.7 s (n=12)
#   persona_runner/core/readiness.READY_CAP_S      45 s (ready regardless)
#
# The API caps failureThreshold at 10 (ContainerAppProbe spec), so a startup
# probe cannot carry a 45 s warmup at a 2 s cadence — and it must not: a startup
# probe that runs out RESTARTS the container, which would turn a slow warmup
# into a restart loop. The split is therefore:
#
# Startup (restarts on failure) asks "did the process come up?" — `/health`,
# always 200 once uvicorn binds. 1 + 2 x 10 = 21 s window, 3x the worst bind.
# Readiness (holds traffic, never restarts) asks "is the pipeline warm?" —
# `/ready`, 503 until warm or capped, every 2 s, so the ingress releases the
# first turn <=2 s after warm. Without it ACA adds its TCP default (period 5 s,
# passes on bind). `/ready` never flips back, so readiness cannot eject a
# serving replica later.
# Liveness: not declared — ACA's TCP default stays (an HTTP liveness would put
# a mid-turn replica at the mercy of a busy event loop).
RUNNER_PROBES = [
    {
        "type": "Startup",
        "httpGet": {"path": "/health", "port": PORT},
        "initialDelaySeconds": 1,
        "periodSeconds": 2,
        "timeoutSeconds": 3,
        "failureThreshold": 10,
        "successThreshold": 1,
    },
    {
        "type": "Readiness",
        "httpGet": {"path": "/ready", "port": PORT},
        "initialDelaySeconds": 1,
        "periodSeconds": 2,
        "timeoutSeconds": 3,
        "failureThreshold": 10,
        "successThreshold": 1,
    },
]

# El lifespan espera los jobs abiertos hasta RUNNER_SHUTDOWN_DRAIN_S (570) y
# suelta sus filas al vencer; techo = presupuesto del turno del gateway (600).
TERMINATION_GRACE_S = 600


def render_patch(live: dict, image: str) -> dict:
    """The template-only PATCH body for `live` (an `az containerapp show`)."""
    props = live.get("properties", live)
    template = copy.deepcopy(props["template"])
    containers = template.get("containers") or []
    if len(containers) != 1 or containers[0].get("name") != APP:
        names = [c.get("name") for c in containers]
        raise SystemExit(f"expected exactly one container named {APP!r}, live has {names}")
    container = containers[0]
    container["image"] = image
    container["probes"] = copy.deepcopy(RUNNER_PROBES)
    template["terminationGracePeriodSeconds"] = TERMINATION_GRACE_S
    # A suffix copied from the live revision would collide with it.
    template.pop("revisionSuffix", None)
    return {"properties": {"template": template}}


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(f"usage: {argv[0]} <live-app.json> <image>", file=sys.stderr)
        return 2
    with open(argv[1]) as f:
        live = json.load(f)
    json.dump(render_patch(live, argv[2]), sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
