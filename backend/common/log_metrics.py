#!/usr/bin/env python3
from __future__ import annotations

"""
Free Intelligence - Log Metrics Export

Exporta métricas de logs para observabilidad:
- llm_requests_total
- llm_latency_p95
- api_requests_total
- api_errors_total
- ingest_segments_total
- audit_events_total

Formato: Prometheus-compatible (simple text format)

FI-CORE-FEAT-003
"""

import json
from datetime import datetime, timedelta
from typing import Any

from log_rotation import LogRotation
from logger_structured import ServiceChannel


class LogMetrics:
    """
    Extrae métricas de logs para observabilidad.

    Métricas implementadas:
    - llm_requests_total
    - llm_latency_p95
    - llm_tokens_total
    - llm_cost_total
    - api_requests_total
    - api_errors_total
    - storage_segments_total
    - audit_events_total
    """

    def __init__(self, base_path: str = "data/logs"):
        """
        Initialize metrics extractor.

        Args:
            base_path: Base path para logs
        """
        self.rotation = LogRotation(base_path=base_path)

    def _read_recent_logs(self, channel: ServiceChannel, hours: int = 24) -> list[dict[str, Any]]:
        """
        Read recent log events from channel.

        Args:
            channel: Service channel
            hours: How many hours back to read

        Returns:
            List of log events
        """
        cutoff_time = datetime.now(UTC) - timedelta(hours=hours)

        # Get current log file
        log_path = self.rotation.get_current_log_path(channel)
        events = []

        if log_path.exists():
            file_events = self.rotation.read_log_file(log_path)

            # Filter by timestamp
            for event in file_events:
                try:
                    event_time = datetime.fromisoformat(event["ts"])
                    if event_time >= cutoff_time:
                        events.append(event)
                except (KeyError, ValueError):
                    continue

        return events

    def compute_percentile(self, values: list[float], percentile: int) -> float:
        """
        Compute percentile of values.

        Args:
            values: List of numeric values
            percentile: Percentile to compute (0-100)

        Returns:
            Percentile value
        """
        if not values:
            return 0.0

        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)

        if index >= len(sorted_values):
            index = len(sorted_values) - 1

        return sorted_values[index]

    def get_llm_metrics(self, hours: int = 24) -> dict[str, Any]:
        """
        Get LLM metrics for last N hours.

        Returns:
            Dict with llm_requests_total, llm_latency_p95, llm_tokens_total, llm_cost_total
        """
        events = self._read_recent_logs(ServiceChannel.LLM, hours=hours)

        if not events:
            return {
                "llm_requests_total": 0,
                "llm_latency_p95": 0.0,
                "llm_tokens_total": 0,
                "llm_cost_total": 0.0,
                "llm_timeout_total": 0,
            }

        latencies = [e["latency_ms"] for e in events if e.get("latency_ms")]
        tokens = sum(
            e["details"].get("tokens_in", 0) + e["details"].get("tokens_out", 0) for e in events
        )
        cost = sum(e["details"].get("cost_est", 0.0) for e in events)
        timeouts = sum(1 for e in events if e["details"].get("timeout", False))

        return {
            "llm_requests_total": len(events),
            "llm_latency_p95": round(self.compute_percentile(latencies, 95), 2),
            "llm_tokens_total": tokens,
            "llm_cost_total": round(cost, 4),
            "llm_timeout_total": timeouts,
        }

    def get_api_metrics(self, hours: int = 24) -> dict[str, Any]:
        """
        Get API metrics for last N hours.

        Returns:
            Dict with api_requests_total, api_errors_total, api_latency_p95
        """
        events = self._read_recent_logs(ServiceChannel.SERVER, hours=hours)

        if not events:
            return {"api_requests_total": 0, "api_errors_total": 0, "api_latency_p95": 0.0}

        errors = sum(1 for e in events if not e.get("ok", True))
        latencies = [e["latency_ms"] for e in events if e.get("latency_ms")]

        return {
            "api_requests_total": len(events),
            "api_errors_total": errors,
            "api_latency_p95": round(self.compute_percentile(latencies, 95), 2),
        }

    def get_storage_metrics(self, hours: int = 24) -> dict[str, Any]:
        """
        Get storage metrics for last N hours.

        Returns:
            Dict with storage_segments_total, storage_ready_total
        """
        events = self._read_recent_logs(ServiceChannel.STORAGE, hours=hours)

        if not events:
            return {"storage_segments_total": 0, "storage_ready_total": 0}

        ready = sum(1 for e in events if e["details"].get("ready", False))

        return {"storage_segments_total": len(events), "storage_ready_total": ready}

    def get_audit_metrics(self, hours: int = 24) -> dict[str, Any]:
        """
        Get audit metrics for last N hours.

        Returns:
            Dict with audit_events_total, audit_failures_total
        """
        events = self._read_recent_logs(ServiceChannel.ACCESS, hours=hours)

        if not events:
            return {
                "audit_events_total": 0,
                "audit_failures_total": 0,
                "audit_logins_total": 0,
                "audit_role_changes_total": 0,
            }

        failures = sum(1 for e in events if not e.get("ok", True))
        logins = sum(1 for e in events if e["action"] == "access.login")
        role_changes = sum(1 for e in events if e["action"] == "access.role_change")

        return {
            "audit_events_total": len(events),
            "audit_failures_total": failures,
            "audit_logins_total": logins,
            "audit_role_changes_total": role_changes,
        }

    def get_all_metrics(self, hours: int = 24) -> dict[str, Any]:
        """
        Get all metrics for last N hours.

        Args:
            hours: Hours back to analyze

        Returns:
            Combined metrics dict
        """
        metrics = {"timestamp": datetime.now(UTC).isoformat(), "hours": hours}

        metrics.update(self.get_llm_metrics(hours))
        metrics.update(self.get_api_metrics(hours))
        metrics.update(self.get_storage_metrics(hours))
        metrics.update(self.get_audit_metrics(hours))

        return metrics

    def export_prometheus_format(self, hours: int = 24) -> str:
        """
        Export metrics in Prometheus text format.

        Args:
            hours: Hours back to analyze

        Returns:
            Prometheus-formatted metrics string
        """
        metrics = self.get_all_metrics(hours)

        lines = [
            "# HELP llm_requests_total Total LLM requests",
            "# TYPE llm_requests_total counter",
            f"llm_requests_total {metrics['llm_requests_total']}",
            "",
            "# HELP llm_latency_p95 95th percentile LLM latency (ms)",
            "# TYPE llm_latency_p95 gauge",
            f"llm_latency_p95 {metrics['llm_latency_p95']}",
            "",
            "# HELP llm_tokens_total Total tokens processed",
            "# TYPE llm_tokens_total counter",
            f"llm_tokens_total {metrics['llm_tokens_total']}",
            "",
            "# HELP llm_cost_total Total cost (USD)",
            "# TYPE llm_cost_total counter",
            f"llm_cost_total {metrics['llm_cost_total']}",
            "",
            "# HELP api_requests_total Total API requests",
            "# TYPE api_requests_total counter",
            f"api_requests_total {metrics['api_requests_total']}",
            "",
            "# HELP api_errors_total Total API errors",
            "# TYPE api_errors_total counter",
            f"api_errors_total {metrics['api_errors_total']}",
            "",
            "# HELP api_latency_p95 95th percentile API latency (ms)",
            "# TYPE api_latency_p95 gauge",
            f"api_latency_p95 {metrics['api_latency_p95']}",
            "",
            "# HELP storage_segments_total Total storage segments",
            "# TYPE storage_segments_total counter",
            f"storage_segments_total {metrics['storage_segments_total']}",
            "",
            "# HELP audit_events_total Total audit events",
            "# TYPE audit_events_total counter",
            f"audit_events_total {metrics['audit_events_total']}",
            "",
        ]

        return "\n".join(lines)


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import sys

    print("📊 FREE INTELLIGENCE - LOG METRICS")
    print("=" * 60)
    print()

    metrics_mgr = LogMetrics(base_path="data/logs")

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "json":
            # Export as JSON
            hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
            metrics = metrics_mgr.get_all_metrics(hours)
            print(json.dumps(metrics, indent=2))

        elif command == "prometheus":
            # Export in Prometheus format
            hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
            prom_text = metrics_mgr.export_prometheus_format(hours)
            print(prom_text)

        elif command == "dashboard":
            # Simple dashboard
            hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
            metrics = metrics_mgr.get_all_metrics(hours)

            print(f"📊 METRICS DASHBOARD (Last {hours}h)")
            print()

            print("LLM:")
            print(f"   Requests: {metrics['llm_requests_total']}")
            print(f"   Latency p95: {metrics['llm_latency_p95']} ms")
            print(f"   Tokens: {metrics['llm_tokens_total']:,}")
            print(f"   Cost: ${metrics['llm_cost_total']}")
            print(f"   Timeouts: {metrics['llm_timeout_total']}")
            print()

            print("API:")
            print(f"   Requests: {metrics['api_requests_total']}")
            print(f"   Errors: {metrics['api_errors_total']}")
            print(f"   Latency p95: {metrics['api_latency_p95']} ms")
            print()

            print("STORAGE:")
            print(f"   Segments: {metrics['storage_segments_total']}")
            print(f"   Ready: {metrics['storage_ready_total']}")
            print()

            print("AUDIT:")
            print(f"   Events: {metrics['audit_events_total']}")
            print(f"   Failures: {metrics['audit_failures_total']}")
            print(f"   Logins: {metrics['audit_logins_total']}")
            print(f"   Role changes: {metrics['audit_role_changes_total']}")

        else:
            print(f"Unknown command: {command}")
            print()
            print("Available commands:")
            print("   json [hours]        - Export as JSON")
            print("   prometheus [hours]  - Export in Prometheus format")
            print("   dashboard [hours]   - Simple dashboard")

    else:
        print("Usage: python3 backend/log_metrics.py [command] [hours]")
        print()
        print("Commands:")
        print("   json [hours]        - Export metrics as JSON (default: 24h)")
        print("   prometheus [hours]  - Export in Prometheus text format")
        print("   dashboard [hours]   - Display simple dashboard")
        print()
        print("Examples:")
        print("   python3 backend/log_metrics.py json 24")
        print("   python3 backend/log_metrics.py prometheus")
        print("   python3 backend/log_metrics.py dashboard 1")
