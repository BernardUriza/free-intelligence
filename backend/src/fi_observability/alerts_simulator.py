from __future__ import annotations

import argparse
from typing import Any

from ._common import (
    add_common_args,
    build_parser,
    coerce_common_args,
    compact_exception,
    ensure_read_only_mode,
    load_policy,
    policy_sha256,
    redact_mapping,
    slo_limits,
    traceability_block,
    validate_base_path,
    write_json_artifact,
)


def build_cli_parser() -> argparse.ArgumentParser:
    parser = build_parser(
        prog="fi-observability-alerts",
        description=(
            "Simulate alert conditions (SLO violations, 5xx spikes, timeouts) in dry-run mode. "
            "Does not send notifications; only validates alert logic against the active SLO policy."
        ),
    )
    add_common_args(parser)

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Required explicit flag: run simulations without any external side effects.",
    )
    parser.add_argument(
        "--service",
        default="public_api",
        help="Service key in SLO policy to simulate (default: public_api).",
    )

    return parser


def run(args: argparse.Namespace) -> int:
    try:
        ensure_read_only_mode(True)
        common = coerce_common_args(args)
        validate_base_path(common.base_path)

        if not bool(getattr(args, "dry_run", False)):
            raise ValueError("--dry-run must be provided explicitly")

        policy = load_policy(common.slo_policy)
        policy_hash = policy_sha256(policy)

        service = str(getattr(args, "service", "public_api")).strip().lower() or "public_api"
        limits = slo_limits(policy, service)

        scenarios = _build_scenarios(limits)
        evaluated: list[dict[str, Any]] = []

        for scenario in scenarios:
            evaluated.append(_evaluate_scenario(service, limits, scenario))

        report: dict[str, Any] = {
            "traceability": traceability_block("AUR-PROMPT-OBS-1.0"),
            "tool": "alerts_simulator",
            "mode": "read_only",
            "environment": common.environment,
            "inputs": {
                "dry_run": True,
                "service": service,
                "slo_policy": common.slo_policy,
                "slo_policy_sha256": policy_hash,
            },
            "slo_limits": limits,
            "simulations": evaluated,
        }

        out_json = write_json_artifact(common.out_dir, "alerts_simulation.json", redact_mapping(report))

        from ._common import safe_print

        safe_print({"ok": True, "tool": "alerts_simulator", "artifacts": {"json": str(out_json)}})
        return 0
    except Exception as e:
        from ._common import safe_print

        safe_print({"ok": False, "tool": "alerts_simulator", **compact_exception(e)})
        return 2


def _build_scenarios(limits: dict[str, float]) -> list[dict[str, Any]]:
    # Deterministic synthetic scenarios, no randomness.
    p95_limit = limits.get("p95_ms")
    er_limit = limits.get("error_rate")

    scenarios: list[dict[str, Any]] = [
        {
            "name": "baseline_ok",
            "p95_ms": p95_limit * 0.8 if p95_limit is not None else 500.0,
            "error_rate": er_limit * 0.5 if er_limit is not None else 0.001,
            "timeouts": 0,
            "http_5xx": 0,
        },
        {
            "name": "latency_slo_violation",
            "p95_ms": p95_limit * 1.25 if p95_limit is not None else 2000.0,
            "error_rate": er_limit * 0.5 if er_limit is not None else 0.001,
            "timeouts": 0,
            "http_5xx": 0,
        },
        {
            "name": "error_rate_slo_violation",
            "p95_ms": p95_limit * 0.8 if p95_limit is not None else 500.0,
            "error_rate": er_limit * 2.0 if er_limit is not None else 0.05,
            "timeouts": 0,
            "http_5xx": 25,
        },
        {
            "name": "timeouts_spike",
            "p95_ms": p95_limit * 1.1 if p95_limit is not None else 1200.0,
            "error_rate": er_limit * 1.5 if er_limit is not None else 0.03,
            "timeouts": 10,
            "http_5xx": 5,
        },
    ]

    return scenarios


def _evaluate_scenario(service: str, limits: dict[str, float], scenario: dict[str, Any]) -> dict[str, Any]:
    p95 = float(scenario.get("p95_ms") or 0.0)
    er = float(scenario.get("error_rate") or 0.0)

    alerts: list[str] = []

    if (limit := limits.get("p95_ms")) is not None and p95 > limit:
        alerts.append(f"{service}.p95_ms_high")

    if (limit := limits.get("error_rate")) is not None and er > limit:
        alerts.append(f"{service}.error_rate_high")

    # Additional synthetic signals (no external systems):
    if int(scenario.get("http_5xx") or 0) > 0:
        alerts.append(f"{service}.http_5xx_detected")

    if int(scenario.get("timeouts") or 0) > 0:
        alerts.append(f"{service}.timeouts_detected")

    return {
        "scenario": scenario,
        "alerts_triggered": sorted(set(alerts)),
        "ok": len(alerts) == 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = build_cli_parser()
    ns = parser.parse_args(argv)
    return run(ns)


if __name__ == "__main__":
    raise SystemExit(main())
