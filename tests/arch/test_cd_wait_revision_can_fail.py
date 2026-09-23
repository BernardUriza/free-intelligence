"""The CD's revision gate must be able to turn RED — and the workflow must use it.

2026-09-17 → 09-18: fourteen `persona-gateway` revisions crash-looped at boot, ACA
kept the previous replica alive, and the CD reported success fourteen times because
its check grepped `persona_gateway_starting` — a line printed BEFORE the crash. A
check that cannot fail proves nothing. These tests drive `scripts/cd_wait_revision.py`
with canned revision lists (no Azure, no sleep) through every verdict, and pin that
`cd.yml` calls it for the two min=1 apps instead of the log grep.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "cd_wait_revision.py"
CD_YML = REPO / ".github" / "workflows" / "cd.yml"

spec = importlib.util.spec_from_file_location("cd_wait_revision", SCRIPT)
assert spec is not None and spec.loader is not None, f"cannot load {SCRIPT}"
cd_wait = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cd_wait)

NEW_IMAGE = "ghcr.io/bernarduriza/discord-bot/persona-gateway:newsha"
OLD_IMAGE = "ghcr.io/bernarduriza/discord-bot/persona-gateway:oldsha"


def _rev(name, image, *, health="Healthy", running="RunningAtMaxScale", traffic=100, active=True, created="2"):
    return {
        "name": name,
        "properties": {
            "active": active,
            "healthState": health,
            "runningState": running,
            "provisioningState": "Provisioned",
            "trafficWeight": traffic,
            "replicas": 1,
            "createdTime": created,
            "template": {"containers": [{"image": image}]},
        },
    }


class _Scenario:
    """Feeds one canned revision list per poll; the last frame repeats. A fake
    clock advances by `poll_s` on every sleep, so the deadline is deterministic."""

    def __init__(self, frames):
        self.frames = list(frames)
        self.polls = 0
        self.now = 0.0
        self.lines: list[str] = []
        self.logs_dumped_for: list[str] = []

    def list_revisions(self, app, rg):
        frame = self.frames[min(self.polls, len(self.frames) - 1)]
        self.polls += 1
        return frame

    def sleep(self, s):
        self.now += s

    def clock(self):
        return self.now

    def dump_logs(self, app, rg, revision):
        self.logs_dumped_for.append(revision)
        return "Traceback (most recent call last): ... TypeError: Config.__init__()"

    def run(self, **kw):
        return cd_wait.wait_for_revision(
            "persona-gateway",
            "insult-rg",
            NEW_IMAGE,
            list_revisions=self.list_revisions,
            dump_logs=self.dump_logs,
            sleep=self.sleep,
            clock=self.clock,
            log=self.lines.append,
            **kw,
        )


def test_green_when_the_new_revision_serves_and_the_old_one_is_gone():
    s = _Scenario(
        [
            [
                _rev("gw--1", OLD_IMAGE, created="1"),
                _rev("gw--2", NEW_IMAGE, health="None", running="Activating", traffic=0),
            ],
            [_rev("gw--1", OLD_IMAGE, running="Deprovisioning", traffic=0, created="1"), _rev("gw--2", NEW_IMAGE)],
        ]
    )
    assert s.run() == 0
    assert s.polls == 2
    assert any(line.startswith("OK persona-gateway: revision gw--2") for line in s.lines)


def test_red_immediately_on_a_crash_loop_without_waiting_for_the_deadline():
    """The founding case: the new revision never comes up, the OLD replica keeps
    serving. The old check said success here. This one says red on the first
    frame that shows the failure — and dumps that revision's logs as evidence."""
    s = _Scenario(
        [
            [
                _rev("gw--212", OLD_IMAGE, created="1"),
                _rev("gw--213", NEW_IMAGE, health="Unhealthy", running="Failed", traffic=0),
            ],
        ]
    )
    assert s.run() == 1
    assert s.polls == 1
    assert s.logs_dumped_for == ["gw--213"]
    assert any("FAIL persona-gateway: revision gw--213" in line for line in s.lines)
    assert any("TypeError" in line for line in s.lines)


def test_red_when_the_new_revision_never_leaves_activating_before_the_deadline():
    """A revision stuck Activating (image pull loop, probe never green) never
    flips to Failed — only the clock catches it."""
    s = _Scenario(
        [
            [
                _rev("gw--1", OLD_IMAGE, created="1"),
                _rev("gw--2", NEW_IMAGE, health="None", running="Activating", traffic=0),
            ]
        ]
    )
    assert s.run(timeout_s=60, poll_s=15) == 1
    assert any("60s passed" in line for line in s.lines)


def test_red_when_no_revision_carries_the_new_image_the_deploy_step_did_not_take():
    """`az containerapp update` is continue-on-error in the workflow; if it fails,
    the only trace is that nothing carries the new image. Green here would be the
    fake-green through a different door."""
    s = _Scenario([[_rev("gw--1", OLD_IMAGE, created="1")]])
    assert s.run(timeout_s=600, poll_s=30) == 1
    assert any("no revision carries" in line for line in s.lines)
    # it gave the deploy the grace period, not the whole deadline
    assert s.now <= cd_wait.NO_CARRIER_GRACE_S + 30


def test_not_green_while_an_older_replica_still_runs_beside_the_new_one():
    """Two running replicas of a Discord bot = duplicate replies. Healthy+100%
    on the new one is not enough while the old one still holds replicas."""
    s = _Scenario(
        [
            [_rev("gw--1", OLD_IMAGE, traffic=0, created="1"), _rev("gw--2", NEW_IMAGE)],
            [_rev("gw--1", OLD_IMAGE, traffic=0, created="1"), _rev("gw--2", NEW_IMAGE)],
            [_rev("gw--1", OLD_IMAGE, running="Deprovisioning", traffic=0, created="1"), _rev("gw--2", NEW_IMAGE)],
        ]
    )
    assert s.run() == 0
    assert s.polls == 3
    assert any("older replicas still run" in line for line in s.lines)


def test_an_az_hiccup_is_retried_not_a_verdict():
    calls = {"n": 0}

    def flaky(app, rg):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("az: connection reset")
        return [_rev("gw--2", NEW_IMAGE)]

    s = _Scenario([])
    s.list_revisions = flaky
    assert s.run() == 0
    assert calls["n"] == 2
    assert any(line.startswith("WARN") for line in s.lines)


@pytest.mark.parametrize("app", ["persona-gateway", "khimeras-host"])
def test_cd_yml_gates_each_min1_app_on_its_revision_state(app):
    text = CD_YML.read_text()
    assert f'python3 scripts/cd_wait_revision.py {app} "$RG" "$REGISTRY/{app}:$NEW_SHA"' in text, (
        f"cd.yml must gate {app} on the revision that carries the new image"
    )


def test_cd_yml_no_longer_greps_a_log_line_printed_before_the_crash():
    text = CD_YML.read_text()
    assert 'grep -q "persona_gateway_starting"' not in text, (
        "persona_gateway_starting is logged BEFORE the gateway can crash — grepping it is the check that cannot fail"
    )
