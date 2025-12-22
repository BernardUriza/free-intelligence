from __future__ import annotations

import json

from backend.src.fi_observability.trace_inspector import main
from pathlib import Path

from ._fixtures import repo_root, write_jsonl, write_policy_json


def test_trace_inspector_generates_reports(tmp_path: Path) -> None:
    policy_path = write_policy_json(tmp_path)
    out_dir = tmp_path / "artifacts"

    logs_path = write_jsonl(
        tmp_path,
        "logs.jsonl",
        events=[
            {
                "timestamp": "2025-12-18T00:00:00Z",
                "idempotency_key": "idem-1",
                "layer": "PUBLIC",
                "endpoint": "/api/workflows/aurity/sessions",
                "latency_ms": 100,
                "status_code": 200,
            },
            {
                "timestamp": "2025-12-18T00:00:01Z",
                "idempotency_key": "idem-1",
                "layer": "INTERNAL",
                "endpoint": "/internal/do-thing",
                "latency_ms": 300,
                "status_code": 200,
            },
            {
                "timestamp": "2025-12-18T00:00:02Z",
                "idempotency_key": "idem-1",
                "layer": "WORKER",
                "endpoint": "worker.task",
                "latency_ms": 700,
                "status_code": 200,
            },
            {
                "timestamp": "2025-12-18T00:00:03Z",
                "workflow_id": "wf-2",
                "layer": "PUBLIC",
                "endpoint": "/api/workflows/aurity/sessions",
                "latency_ms": 10,
                "status_code": 200,
            },
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
            "--top",
            "10",
        ]
    )
    assert code == 0

    json_path = out_dir / "traces_report.json"
    dot_path = out_dir / "traces_top.dot"
    assert json_path.exists()
    assert (out_dir / "traces_report.json.sha256").exists()
    assert dot_path.exists()
    assert (out_dir / "traces_top.dot.sha256").exists()

    report = json.loads(json_path.read_text(encoding="utf-8"))
    assert report["tool"] == "trace_inspector"
    assert report["summary"]["traces_total"] >= 2

    top_traces = report["top_traces"]
    assert len(top_traces) >= 1
    assert top_traces[0]["trace_id"] == "idem-1"
    assert float(top_traces[0]["total_latency_ms"]) >= 1100.0
