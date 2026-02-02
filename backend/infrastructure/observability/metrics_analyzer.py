from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime
from typing import Any

from ._common import (
    add_common_args,
    best_effort_timestamp,
    build_parser,
    coerce_common_args,
    compact_exception,
    ensure_read_only_mode,
    get_endpoint,
    get_status_code,
    iter_json_logs,
    load_policy,
    normalize_service,
    percentile,
    policy_sha256,
    redact_mapping,
    require_log_source,
    slo_limits,
    traceability_block,
    validate_base_path,
    within_range,
    write_json_artifact,
    write_text_artifact,
)


def build_cli_parser() -> argparse.ArgumentParser:
    parser = build_parser(
        prog="fi-observability-metrics",
        description=(
            "Analyze structured JSON logs (structlog-compatible) to compute endpoint latency percentiles "
            "and SLO violations. Produces verifiable, read-only artifacts."
        ),
    )
    add_common_args(parser)

    parser.add_argument(
        "--since",
        default=None,
        help="Filter events since this timestamp (ISO8601 or unix seconds).",
    )
    parser.add_argument(
        "--until",
        default=None,
        help="Filter events until this timestamp (ISO8601 or unix seconds).",
    )
    parser.add_argument(
        "--endpoint-prefix",
        default=None,
        help="Only include endpoints that start with this prefix.",
    )
    parser.add_argument(
        "--max-endpoints",
        type=int,
        default=200,
        help="Limit number of endpoints included in the report (sorted by p95 desc).",
    )

    return parser


def _parse_optional_time(value: str | None) -> datetime | None:
    if value is None:
        return None

    from ._common import parse_time

    return parse_time(value)


def run(args: argparse.Namespace) -> int:
    """Analyze API metrics and compute SLO compliance statistics.

    Processes structured logs to extract latency metrics per endpoint,
    computes percentiles (p50, p95, p99), and checks compliance against
    defined SLO thresholds. Generates reports for capacity planning.

    Args:
        args: CLI arguments including log source, time range, and endpoint filters

    Returns:
        Exit code (0 for success, non-zero for SLO violations or errors)
    """
    try:
        ensure_read_only_mode(True)
        common = coerce_common_args(args)
        validate_base_path(common.base_path)

        policy = load_policy(common.slo_policy)
        policy_hash = policy_sha256(policy)

        log_source = require_log_source(common)

        since = _parse_optional_time(getattr(args, "since", None))
        until = _parse_optional_time(getattr(args, "until", None))
        endpoint_prefix = getattr(args, "endpoint_prefix", None)

        durations_by_endpoint: dict[str, list[float]] = defaultdict(list)
        errors_by_endpoint: dict[str, int] = defaultdict(int)
        counts_by_endpoint: dict[str, int] = defaultdict(int)
        service_by_endpoint: dict[str, str] = {}

        total_events = 0
        used_events = 0

        for event in iter_json_logs(log_source):
            total_events += 1
            ts = best_effort_timestamp(event)
            if (since is not None or until is not None) and not within_range(ts, since, until):
                continue

            endpoint = get_endpoint(event)
            if endpoint is None:
                continue

            if endpoint_prefix and not endpoint.startswith(endpoint_prefix):
                continue

            from ._common import parse_duration_ms

            duration_ms = parse_duration_ms(event)
            if duration_ms is None:
                continue

            used_events += 1
            counts_by_endpoint[endpoint] += 1
            durations_by_endpoint[endpoint].append(float(duration_ms))

            status = get_status_code(event)
            if status is not None and status >= 500:
                errors_by_endpoint[endpoint] += 1

            if endpoint not in service_by_endpoint:
                service_by_endpoint[endpoint] = normalize_service(event, endpoint)

        rows: list[dict[str, Any]] = []
        for endpoint, durations in durations_by_endpoint.items():
            count = counts_by_endpoint[endpoint]
            errors = errors_by_endpoint[endpoint]
            er = (errors / count) if count else 0.0

            p50 = percentile(durations, 0.50)
            p95 = percentile(durations, 0.95)
            p99 = percentile(durations, 0.99)

            service = service_by_endpoint.get(endpoint, "unknown")
            limits = slo_limits(policy, service)

            violations: list[str] = []
            if p95 is not None and (limit := limits.get("p95_ms")) is not None and p95 > limit:
                violations.append("p95_ms")
            if p99 is not None and (limit := limits.get("p99_ms")) is not None and p99 > limit:
                violations.append("p99_ms")
            if (limit := limits.get("error_rate")) is not None and er > limit:
                violations.append("error_rate")

            rows.append(
                {
                    "endpoint": endpoint,
                    "service": service,
                    "count": count,
                    "errors": errors,
                    "error_rate": round(er, 6),
                    "p50_ms": None if p50 is None else round(p50, 3),
                    "p95_ms": None if p95 is None else round(p95, 3),
                    "p99_ms": None if p99 is None else round(p99, 3),
                    "slo_limits": limits,
                    "slo_violations": sorted(violations),
                }
            )

        rows.sort(key=lambda r: (r["p95_ms"] is None, -(r["p95_ms"] or 0.0), r["endpoint"]))
        max_endpoints = int(getattr(args, "max_endpoints", 200))
        rows = rows[: max(0, max_endpoints)]

        report: dict[str, Any] = {
            "traceability": traceability_block("AUR-PROMPT-OBS-1.0"),
            "tool": "metrics_analyzer",
            "mode": "read_only",
            "environment": common.environment,
            "inputs": {
                "log_source": "<stdin>" if log_source == "-" else log_source,
                "slo_policy": common.slo_policy,
                "slo_policy_sha256": policy_hash,
                "since": getattr(args, "since", None),
                "until": getattr(args, "until", None),
                "endpoint_prefix": endpoint_prefix,
            },
            "summary": {
                "events_total": total_events,
                "events_used": used_events,
                "endpoints": len(rows),
                "slo_violations_endpoints": sum(1 for r in rows if r["slo_violations"]),
            },
            "by_endpoint": rows,
        }

        out_json = write_json_artifact(
            common.out_dir, "metrics_report.json", redact_mapping(report)
        )
        out_html = write_text_artifact(common.out_dir, "metrics_report.html", _render_html(report))

        from ._common import safe_print

        safe_print(
            {
                "ok": True,
                "tool": "metrics_analyzer",
                "artifacts": {
                    "json": str(out_json),
                    "html": str(out_html),
                },
            }
        )
        return 0
    except Exception as e:
        from ._common import safe_print

        safe_print({"ok": False, "tool": "metrics_analyzer", **compact_exception(e)})
        return 2


def _render_html(report: dict[str, Any]) -> str:
    rows = report.get("by_endpoint")
    if not isinstance(rows, list):
        rows = []

    def esc(s: Any) -> str:
        return (
            str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    # Avoid embedding potentially sensitive raw inputs.
    title = "AURITY Observability — Metrics Report"

    header = (
        "<tr>"
        "<th>Endpoint</th><th>Service</th><th>Count</th><th>Errors</th><th>Error rate</th>"
        "<th>p50 ms</th><th>p95 ms</th><th>p99 ms</th><th>SLO violations</th>"
        "</tr>"
    )

    body_parts: list[str] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        violations = r.get("slo_violations")
        v_txt = ", ".join(str(v) for v in violations) if isinstance(violations, list) else ""

        body_parts.append(
            "<tr>"
            f"<td>{esc(r.get('endpoint'))}</td>"
            f"<td>{esc(r.get('service'))}</td>"
            f"<td>{esc(r.get('count'))}</td>"
            f"<td>{esc(r.get('errors'))}</td>"
            f"<td>{esc(r.get('error_rate'))}</td>"
            f"<td>{esc(r.get('p50_ms'))}</td>"
            f"<td>{esc(r.get('p95_ms'))}</td>"
            f"<td>{esc(r.get('p99_ms'))}</td>"
            f"<td>{esc(v_txt)}</td>"
            "</tr>"
        )

    table = (
        f"<table border='1' cellpadding='6' cellspacing='0'>{header}{''.join(body_parts)}</table>"
    )

    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    summary_json = esc(
        __import__("json").dumps(redact_mapping(summary), sort_keys=True, ensure_ascii=False)
    )

    return (
        "<!doctype html>"
        "<html><head><meta charset='utf-8'>"
        f"<title>{esc(title)}</title>"
        "</head><body>"
        f"<h1>{esc(title)}</h1>"
        f"<pre>{summary_json}</pre>"
        f"{table}"
        "</body></html>"
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_cli_parser()
    ns = parser.parse_args(argv)
    return run(ns)


if __name__ == "__main__":
    raise SystemExit(main())
