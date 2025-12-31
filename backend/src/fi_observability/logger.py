# fi_observability/logger.py
# LLM Logger - Logs all LLM calls to SQLite

import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from fi_observability.database import ensure_initialized, get_connection
from fi_observability.models import CallStats, CallStatus, ClientReport, LLMCall, LLMCallCreate
from ulid import ULID

logger = logging.getLogger(__name__)

# Singleton instance
_logger_instance: Optional["LLMLogger"] = None


def get_llm_logger() -> "LLMLogger":
    """Get the singleton LLMLogger instance."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = LLMLogger()
    return _logger_instance


class LLMLogger:
    """Logs LLM calls to SQLite for observability."""

    def __init__(self):
        ensure_initialized()
        logger.info("LLMLogger initialized")

    def log_call(self, call: LLMCallCreate) -> str:
        """Log an LLM call. Returns the call ID."""
        call_id = str(ULID())
        timestamp = datetime.utcnow()

        data = call.to_dict()
        data["id"] = call_id
        data["timestamp"] = timestamp.isoformat()

        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO llm_calls (
                    id, timestamp, model, provider,
                    prompt_tokens, completion_tokens, latency_ms,
                    status, error_message,
                    prompt_preview, response_preview,
                    client_id, session_id, persona,
                    prompt_hash, response_hash, metadata
                ) VALUES (
                    :id, :timestamp, :model, :provider,
                    :prompt_tokens, :completion_tokens, :latency_ms,
                    :status, :error_message,
                    :prompt_preview, :response_preview,
                    :client_id, :session_id, :persona,
                    :prompt_hash, :response_hash, :metadata
                )
                """,
                data
            )
            conn.commit()

        logger.debug(f"Logged LLM call {call_id}: {call.model} ({call.latency_ms}ms)")
        return call_id

    def get_call(self, call_id: str) -> Optional[LLMCall]:
        """Get a specific call by ID."""
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM llm_calls WHERE id = ?",
                (call_id,)
            ).fetchone()

        if row:
            return LLMCall.from_row(dict(row))
        return None

    def get_recent_calls(
        self,
        limit: int = 5,
        client_id: Optional[str] = None,
        model: Optional[str] = None,
        status: Optional[CallStatus] = None,
    ) -> list[LLMCall]:
        """Get most recent calls with optional filters."""
        query = "SELECT * FROM llm_calls WHERE 1=1"
        params = []

        if client_id:
            query += " AND client_id = ?"
            params.append(client_id)

        if model:
            query += " AND model = ?"
            params.append(model)

        if status:
            query += " AND status = ?"
            params.append(status.value)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with get_connection() as conn:
            rows = conn.execute(query, params).fetchall()

        return [LLMCall.from_row(dict(row)) for row in rows]

    def get_stats(
        self,
        hours: int = 24,
        client_id: Optional[str] = None,
    ) -> CallStats:
        """Get aggregated statistics for the last N hours."""
        since = datetime.utcnow() - timedelta(hours=hours)

        base_filter = "timestamp >= ?"
        params: list = [since.isoformat()]

        if client_id:
            base_filter += " AND client_id = ?"
            params.append(client_id)

        with get_connection() as conn:
            # Basic stats
            row = conn.execute(
                f"""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success,
                    SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as errors,
                    SUM(prompt_tokens) as prompt_tokens,
                    SUM(completion_tokens) as completion_tokens,
                    AVG(latency_ms) as avg_latency
                FROM llm_calls
                WHERE {base_filter}
                """,
                params
            ).fetchone()

            stats = CallStats(
                total_calls=row["total"] or 0,
                success_calls=row["success"] or 0,
                error_calls=row["errors"] or 0,
                total_prompt_tokens=row["prompt_tokens"] or 0,
                total_completion_tokens=row["completion_tokens"] or 0,
                avg_latency_ms=row["avg_latency"] or 0.0,
            )

            # Percentile latencies
            latencies = conn.execute(
                f"""
                SELECT latency_ms FROM llm_calls
                WHERE {base_filter} AND status = 'success'
                ORDER BY latency_ms
                """,
                params
            ).fetchall()

            if latencies:
                latency_list = [r["latency_ms"] for r in latencies]
                n = len(latency_list)
                stats.p50_latency_ms = latency_list[int(n * 0.5)] if n > 0 else 0
                stats.p95_latency_ms = latency_list[int(n * 0.95)] if n > 0 else 0

            # By model
            model_rows = conn.execute(
                f"""
                SELECT model, COUNT(*) as count, SUM(prompt_tokens + completion_tokens) as tokens
                FROM llm_calls
                WHERE {base_filter}
                GROUP BY model
                ORDER BY count DESC
                """,
                params
            ).fetchall()

            stats.calls_by_model = {
                r["model"]: {"count": r["count"], "tokens": r["tokens"] or 0}
                for r in model_rows
            }

            # By client (only if not filtering by client)
            if not client_id:
                client_rows = conn.execute(
                    f"""
                    SELECT client_id, COUNT(*) as count
                    FROM llm_calls
                    WHERE {base_filter} AND client_id IS NOT NULL
                    GROUP BY client_id
                    ORDER BY count DESC
                    LIMIT 10
                    """,
                    params
                ).fetchall()

                stats.calls_by_client = {
                    r["client_id"]: r["count"]
                    for r in client_rows
                }

        return stats

    def get_client_report(
        self,
        client_id: str,
        days: int = 30,
    ) -> ClientReport:
        """Generate a detailed report for a specific client."""
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=days)

        report = ClientReport(
            client_id=client_id,
            period_start=period_start,
            period_end=period_end,
        )

        with get_connection() as conn:
            # Basic stats
            row = conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(prompt_tokens) as prompt_tokens,
                    SUM(completion_tokens) as completion_tokens,
                    AVG(latency_ms) as avg_latency,
                    SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as error_rate
                FROM llm_calls
                WHERE client_id = ? AND timestamp >= ?
                """,
                (client_id, period_start.isoformat())
            ).fetchone()

            report.total_calls = row["total"] or 0
            report.total_prompt_tokens = row["prompt_tokens"] or 0
            report.total_completion_tokens = row["completion_tokens"] or 0
            report.total_tokens = report.total_prompt_tokens + report.total_completion_tokens
            report.avg_latency_ms = row["avg_latency"] or 0.0
            report.error_rate = row["error_rate"] or 0.0

            # By model
            model_rows = conn.execute(
                """
                SELECT model, COUNT(*) as count, SUM(prompt_tokens + completion_tokens) as tokens
                FROM llm_calls
                WHERE client_id = ? AND timestamp >= ?
                GROUP BY model
                """,
                (client_id, period_start.isoformat())
            ).fetchall()

            report.calls_by_model = {
                r["model"]: {"count": r["count"], "tokens": r["tokens"] or 0}
                for r in model_rows
            }

            # By persona
            persona_rows = conn.execute(
                """
                SELECT persona, COUNT(*) as count
                FROM llm_calls
                WHERE client_id = ? AND timestamp >= ? AND persona IS NOT NULL
                GROUP BY persona
                """,
                (client_id, period_start.isoformat())
            ).fetchall()

            report.calls_by_persona = {
                r["persona"]: r["count"]
                for r in persona_rows
            }

            # Recent calls
            recent = conn.execute(
                """
                SELECT * FROM llm_calls
                WHERE client_id = ?
                ORDER BY timestamp DESC
                LIMIT 10
                """,
                (client_id,)
            ).fetchall()

            report.recent_calls = [LLMCall.from_row(dict(r)) for r in recent]

            # Cost estimation (rough, configurable)
            # Assuming ~$0.001 per 1K tokens for local Ollama (electricity cost)
            # Or use actual API costs for cloud models
            cost_per_1k_tokens = {
                "qwen3:1.7b": 0.0001,  # Local, minimal cost
                "qwen3:8b": 0.0002,
                "llama3.1:8b": 0.0002,
                "gpt-4": 0.03,  # If using Azure
                "claude-3-opus": 0.015,
            }

            total_cost = 0.0
            for model, data in report.calls_by_model.items():
                rate = cost_per_1k_tokens.get(model, 0.001)  # Default
                total_cost += (data["tokens"] / 1000) * rate

            report.estimated_cost_usd = round(total_cost, 4)

        return report

    def search_calls(
        self,
        query: str,
        limit: int = 20,
    ) -> list[LLMCall]:
        """Search calls by prompt/response preview content."""
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM llm_calls
                WHERE prompt_preview LIKE ? OR response_preview LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (f"%{query}%", f"%{query}%", limit)
            ).fetchall()

        return [LLMCall.from_row(dict(row)) for row in rows]
