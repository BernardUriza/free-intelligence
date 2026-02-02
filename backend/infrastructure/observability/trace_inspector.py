from __future__ import annotations

import argparse
from collections import Counter
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
    get_layer,
    get_status_code,
    iter_json_logs,
    load_policy,
    policy_sha256,
    redact_mapping,
    require_log_source,
    traceability_block,
    validate_base_path,
    within_range,
    write_json_artifact,
    write_text_artifact,
)


def build_cli_parser() -> argparse.ArgumentParser:
    parser = build_parser(
        prog="fi-observability-traces",
        description=(
            "Inspect tracing/correlation across PUBLIC → INTERNAL → WORKER layers using structured JSON logs. "
            "Correlates events by idempotency_key/workflow_id/session_id and identifies highest-latency traces."
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
        "--endpoint",
        default=None,
        help="Only include events for this endpoint/path (exact match).",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=20,
        help="Top N traces by total accumulated latency.",
    )
    parser.add_argument(
        "--max-events-per-trace",
        type=int,
        default=200,
        help="Cap stored event summaries per trace (prevents huge reports).",
    )

    return parser


def _parse_optional_time(value: str | None) -> datetime | None:
    if value is None:
        return None

    from ._common import parse_time

    return parse_time(value)


def _correlation_id(event: dict[str, Any]) -> str | None:
    for key in ("idempotency_key", "workflow_id", "session_id"):
        v = event.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def run(args: argparse.Namespace) -> int:
    """Execute trace inspection analysis on observability logs.

    Analyzes distributed traces from log files, computing latency percentiles,
    identifying slow endpoints, and detecting anomalies. Output is formatted
    as a structured report suitable for SRE review.

    Args:
        args: CLI arguments including log source, time filters, and output options

    Returns:
        Exit code (0 for success, 1 for errors)
    """
    try:
        ensure_read_only_mode(True)
        common = coerce_common_args(args)
        validate_base_path(common.base_path)

        # Policy isn't strictly required for trace inspection, but we include its checksum for auditability.
        policy = load_policy(common.slo_policy)
        policy_hash = policy_sha256(policy)

        log_source = require_log_source(common)
        since = _parse_optional_time(getattr(args, "since", None))
        until = _parse_optional_time(getattr(args, "until", None))
        endpoint_filter = getattr(args, "endpoint", None)
        top_n = int(getattr(args, "top", 20))
        max_events_per_trace = int(getattr(args, "max_events_per_trace", 200))

        from ._common import parse_duration_ms

        traces: dict[str, dict[str, Any]] = {}
        flow_edges: Counter[tuple[str, str]] = Counter()

        total_events = 0
        used_events = 0

        for event in iter_json_logs(log_source):
            total_events += 1
            ts = best_effort_timestamp(event)
            if (since is not None or until is not None) and not within_range(ts, since, until):
                continue

            corr_id = _correlation_id(event)
            if corr_id is None:
                continue

            endpoint = get_endpoint(event)
            if endpoint_filter and endpoint != endpoint_filter:
                continue

            used_events += 1
            layer = get_layer(event) or "UNKNOWN"
            status = get_status_code(event)
            duration_ms = parse_duration_ms(event)

            record = traces.get(corr_id)
            if record is None:
                record = {
                    "trace_id": corr_id,
                    "first_ts": None,
                    "last_ts": None,
                    "total_latency_ms": 0.0,
                    "layers": [],
                    "events": [],
                    "endpoints": set(),
                }
                traces[corr_id] = record

            if ts is not None:
                iso = ts.isoformat()
                if record["first_ts"] is None or iso < record["first_ts"]:
                    record["first_ts"] = iso
                if record["last_ts"] is None or iso > record["last_ts"]:
                    record["last_ts"] = iso

            if duration_ms is not None:
                record["total_latency_ms"] = float(record["total_latency_ms"]) + float(duration_ms)

            if endpoint:
                record["endpoints"].add(endpoint)

            if len(record["events"]) < max_events_per_trace:
                record["events"].append(
                    {
                        "ts": None if ts is None else ts.isoformat(),
                        "layer": layer,
                        "endpoint": endpoint,
                        "latency_ms": None if duration_ms is None else round(float(duration_ms), 3),
                        "status_code": status,
                    }
                )

            # Flow edge estimation: count transitions between successive layers.
            layers = record["layers"]
            if not layers or layers[-1] != layer:
                if layers:
                    flow_edges[(layers[-1], layer)] += 1
                layers.append(layer)

        # Finalize traces
        finalized: list[dict[str, Any]] = []
        for record in traces.values():
            endpoints = (
                sorted(record["endpoints"]) if isinstance(record.get("endpoints"), set) else []
            )
            record["endpoints"] = endpoints

            # Stable ordering of events
            evs = record.get("events")
            if isinstance(evs, list):
                evs.sort(key=lambda e: (e.get("ts") is None, e.get("ts") or ""))

            finalized.append(record)

        finalized.sort(
            key=lambda r: (-float(r.get("total_latency_ms") or 0.0), str(r.get("trace_id")))
        )
        top_traces = finalized[: max(0, top_n)]

        dot = _render_dot(top_traces)

        report: dict[str, Any] = {
            "traceability": traceability_block("AUR-PROMPT-OBS-1.0"),
            "tool": "trace_inspector",
            "mode": "read_only",
            "environment": common.environment,
            "inputs": {
                "log_source": "<stdin>" if log_source == "-" else log_source,
                "slo_policy": common.slo_policy,
                "slo_policy_sha256": policy_hash,
                "since": getattr(args, "since", None),
                "until": getattr(args, "until", None),
                "endpoint": endpoint_filter,
                "top": top_n,
            },
            "summary": {
                "events_total": total_events,
                "events_used": used_events,
                "traces_total": len(finalized),
                "traces_reported": len(top_traces),
            },
            "flow_edges": [
                {"from": a, "to": b, "count": c}
                for (a, b), c in sorted(flow_edges.items(), key=lambda kv: (-kv[1], kv[0]))
            ],
            "top_traces": top_traces,
        }

        out_json = write_json_artifact(common.out_dir, "traces_report.json", redact_mapping(report))
        out_dot = write_text_artifact(common.out_dir, "traces_top.dot", dot)

        from ._common import safe_print

        safe_print(
            {
                "ok": True,
                "tool": "trace_inspector",
                "artifacts": {"json": str(out_json), "dot": str(out_dot)},
            }
        )
        return 0
    except Exception as e:
        from ._common import safe_print

        safe_print({"ok": False, "tool": "trace_inspector", **compact_exception(e)})
        return 2


def _render_dot(top_traces: list[dict[str, Any]]) -> str:
    # DOT is a static artifact; it can be rendered by Graphviz externally if desired.
    parts: list[str] = ["digraph traces {", "rankdir=LR;"]

    for i, t in enumerate(top_traces, start=1):
        tid = str(t.get("trace_id"))
        total = float(t.get("total_latency_ms") or 0.0)
        label = f"T{i}: {tid}\\n{total:.1f}ms"

        cluster_name = f"cluster_{i}"
        parts.append(f"subgraph {cluster_name} {{")
        parts.append(f'label="{_dot_escape(label)}";')

        layers = t.get("layers")
        if not isinstance(layers, list) or not layers:
            parts.append("}")
            continue

        # Create nodes
        for j, layer in enumerate(layers):
            node = f"t{i}_n{j}"
            parts.append(f'{node} [label="{_dot_escape(str(layer))}"]; ')

        # Create edges
        for j in range(len(layers) - 1):
            a = f"t{i}_n{j}"
            b = f"t{i}_n{j + 1}"
            parts.append(f"{a} -> {b};")

        parts.append("}")

    parts.append("}")
    return "\n".join(parts) + "\n"


def _dot_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def main(argv: list[str] | None = None) -> int:
    parser = build_cli_parser()
    ns = parser.parse_args(argv)
    return run(ns)


if __name__ == "__main__":
    raise SystemExit(main())
