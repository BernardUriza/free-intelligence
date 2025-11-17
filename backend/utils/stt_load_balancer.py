"""STT Load Balancer - Intelligent provider selection with adaptive performance tracking.

Philosophy:
  - Distribute chunks across multiple STT providers to maximize throughput
  - Avoid rate limiting by alternating between Azure Whisper and Deepgram
  - Thread-safe round-robin selection with adaptive performance tracking
  - Automatic switching if provider is underperforming

Strategy (Adaptive):
  - Track resolution_time and retry_attempts per provider
  - Switch to faster provider if current one is slow (>10s) or failing
  - Use weighted selection: favor providers with lower avg resolution time
  - Fallback to round-robin if no performance data available

Performance Thresholds:
  - SLOW_THRESHOLD = 10s (switch to alternate if consistently >10s)
  - RETRY_THRESHOLD = 2 (switch if >2 retries in last 5 chunks)
  - WINDOW_SIZE = 5 chunks (rolling window for stats)

Created: 2025-11-15
Updated: 2025-11-16 (Adaptive Performance Tracking)
Author: Bernard Uriza Orozco
Card: STT Adaptive Load Balancing
"""

from __future__ import annotations

import os
import threading
from collections import defaultdict, deque
from typing import Optional

from backend.logger import get_logger

logger = get_logger(__name__)

# Performance thresholds for adaptive switching
SLOW_THRESHOLD_SECONDS = 10.0  # Switch if resolution_time > 10s consistently
RETRY_THRESHOLD = 2  # Switch if >2 retries in last 5 chunks
WINDOW_SIZE = 5  # Rolling window size for performance stats


class STTLoadBalancer:
    """Intelligent load balancer for STT providers."""

    def __init__(
        self,
        providers: Optional[list[str]] = None,
        strategy: str = "adaptive",
    ):
        """Initialize load balancer.

        Args:
            providers: List of provider names (default: ["azure_whisper", "deepgram"])
            strategy: Load balancing strategy (default: "adaptive")
                - "adaptive": Intelligent selection based on performance metrics
                - "round_robin": Alternate between providers
                - "weighted": Weighted by provider speed
        """
        self.providers = providers or self._get_available_providers()
        self.strategy = strategy
        self.current_index = 0
        self.lock = threading.Lock()

        # NEW: Performance tracking per provider (rolling window)
        self.performance_stats: dict[str, dict] = defaultdict(
            lambda: {
                "resolution_times": deque(maxlen=WINDOW_SIZE),  # Last 5 resolution times
                "retry_attempts": deque(maxlen=WINDOW_SIZE),  # Last 5 retry attempts
                "total_chunks": 0,
                "failed_chunks": 0,
            }
        )

        # Session-specific provider preference (adapts per session)
        self.session_provider: dict[str, str] = {}  # session_id -> preferred_provider

        if not self.providers:
            raise ValueError("No STT providers available. Check API keys in .env")

        logger.info(
            "STT_LOAD_BALANCER_INITIALIZED",
            providers=self.providers,
            strategy=strategy,
            num_providers=len(self.providers),
        )

    def _get_available_providers(self) -> list[str]:
        """Detect available providers based on environment variables.

        Returns:
            List of available provider names
        """
        available = []

        # ❌ TEMPORARY: Azure Whisper disabled - fails silently with duration=0.0
        # if os.getenv("AZURE_OPENAI_ENDPOINT") and os.getenv("AZURE_OPENAI_KEY"):
        #     available.append("azure_whisper")

        # Check Deepgram (ONLY provider for now)
        if os.getenv("DEEPGRAM_API_KEY"):
            available.append("deepgram")

        logger.info(
            "STT_PROVIDERS_DETECTED",
            available=available,
            azure_configured=bool(os.getenv("AZURE_OPENAI_ENDPOINT")),
            deepgram_configured=bool(os.getenv("DEEPGRAM_API_KEY")),
        )

        return available

    def select_provider(
        self, chunk_number: Optional[int] = None, session_id: Optional[str] = None
    ) -> str:
        """Select next provider using configured strategy.

        Args:
            chunk_number: Optional chunk number for deterministic selection
            session_id: Optional session ID for adaptive selection

        Returns:
            Provider name (e.g., "azure_whisper" or "deepgram")

        Strategy:
            - adaptive: Intelligent selection based on performance (NEW)
            - round_robin: Alternates providers sequentially
            - chunk_number-based: Uses chunk_number % num_providers for determinism
        """
        if not self.providers:
            raise ValueError("No providers available")

        if len(self.providers) == 1:
            return self.providers[0]

        # NEW: Adaptive strategy (default)
        if self.strategy == "adaptive":
            return self.select_adaptive_provider(session_id=session_id)

        # Round-robin strategy
        with self.lock:
            if self.strategy == "round_robin":
                if chunk_number is not None:
                    # Deterministic: chunk 0→Azure, 1→Deepgram, 2→Azure, etc.
                    index = chunk_number % len(self.providers)
                else:
                    # Sequential: increment counter
                    index = self.current_index
                    self.current_index = (self.current_index + 1) % len(self.providers)

                provider = self.providers[index]

                logger.debug(
                    "STT_PROVIDER_SELECTED",
                    provider=provider,
                    chunk_number=chunk_number,
                    index=index,
                    strategy=self.strategy,
                )

                return provider

            else:
                # Default: return first provider
                return self.providers[0]

    def record_performance(
        self,
        provider: str,
        resolution_time: float,
        retry_attempts: int = 0,
        failed: bool = False,
    ) -> None:
        """Record performance metrics for a provider.

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

    def select_adaptive_provider(self, session_id: Optional[str] = None) -> str:
        """Select provider based on performance metrics (adaptive strategy).

        Strategy:
          1. If session has preferred provider, check if it's still performing well
          2. If not, select provider with best avg resolution_time
          3. Switch if current provider is slow (>10s) or has many retries

        Args:
            session_id: Optional session ID for session-specific preference

        Returns:
            Provider name
        """
        if len(self.providers) == 1:
            return self.providers[0]

        with self.lock:
            # Check if we have performance data
            providers_with_data = [
                p for p in self.providers if len(self.performance_stats[p]["resolution_times"]) > 0
            ]

            if not providers_with_data:
                # No data yet - use round-robin
                provider = self.providers[self.current_index]
                self.current_index = (self.current_index + 1) % len(self.providers)
                logger.debug("ADAPTIVE_NO_DATA_FALLBACK_ROUND_ROBIN", provider=provider)
                return provider

            # Calculate average performance for each provider
            provider_scores = {}
            for provider in providers_with_data:
                stats = self.performance_stats[provider]
                times = list(stats["resolution_times"])
                retries = list(stats["retry_attempts"])

                avg_time = sum(times) / len(times)
                avg_retries = sum(retries) / len(retries)
                failure_rate = stats["failed_chunks"] / stats["total_chunks"]

                # Score: lower is better (penalize slow time, retries, failures)
                score = avg_time + (avg_retries * 2) + (failure_rate * 10)
                provider_scores[provider] = score

            # Select provider with lowest score (best performance)
            best_provider = min(provider_scores, key=provider_scores.get)  # type: ignore[arg-type]

            # Check if session has a preferred provider
            if session_id and session_id in self.session_provider:
                preferred = self.session_provider[session_id]
                preferred_stats = self.performance_stats[preferred]

                # Check if preferred provider is still good
                if len(preferred_stats["resolution_times"]) > 0:
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
                        logger.debug(
                            "ADAPTIVE_KEEP_PREFERRED",
                            session_id=session_id,
                            provider=preferred,
                            avg_time=round(avg_time, 2),
                        )
                        return preferred

            # No preferred provider yet - use best one
            if session_id:
                self.session_provider[session_id] = best_provider

            logger.info(
                "ADAPTIVE_PROVIDER_SELECTED",
                provider=best_provider,
                score=round(provider_scores[best_provider], 2),
                session_id=session_id,
            )

            return best_provider

    def get_fallback_provider(self, failed_provider: str) -> Optional[str]:
        """Get fallback provider if one fails.

        Args:
            failed_provider: Provider that failed

        Returns:
            Alternative provider name, or None if no alternatives
        """
        alternatives = [p for p in self.providers if p != failed_provider]

        if alternatives:
            fallback = alternatives[0]
            logger.warning(
                "STT_PROVIDER_FALLBACK",
                failed_provider=failed_provider,
                fallback_provider=fallback,
            )
            return fallback

        return None

    def get_stats(self) -> dict:
        """Get load balancer statistics with performance metrics.

        Returns:
            Dict with provider stats and performance data
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

            return {
                "providers": self.providers,
                "strategy": self.strategy,
                "num_providers": len(self.providers),
                "current_index": self.current_index,
                "performance": performance_summary,
                "session_preferences": dict(self.session_provider),
            }


# Global singleton instance
_load_balancer: Optional[STTLoadBalancer] = None
_balancer_lock = threading.Lock()


def get_stt_load_balancer() -> STTLoadBalancer:
    """Get or create global STT load balancer (singleton).

    Returns:
        STTLoadBalancer instance
    """
    global _load_balancer

    if _load_balancer is None:
        with _balancer_lock:
            if _load_balancer is None:
                _load_balancer = STTLoadBalancer()

    return _load_balancer
