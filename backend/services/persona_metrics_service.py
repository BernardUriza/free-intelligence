"""
Persona Metrics Service - Track AI Persona Usage

Computes usage statistics per persona by querying audit logs.

Metrics tracked:
- Total invocations (count of LLM calls per persona)
- Average latency (milliseconds)
- Average cost (USD per invocation)
- Last used timestamp

Architecture:
- Queries HDF5 audit_logs group
- Filters by action='llm_call' and parses persona from details
- Computes aggregate statistics

Author: Bernard Uriza Orozco
Created: 2025-11-20
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import h5py

from backend.logger import get_logger

logger = get_logger(__name__)

# HDF5 corpus path
CORPUS_PATH = Path(__file__).parent.parent.parent / "storage" / "corpus.h5"


class PersonaMetricsService:
    """Service for computing persona usage metrics from audit logs."""

    def __init__(self, corpus_path: Path = CORPUS_PATH):
        """Initialize metrics service.

        Args:
            corpus_path: Path to HDF5 corpus file
        """
        self.corpus_path = corpus_path

    def get_persona_stats(self, persona_id: str) -> dict[str, Any]:
        """Get usage statistics for a specific persona.

        Args:
            persona_id: Persona identifier (e.g., 'general_assistant')

        Returns:
            dict with:
                - total_invocations: int
                - avg_latency_ms: float
                - avg_cost_usd: float
                - last_used: str (ISO timestamp) or None
        """
        try:
            stats = {
                "total_invocations": 0,
                "avg_latency_ms": 0.0,
                "avg_cost_usd": 0.0,
                "last_used": None,
            }

            if not self.corpus_path.exists():
                logger.warning("CORPUS_NOT_FOUND", path=str(self.corpus_path))
                return stats

            with h5py.File(self.corpus_path, "r") as f:
                # Check if audit_logs group exists
                if "audit_logs" not in f:
                    logger.info("NO_AUDIT_LOGS", persona=persona_id)
                    return stats

                audit_logs_group = f["audit_logs"]

                # Collect metrics from matching logs
                latencies = []
                costs = []
                timestamps = []

                for log_id in audit_logs_group.keys():
                    log_group = audit_logs_group[log_id]

                    # Check if this is an LLM call
                    action = log_group.attrs.get("action", "")
                    if action != "llm_call":
                        continue

                    # Parse details JSON
                    details_json = log_group.attrs.get("details", "{}")
                    try:
                        details = json.loads(details_json)
                    except json.JSONDecodeError:
                        continue

                    # Check if persona matches
                    log_persona = details.get("persona", "")
                    if log_persona != persona_id:
                        continue

                    # Collect metrics
                    stats["total_invocations"] += 1

                    if "latency_ms" in details:
                        latencies.append(float(details["latency_ms"]))

                    if "cost_usd" in details:
                        costs.append(float(details["cost_usd"]))

                    # Track timestamp
                    timestamp = log_group.attrs.get("timestamp")
                    if timestamp:
                        timestamps.append(timestamp)

                # Compute averages
                if latencies:
                    stats["avg_latency_ms"] = sum(latencies) / len(latencies)

                if costs:
                    stats["avg_cost_usd"] = sum(costs) / len(costs)

                if timestamps:
                    # Most recent timestamp
                    stats["last_used"] = max(timestamps)

            logger.info(
                "PERSONA_STATS_COMPUTED",
                persona=persona_id,
                invocations=stats["total_invocations"],
            )

            return stats

        except Exception as e:
            logger.error("PERSONA_STATS_FAILED", persona=persona_id, error=str(e))
            return {
                "total_invocations": 0,
                "avg_latency_ms": 0.0,
                "avg_cost_usd": 0.0,
                "last_used": None,
            }

    def get_all_persona_stats(self) -> dict[str, dict[str, Any]]:
        """Get usage statistics for all personas.

        Returns:
            dict mapping persona_id -> stats dict
        """
        try:
            all_stats: dict[str, dict[str, Any]] = defaultdict(
                lambda: {
                    "total_invocations": 0,
                    "avg_latency_ms": 0.0,
                    "avg_cost_usd": 0.0,
                    "last_used": None,
                }
            )

            if not self.corpus_path.exists():
                logger.warning("CORPUS_NOT_FOUND", path=str(self.corpus_path))
                return dict(all_stats)

            with h5py.File(self.corpus_path, "r") as f:
                # Check if audit_logs group exists
                if "audit_logs" not in f:
                    logger.info("NO_AUDIT_LOGS")
                    return dict(all_stats)

                audit_logs_group = f["audit_logs"]

                # Temporary storage for raw metrics
                persona_latencies: dict[str, list[float]] = defaultdict(list)
                persona_costs: dict[str, list[float]] = defaultdict(list)
                persona_timestamps: dict[str, list[str]] = defaultdict(list)

                for log_id in audit_logs_group.keys():
                    log_group = audit_logs_group[log_id]

                    # Check if this is an LLM call
                    action = log_group.attrs.get("action", "")
                    if action != "llm_call":
                        continue

                    # Parse details JSON
                    details_json = log_group.attrs.get("details", "{}")
                    try:
                        details = json.loads(details_json)
                    except json.JSONDecodeError:
                        continue

                    # Get persona
                    persona = details.get("persona", "unknown")

                    # Increment invocation count
                    all_stats[persona]["total_invocations"] += 1

                    # Collect metrics
                    if "latency_ms" in details:
                        persona_latencies[persona].append(float(details["latency_ms"]))

                    if "cost_usd" in details:
                        persona_costs[persona].append(float(details["cost_usd"]))

                    # Track timestamp
                    timestamp = log_group.attrs.get("timestamp")
                    if timestamp:
                        persona_timestamps[persona].append(timestamp)

                # Compute averages for each persona
                for persona in all_stats.keys():
                    if persona in persona_latencies:
                        latencies = persona_latencies[persona]
                        all_stats[persona]["avg_latency_ms"] = sum(latencies) / len(latencies)

                    if persona in persona_costs:
                        costs = persona_costs[persona]
                        all_stats[persona]["avg_cost_usd"] = sum(costs) / len(costs)

                    if persona in persona_timestamps:
                        timestamps = persona_timestamps[persona]
                        all_stats[persona]["last_used"] = max(timestamps)

            logger.info(
                "ALL_PERSONA_STATS_COMPUTED",
                total_personas=len(all_stats),
            )

            return dict(all_stats)

        except Exception as e:
            logger.error("ALL_PERSONA_STATS_FAILED", error=str(e))
            return {}


# Singleton instance
_metrics_service: PersonaMetricsService | None = None


def get_persona_metrics_service() -> PersonaMetricsService:
    """Get singleton persona metrics service instance."""
    global _metrics_service
    if _metrics_service is None:
        _metrics_service = PersonaMetricsService()
    return _metrics_service
