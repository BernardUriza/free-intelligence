"""The runner's startup + readiness probes are declared in the repo and ride every deploy.

Until 2026-10-03 every `persona-runner` revision had `probes: []`: ACA's implicit
TCP defaults handed a cold replica traffic the moment uvicorn bound, ~13 s
before the turn pipeline was warm. The probes now live in
`scripts/cd_runner_template.py` and `cd.yml` applies them with the image. These
tests fail if the probe disappears from either place, if the template drops what
the live container already had, or if the probe's budget falls under the
readiness cap (a probe that restarts a replica for a slow warmup is a restart
loop, not a guard).
"""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from persona_runner.core import readiness

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "cd_runner_template.py"
CD_YML = REPO / ".github" / "workflows" / "cd.yml"

spec = importlib.util.spec_from_file_location("cd_runner_template", SCRIPT)
assert spec is not None and spec.loader is not None, f"cannot load {SCRIPT}"
tpl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tpl)

IMAGE = "ghcr.io/bernarduriza/discord-bot/persona-runner:newsha"


def _live() -> dict:
    """Shape of `az containerapp show -o json` for persona-runner (2026-10-03)."""
    return {
        "name": "persona-runner",
        "properties": {
            "configuration": {"secrets": [{"name": "postgres-url"}], "ingress": {"targetPort": 8080}},
            "template": {
                "containers": [
                    {
                        "name": "persona-runner",
                        "image": "ghcr.io/bernarduriza/discord-bot/persona-runner:oldsha",
                        "env": [
                            {"name": "POSTGRES_URL", "secretRef": "postgres-url"},
                            {"name": "AIRE_TURN_MODE", "value": "agent"},
                        ],
                        "resources": {"cpu": 2.0, "memory": "4Gi", "ephemeralStorage": "8Gi"},
                        "volumeMounts": [{"mountPath": "/data/insult-workspace", "volumeName": "workspace"}],
                    }
                ],
                "revisionSuffix": "",
                "scale": {"minReplicas": 0, "maxReplicas": 1, "cooldownPeriod": 300},
                "terminationGracePeriodSeconds": 600,
                "volumes": [{"name": "workspace", "storageName": "insult-workspace", "storageType": "AzureFile"}],
            },
        },
    }


def _probe(patch: dict, kind: str) -> dict:
    probes = patch["properties"]["template"]["containers"][0]["probes"]
    found = [p for p in probes if p["type"] == kind]
    assert len(found) == 1, f"expected one {kind} probe, got {probes}"
    return found[0]


def test_the_patch_sets_image_probes_and_grace_and_keeps_the_rest():
    patch = tpl.render_patch(_live(), IMAGE)
    template = patch["properties"]["template"]
    container = template["containers"][0]
    assert container["image"] == IMAGE
    assert _probe(patch, "Startup")["httpGet"] == {"path": "/health", "port": 8080}
    assert _probe(patch, "Readiness")["httpGet"] == {"path": "/ready", "port": 8080}
    assert template["terminationGracePeriodSeconds"] == 600
    # ARM replaces arrays: whatever the live container had must ride along.
    assert container["env"] == _live()["properties"]["template"]["containers"][0]["env"]
    assert container["volumeMounts"] and template["volumes"]
    assert template["scale"]["minReplicas"] == 0, "the template must never decide min replicas (Bernard's call)"
    assert "revisionSuffix" not in template
    # Template-only: secrets and ingress are never part of this PATCH.
    assert set(patch["properties"]) == {"template"}


def test_the_patch_does_not_mutate_its_input():
    live = _live()
    tpl.render_patch(live, IMAGE)
    assert live == _live()


def test_a_second_container_is_refused_rather_than_silently_dropped():
    live = _live()
    live["properties"]["template"]["containers"].append({"name": "sidecar", "image": "x"})
    with pytest.raises(SystemExit):
        tpl.render_patch(live, IMAGE)


def test_liveness_stays_the_platform_default():
    """RESISTANCE: an HTTP liveness would let a busy event loop restart a replica
    mid-turn. Only startup and readiness are declared."""
    kinds = {p["type"] for p in tpl.RUNNER_PROBES}
    assert kinds == {"Startup", "Readiness"}


def test_probe_numbers_stay_inside_the_api_limits():
    """ContainerAppProbe: failureThreshold 1-10, initialDelaySeconds 1-60,
    periodSeconds 1-240; successThreshold must be 1 for startup."""
    for p in tpl.RUNNER_PROBES:
        assert 1 <= p["failureThreshold"] <= 10, p
        assert 1 <= p.get("initialDelaySeconds", 1) <= 60, p
        assert 1 <= p["periodSeconds"] <= 240, p
        assert p["successThreshold"] == 1, p


def test_the_startup_probe_asks_liveness_never_warmth():
    """RESISTANCE: a startup probe that runs out RESTARTS the container. Pointed
    at /ready, a warmup slower than its 10-failure window would be a restart
    loop. Warmth belongs to readiness, which only holds traffic."""
    s = _probe(tpl.render_patch(_live(), IMAGE), "Startup")
    assert s["httpGet"]["path"] == "/health"
    window = s["initialDelaySeconds"] + s["periodSeconds"] * s["failureThreshold"]
    # worst measured booting -> "Uvicorn running" was 7 s (2026-10-03, 369 boots)
    assert window >= 3 * 7, window


def test_readiness_gates_on_warmth_at_a_tight_cadence():
    r = _probe(tpl.render_patch(_live(), IMAGE), "Readiness")
    assert r["httpGet"]["path"] == "/ready"
    # ACA's implicit TCP readiness polls every 5 s; the point is to beat it.
    assert r["periodSeconds"] <= 2


def test_the_readiness_cap_releases_traffic_well_before_the_ingress_cut():
    """Without the cap a hung warmup keeps /ready red and the ingress holds every
    turn until its fixed 240 s cut (robustness.md)."""
    assert readiness.READY_CAP_S <= 60


def test_cd_yml_applies_the_rendered_template_with_the_new_image():
    text = CD_YML.read_text()
    assert "python3 scripts/cd_runner_template.py runner-live.json" in text
    assert '"$REGISTRY/persona-runner:${{ env.NEW_SHA }}" > runner-patch.json' in text
    assert "--yaml runner-patch.json" in text


def test_cd_yml_goes_red_if_the_probe_did_not_land():
    text = CD_YML.read_text()
    assert "probes[].join(':', [type, httpGet.path])" in text
    assert 'if [ "$PROBE_PATHS" != "Startup:/health,Readiness:/ready" ]; then' in text


# --- /ready itself ---------------------------------------------------------


@pytest.fixture(autouse=True)
def _fresh_readiness():
    readiness.reset()
    yield
    readiness.reset()


def _client():
    from fastapi import FastAPI

    from persona_runner.api import ops

    app = FastAPI()
    app.include_router(ops.router)
    return TestClient(app)


def test_ready_is_503_until_marked_and_200_after():
    c = _client()
    r = c.get("/ready")
    assert r.status_code == 503 and r.json()["ready"] is False
    readiness.mark_ready("warm")
    r = c.get("/ready")
    assert r.status_code == 200 and r.json() == {"ready": True, "reason": "warm"}


def test_ready_never_flips_back_once_true():
    readiness.mark_ready("warm")
    readiness.mark_ready("cap")
    assert readiness.state() == {"ready": True, "reason": "warm"}


def test_health_stays_200_while_not_ready():
    """RESISTANCE: liveness must not inherit readiness — a warming replica is alive."""
    assert _client().get("/health").status_code == 200


def test_gate_marks_ready_when_the_warmup_ends():
    async def run():
        warm = asyncio.create_task(asyncio.sleep(0))
        await readiness.gate(warm, cap_s=5)

    asyncio.run(run())
    assert readiness.state() == {"ready": True, "reason": "warm"}


def test_gate_marks_ready_at_the_cap_and_leaves_the_warmup_running():
    """A hung warmup (Postgres, the model download) never keeps the replica out
    of rotation — and hitting the cap must not cancel the warmup."""

    async def run():
        warm = asyncio.create_task(asyncio.sleep(10))
        await readiness.gate(warm, cap_s=0.05)
        still_running = not warm.done()
        warm.cancel()
        return still_running

    assert asyncio.run(run()) is True
    assert readiness.state() == {"ready": True, "reason": "cap"}


def test_gate_marks_ready_even_if_the_warmup_raises():
    async def boom():
        raise RuntimeError("warmup exploded")

    async def run():
        await readiness.gate(asyncio.create_task(boom()), cap_s=5)

    asyncio.run(run())
    assert readiness.state() == {"ready": True, "reason": "warm_failed"}


def test_the_cd_check_expects_exactly_what_the_script_declares():
    """The CD's post-deploy check and the declared probes are one fact: if one
    moves without the other, the check goes red on a correct deploy (or green
    on a wrong one)."""
    declared = ",".join(f"{p['type']}:{p['httpGet']['path']}" for p in tpl.RUNNER_PROBES)
    assert f'"$PROBE_PATHS" != "{declared}"' in CD_YML.read_text()
