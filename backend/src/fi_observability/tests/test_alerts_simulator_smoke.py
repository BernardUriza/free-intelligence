from __future__ import annotations

import json
from pathlib import Path

from backend.src.fi_observability.alerts_simulator import main

from ._fixtures import repo_root, write_policy_json


def test_alerts_simulator_dry_run(tmp_path: Path) -> None:
    policy_path = write_policy_json(tmp_path)
    out_dir = tmp_path / "artifacts"

    code = main(
        [
            "--base-path",
            str(repo_root()),
            "--slo-policy",
            str(policy_path),
            "--environment",
            "local",
            "--dry-run",
            "--service",
            "public_api",
            "--out-dir",
            str(out_dir),
        ]
    )
    assert code == 0

    json_path = out_dir / "alerts_simulation.json"
    assert json_path.exists()
    assert (out_dir / "alerts_simulation.json.sha256").exists()

    report = json.loads(json_path.read_text(encoding="utf-8"))
    assert report["tool"] == "alerts_simulator"
    assert report["inputs"]["dry_run"] is True
    assert isinstance(report["simulations"], list)
    assert report["simulations"], "expected at least one simulation"
