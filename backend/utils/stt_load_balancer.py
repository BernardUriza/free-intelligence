"""STT Load Balancer - Policy-Driven Selection with Adaptive Performance Tracking.

SOLID Principles Applied:
  - Single Responsibility: Selects STT provider based on policy and performance
  - Open/Closed: Extensible via policy.yaml without code changes
  - Dependency Inversion: Depends on policy.yaml abstraction, not hardcoded values

Architecture:
  - Policy-driven: File size, duration thresholds from policy.yaml
  - Adaptive tracking: Rolling window of performance metrics (5 chunks)
  - Fallback management: Policy-based fallback on empty transcripts
  - Thread-safe: All state changes protected by locks

Selection Strategy:
  1. Forced provider (if specified) → highest priority
  2. File size threshold (>5MB → Azure) → policy-driven
  3. Duration threshold (>300s → Azure) → policy-driven
  4. Adaptive selection (based on performance) → data-driven
  5. Primary provider → policy default

Performance Tracking:
  - Rolling window: Last 5 chunks per provider
  - Metrics: resolution_time, retry_attempts, failure_rate
  - Auto-switch: If provider >10s or >2 retries consistently

Created: 2025-11-17
Updated: 2025-11-17 (SOLID refactor - merged policy + adaptive)
Author: Claude Code
"""

from __future__ import annotations

import threading
from collections import defaultdict, deque
from pathlib import Path
from typing import Optional

import yaml

from backend.logger import get_logger

logger = get_logger(__name__)

# Performance thresholds for adaptive switching
SLOW_THRESHOLD_SECONDS = 10.0  # Switch if resolution_time > 10s consistently
RETRY_THRESHOLD = 2  # Switch if >2 retries in last 5 chunks
WINDOW_SIZE = 5  # Rolling window size for performance stats


class STTLoadBalancer:
    """Policy-driven STT load balancer with adaptive performance tracking."""

    def __init__(self):
        """Initialize with policy configuration and performance tracking."""
        self.lock = threading.Lock()
        self.policy = self._load_policy()

        # Adaptive performance tracking (rolling window per provider)
        self.performance_stats: dict[str, dict] = defaultdict(
            lambda: {
                "resolution_times": deque(maxlen=WINDOW_SIZE),
                "retry_attempts": deque(maxlen=WINDOW_SIZE),
                "total_chunks": 0,
                "failed_chunks": 0,
            }
        )

        # Session-specific provider preference (adapts per session)
        self.session_provider: dict[str, str] = {}

    def _load_policy(self) -> dict:
        """Load policy.yaml configuration (Dependency Inversion principle).

        Returns:
            Policy configuration dict, or empty dict if file not found
        """
        policy_path = Path("policy.yaml")
        if not policy_path.exists():
            logger.warning("NO_POLICY_FILE", message="policy.yaml not found, using defaults")
            return {}

        with open(policy_path) as f:
            policy = yaml.safe_load(f)

        stt_config = policy.get("stt", {})
        logger.info(
            "POLICY_LOADED",
            primary_provider=stt_config.get("primary_provider"),
            large_file_threshold_mb=stt_config.get("routing_rules", {}).get(
                "large_file_threshold_mb"
            ),
            large_file_provider=stt_config.get("routing_rules", {}).get("large_file_provider"),
        )
        return policy

    def select_provider_for_file(
        self,
        audio_size_bytes: Optional[int] = None,
        duration_seconds: Optional[float] = None,
        chunk_number: Optional[int] = None,
        session_id: Optional[str] = None,
        force_provider: Optional[str] = None,
    ) -> tuple[str, str]:
        """Select STT provider based on file characteristics and policy.

        Selection priority (Open/Closed principle - extensible via policy):
          1. Forced provider (explicit override)
          2. File size threshold (policy-driven)
          3. Duration threshold (policy-driven)
          4. Adaptive selection (performance-driven)
          5. Primary provider (policy default)

        Args:
            audio_size_bytes: Size of audio file in bytes
            duration_seconds: Duration of audio in seconds
            chunk_number: Chunk index (for adaptive selection)
            session_id: Session ID (for adaptive selection)
            force_provider: Force specific provider (overrides policy)

        Returns:
            Tuple of (provider_name, decision_reason)
        """
        # 1. Check if provider is forced (highest priority)
        if force_provider:
            logger.info("PROVIDER_FORCED", provider=force_provider, reason="Explicitly requested")
            return force_provider, "forced_by_request"

        stt_config = self.policy.get("stt", {})
        routing_rules = stt_config.get("routing_rules", {})

        # 2. Check file size threshold (policy-driven routing)
        if audio_size_bytes:
            size_mb = audio_size_bytes / (1024 * 1024)
            threshold_mb = routing_rules.get("large_file_threshold_mb", 5.0)

            if size_mb > threshold_mb:
                provider = routing_rules.get("large_file_provider", "azure_whisper")
                reason = f"file_size_{size_mb:.1f}MB_exceeds_{threshold_mb}MB"

                logger.info(
                    "LARGE_FILE_ROUTING",
                    provider=provider,
                    file_size_mb=size_mb,
                    threshold_mb=threshold_mb,
                    decision="Using large file provider from policy",
                )
                return provider, reason

        # 3. Check duration threshold (policy-driven routing)
        if duration_seconds:
            threshold_seconds = routing_rules.get("long_duration_threshold_seconds", 300)

            if duration_seconds > threshold_seconds:
                provider = routing_rules.get("long_duration_provider", "azure_whisper")
                reason = f"duration_{duration_seconds}s_exceeds_{threshold_seconds}s"

                logger.info(
                    "LONG_DURATION_ROUTING",
                    provider=provider,
                    duration_seconds=duration_seconds,
                    threshold_seconds=threshold_seconds,
                    decision="Using long duration provider from policy",
                )
                return provider, reason

        # 4. Use adaptive selection if we have performance data
        if session_id or chunk_number is not None:
            adaptive_provider = self._select_adaptive_provider(session_id=session_id)
            if adaptive_provider:
                logger.info(
                    "ADAPTIVE_ROUTING",
                    provider=adaptive_provider,
                    session_id=session_id,
                    reason="Using adaptive selection based on performance",
                )
                return adaptive_provider, "adaptive_performance"

        # 5. Fallback to primary provider from policy
        primary = stt_config.get("primary_provider", "deepgram")

        logger.info(
            "STANDARD_ROUTING",
            provider=primary,
            reason="Using primary provider from policy",
            size_mb=audio_size_bytes / (1024 * 1024) if audio_size_bytes else None,
        )

        return primary, "primary_provider"

    def get_fallback_for_empty(self, failed_provider: str) -> Optional[str]:
        """Get fallback provider when transcript is empty (policy-driven).

        Args:
            failed_provider: Provider that returned empty transcript

        Returns:
            Fallback provider name or None
        """
        stt_config = self.policy.get("stt", {})
        providers_config = stt_config.get("providers", {})

        # Check provider-specific fallback in policy
        provider_config = providers_config.get(failed_provider, {})
        specific_fallback = provider_config.get("fallback_on_empty")

        if specific_fallback:
            logger.info(
                "EMPTY_TRANSCRIPT_FALLBACK",
                failed_provider=failed_provider,
                fallback_provider=specific_fallback,
                reason="Provider-specific fallback configured in policy",
            )
            return specific_fallback

        # Use general fallback list from policy
        fallback_providers = stt_config.get("fallback_providers", [])
        for fallback in fallback_providers:
            if fallback != failed_provider:
                logger.info(
                    "EMPTY_TRANSCRIPT_FALLBACK",
                    failed_provider=failed_provider,
                    fallback_provider=fallback,
                    reason="Using next provider in fallback list from policy",
                )
                return fallback

        logger.warning(
            "NO_FALLBACK_AVAILABLE",
            failed_provider=failed_provider,
            message="No fallback provider available for empty transcript",
        )
        return None

    def record_performance(
        self,
        provider: str,
        resolution_time: float,
        retry_attempts: int = 0,
        failed: bool = False,
    ) -> None:
        """Record performance metrics for adaptive tracking.

        Args:
            provider: Provider name
            resolution_time: Time to transcribe (seconds)
            retry_attempts: Number of retries/fallbacks
            failed: Whether the transcription failed
        """
        with self.lock:
            stats = self.performance_stats[provider]
            stats["resolution_times"].append(resolution_time)
            stats["retry_attempts"].append(retry_attempts)
            stats["total_chunks"] += 1
            if failed:
                stats["failed_chunks"] += 1

            # Calculate current averages
            avg_time = sum(stats["resolution_times"]) / len(stats["resolution_times"])
            avg_retries = sum(stats["retry_attempts"]) / len(stats["retry_attempts"])

            logger.info(
                "STT_PERFORMANCE_RECORDED",
                provider=provider,
                resolution_time=resolution_time,
                retry_attempts=retry_attempts,
                avg_time=round(avg_time, 2),
                avg_retries=round(avg_retries, 2),
                failed=failed,
            )

    def _select_adaptive_provider(self, session_id: Optional[str] = None) -> Optional[str]:
        """Select provider based on performance metrics (adaptive strategy).

        Strategy:
          1. If session has preferred provider, check if it's still performing well
          2. If not, select provider with best avg resolution_time
          3. Switch if current provider is slow (>10s) or has many retries

        Args:
            session_id: Optional session ID for session-specific preference

        Returns:
            Provider name or None if no performance data available
        """
        with self.lock:
            # Get providers with performance data
            providers_with_data = [
                p
                for p in self.performance_stats.keys()
                if len(self.performance_stats[p]["resolution_times"]) > 0
            ]

            if not providers_with_data:
                # No performance data yet - return None to use policy default
                return None

            # Calculate average performance for each provider
            provider_scores = {}
            for provider in providers_with_data:
                stats = self.performance_stats[provider]
                times = list(stats["resolution_times"])
                retries = list(stats["retry_attempts"])

                avg_time = sum(times) / len(times)
                avg_retries = sum(retries) / len(retries)
                failure_rate = (
                    stats["failed_chunks"] / stats["total_chunks"]
                    if stats["total_chunks"] > 0
                    else 0
                )

                # Score: lower is better (penalize slow time, retries, failures)
                score = avg_time + (avg_retries * 2) + (failure_rate * 10)
                provider_scores[provider] = score

            # Select provider with lowest score (best performance)
            best_provider = min(provider_scores, key=provider_scores.get)  # type: ignore[arg-type]

            # Check if session has a preferred provider
            if session_id and session_id in self.session_provider:
                preferred = self.session_provider[session_id]
                preferred_stats = self.performance_stats.get(preferred)

                # Check if preferred provider is still good
                if preferred_stats and len(preferred_stats["resolution_times"]) > 0:
                    recent_times = list(preferred_stats["resolution_times"])
                    recent_retries = list(preferred_stats["retry_attempts"])

                    avg_time = sum(recent_times) / len(recent_times)
                    avg_retries = sum(recent_retries) / len(recent_retries)

                    # Switch if preferred is underperforming
                    if avg_time > SLOW_THRESHOLD_SECONDS or avg_retries >= RETRY_THRESHOLD:
                        logger.warning(
                            "ADAPTIVE_PROVIDER_SWITCH",
                            session_id=session_id,
                            old_provider=preferred,
                            new_provider=best_provider,
                            reason=f"avg_time={avg_time:.1f}s, avg_retries={avg_retries:.1f}",
                        )
                        self.session_provider[session_id] = best_provider
                        return best_provider
                    else:
                        # Preferred provider is still good
                        return preferred

            # No preferred provider yet - use best one
            if session_id:
                self.session_provider[session_id] = best_provider

            return best_provider

    def get_stats(self) -> dict:
        """Get load balancer statistics with performance metrics.

        Returns:
            Dict with policy info, provider stats, and performance data
        """
        with self.lock:
            # Calculate average metrics per provider
            performance_summary = {}
            for provider, stats in self.performance_stats.items():
                times = list(stats["resolution_times"])
                retries = list(stats["retry_attempts"])

                if times:
                    performance_summary[provider] = {
                        "avg_resolution_time": round(sum(times) / len(times), 2),
                        "avg_retries": round(sum(retries) / len(retries), 2),
                        "total_chunks": stats["total_chunks"],
                        "failed_chunks": stats["failed_chunks"],
                        "failure_rate": round(
                            stats["failed_chunks"] / stats["total_chunks"]
                            if stats["total_chunks"] > 0
                            else 0,
                            2,
                        ),
                        "recent_times": list(times),  # Last 5
                        "recent_retries": list(retries),  # Last 5
                    }

            stt_config = self.policy.get("stt", {})
            return {
                "policy": {
                    "primary_provider": stt_config.get("primary_provider"),
                    "large_file_threshold_mb": stt_config.get("routing_rules", {}).get(
                        "large_file_threshold_mb"
                    ),
                    "fallback_providers": stt_config.get("fallback_providers", []),
                },
                "performance": performance_summary,
                "session_preferences": dict(self.session_provider),
            }


# Global singleton instance (thread-safe)
_load_balancer: Optional[STTLoadBalancer] = None
_balancer_lock = threading.Lock()


def get_stt_load_balancer() -> STTLoadBalancer:
    """Get or create global STT load balancer singleton.

    Returns:
        STTLoadBalancer instance
    """
    global _load_balancer

    if _load_balancer is None:
        with _balancer_lock:
            if _load_balancer is None:
                _load_balancer = STTLoadBalancer()

    return _load_balancer
