from __future__ import annotations

import argparse
import concurrent.futures
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
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


@dataclass(frozen=True)
class ProbeResult:
    path: str
    ok: bool
    status_code: int | None
    latency_ms: float


def build_cli_parser() -> argparse.ArgumentParser:
    parser = build_parser(
        prog="fi-observability-health",
        description=(
            "Run shallow/deep health probes (read-only GET) and a finite load simulation. "
            "Evaluates error rate and latency against SLOs from a policy file."
        ),
    )
    add_common_args(parser)

    parser.add_argument(
        "--base-url",
        required=True,
        help="Base URL for the target system (e.g. http://localhost:7001).",
    )
    parser.add_argument(
        "--shallow-paths",
        default="/health",
        help="Comma-separated shallow health endpoints (default: /health).",
    )
    parser.add_argument(
        "--deep-paths",
        default="",
        help="Comma-separated deep health endpoints (optional).",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=5.0,
        help="Per-request timeout in seconds.",
    )

    parser.add_argument(
        "--load-path",
        default="/health",
        help="Path used for finite load simulation (default: /health).",
    )
    parser.add_argument(
        "--requests",
        type=int,
        default=30,
        help="Number of requests for load simulation.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Concurrency level for load simulation.",
    )

    return parser


def run(args: argparse.Namespace) -> int:
    """Execute health validation probes against API endpoints.

    Performs shallow (HTTP status) and deep (response validation) health
    checks against configured endpoints. Results are compared against SLO
    policy thresholds to determine overall system health.

    Args:
        args: CLI arguments including base URL, probe paths, and timeouts

    Returns:
        Exit code (0 if all probes pass, 1 if any fail)
    """
    try:
        ensure_read_only_mode(True)
        common = coerce_common_args(args)
        validate_base_path(common.base_path)

        policy = load_policy(common.slo_policy)
        policy_hash = policy_sha256(policy)

        base_url = str(args.base_url)
        shallow_paths = _split_paths(str(args.shallow_paths))
        deep_paths = _split_paths(str(args.deep_paths))
        timeout_s = float(args.timeout_seconds)

        # Shallow + deep probes
        probes: list[ProbeResult] = []
        for p in shallow_paths:
            probes.append(_probe_get(base_url, p, timeout_s))
        for p in deep_paths:
            probes.append(_probe_get(base_url, p, timeout_s))

        # Load simulation
        load_path = str(args.load_path)
        total_requests = max(0, int(args.requests))
        concurrency = max(1, int(args.concurrency))

        load_results = _run_load(base_url, load_path, timeout_s, total_requests, concurrency)

        latencies = [r.latency_ms for r in load_results]
        errors = sum(1 for r in load_results if not r.ok)
        error_rate = (errors / total_requests) if total_requests else 0.0

        # Health SLOs are treated as PUBLIC API defaults unless overridden by policy.
        limits = slo_limits(policy, "public_api")
        p95_ms = _p95(latencies)

        violations: list[str] = []
        if p95_ms is not None and (limit := limits.get("p95_ms")) is not None and p95_ms > limit:
            violations.append("p95_ms")
        if (limit := limits.get("error_rate")) is not None and error_rate > limit:
            violations.append("error_rate")

        report: dict[str, Any] = {
            "traceability": traceability_block("AUR-PROMPT-OBS-1.0"),
            "tool": "health_validator",
            "mode": "read_only",
            "environment": common.environment,
            "inputs": {
                "base_url": base_url,
                "shallow_paths": shallow_paths,
                "deep_paths": deep_paths,
                "timeout_seconds": timeout_s,
                "load_path": load_path,
                "requests": total_requests,
                "concurrency": concurrency,
                "slo_policy": common.slo_policy,
                "slo_policy_sha256": policy_hash,
            },
            "probes": [
                {
                    "path": p.path,
                    "ok": p.ok,
                    "status_code": p.status_code,
                    "latency_ms": round(p.latency_ms, 3),
                }
                for p in probes
            ],
            "load": {
                "count": total_requests,
                "errors": errors,
                "error_rate": round(error_rate, 6),
                "p95_ms": None if p95_ms is None else round(p95_ms, 3),
                "slo_limits": limits,
                "slo_violations": sorted(violations),
            },
        }

        out_json = write_json_artifact(common.out_dir, "health_report.json", redact_mapping(report))

        from ._common import safe_print

        safe_print({"ok": True, "tool": "health_validator", "artifacts": {"json": str(out_json)}})
        return 0
    except Exception as e:
        from ._common import safe_print

        safe_print({"ok": False, "tool": "health_validator", **compact_exception(e)})
        return 2


def _split_paths(csv: str) -> list[str]:
    parts = [p.strip() for p in csv.split(",") if p.strip()]
    out: list[str] = []
    for p in parts:
        if not p.startswith("/"):
            p = "/" + p
        out.append(p)
    return out


def _probe_get(base_url: str, path: str, timeout_s: float) -> ProbeResult:
    url = base_url.rstrip("/") + path

    start = time.perf_counter()
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            status = int(getattr(resp, "status", 200))
            # Avoid reading the body to prevent any accidental PII/PHI processing.
            ok = 200 <= status < 400
    except urllib.error.HTTPError as e:
        status = int(getattr(e, "code", 0))
        ok = False
    except Exception:
        status = None
        ok = False
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000.0

    return ProbeResult(path=path, ok=ok, status_code=status, latency_ms=elapsed_ms)


def _run_load(
    base_url: str,
    path: str,
    timeout_s: float,
    total_requests: int,
    concurrency: int,
) -> list[ProbeResult]:
    if total_requests <= 0:
        return []

    results: list[ProbeResult] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(_probe_get, base_url, path, timeout_s) for _ in range(total_requests)
        ]
        for fut in concurrent.futures.as_completed(futures):
            results.append(fut.result())

    # Stable ordering for report
    results.sort(key=lambda r: (r.ok is False, r.latency_ms))
    return results


def _p95(latencies: list[float]) -> float | None:
    if not latencies:
        return None

    xs = sorted(latencies)
    idx = round(0.95 * (len(xs) - 1))
    idx = max(0, min(len(xs) - 1, idx))
    return float(xs[idx])


def main(argv: list[str] | None = None) -> int:
    parser = build_cli_parser()
    ns = parser.parse_args(argv)
    return run(ns)


if __name__ == "__main__":
    raise SystemExit(main())
