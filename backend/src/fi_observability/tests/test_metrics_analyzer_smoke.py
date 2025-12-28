from __future__ import annotations

import json

from backend.src.fi_observability.metrics_analyzer import main
from pathlib import Path

from ._fixtures import repo_root, write_jsonl, write_policy_json


def test_metrics_analyzer_generates_artifacts(tmp_path: Path) -> None:
    policy_path = write_policy_json(tmp_path)
    out_dir = tmp_path / "artifacts"

    logs_path = write_jsonl(
        tmp_path,
        "logs.jsonl",
        events=[
            {"timestamp": "2025-12-18T00:00:00Z", "endpoint": "/health", "latency_ms": 10, "status_code": 200},
            {"timestamp": "2025-12-18T00:00:01Z", "endpoint": "/api/foo", "latency_ms": 900, "status_code": 200},
            {"timestamp": "2025-12-18T00:00:02Z", "endpoint": "/api/foo", "latency_ms": 950, "status_code": 200},
            {"timestamp": "2025-12-18T00:00:03Z", "endpoint": "/api/foo", "latency_ms": 1000, "status_code": 503},
            {"timestamp": "2025-12-18T00:00:04Z", "endpoint": "/api/bar", "latency_ms": 100, "status_code": 200},
        ],
    )

    code = main(
        [
            "--base-path",
            str(repo_root()),
            "--log-source",
            str(logs_path),
            "--slo-policy",
            str(policy_path),
            "--environment",
            "local",
            "--out-dir",
            str(out_dir),
        ]
    )
    assert code == 0

    report_path = out_dir / "metrics_report.json"
    assert report_path.exists()
    assert (out_dir / "metrics_report.json.sha256").exists()

    html_path = out_dir / "metrics_report.html"
    assert html_path.exists()
    assert (out_dir / "metrics_report.html.sha256").exists()

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["tool"] == "metrics_analyzer"
    assert report["mode"] == "read_only"

    by_endpoint = report["by_endpoint"]
    endpoints = {row["endpoint"] for row in by_endpoint}
    assert "/api/foo" in endpoints

    foo = next(row for row in by_endpoint if row["endpoint"] == "/api/foo")
    assert foo["count"] == 3
    assert foo["errors"] == 1
