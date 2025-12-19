from __future__ import annotations

import json
from pathlib import Path


def repo_root() -> Path:
    # backend/src/fi_observability/tests/_fixtures.py -> repo root
    return Path(__file__).resolve().parents[4]


def write_policy_json(tmp_path: Path) -> Path:
    policy = {
        "services": {
            "public_api": {"p95_ms": 800.0, "p99_ms": 1200.0, "error_rate": 0.01},
            "realtime_talk": {"p95_ms": 5000.0, "error_rate": 0.01},
            "soap_generation": {"p95_ms": 1500.0, "error_rate": 0.01},
            "internal": {"p95_ms": 1200.0, "error_rate": 0.02},
            "worker": {"p95_ms": 2000.0, "error_rate": 0.02},
        }
    }

    p = tmp_path / "slo_policy.json"
    p.write_text(json.dumps(policy), encoding="utf-8")
    return p


def write_jsonl(tmp_path: Path, name: str, events: list[dict]) -> Path:
    p = tmp_path / name
    lines = [json.dumps(e, ensure_ascii=False) for e in events]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p
