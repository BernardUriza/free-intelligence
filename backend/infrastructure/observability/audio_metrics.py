"""
Audio Subsystem Metrics - Prometheus-compatible observability

Tracks key metrics for the audio subsystem:
- Cache hit/miss rates
- TTS request latency by provider
- Error rates by error code
- Total requests by provider and voice

Metrics are exposed via /api/observability/audio/metrics endpoint
and compatible with Prometheus scraping.

Module: fi_observability.audio_metrics
"""

import threading
from collections import defaultdict
from datetime import datetime
from typing import Any

from backend.utils.common.types import utc_now


class AudioMetrics:
    """
    Thread-safe audio metrics collector

    Collects metrics from frontend and backend for observability.
    Provides Prometheus-compatible format for scraping.
    """

    def __init__(self):
        self._lock = threading.Lock()

        # Counters
        self.tts_requests_total: dict[str, int] = defaultdict(int)  # {provider:voice:count}
        self.cache_hits_total: int = 0
        self.cache_misses_total: int = 0
        self.errors_total: dict[str, int] = defaultdict(int)  # {error_code:count}

        # Histograms (simplified - store samples)
        self.latency_samples: dict[str, list] = defaultdict(list)  # {provider:[latencies]}

        # Gauges
        self.cache_size: int = 0
        self.cache_max: int = 50
        self.queue_depth: int = 0

        # Session info
        self.session_start: datetime = utc_now()

    def record_tts_request(self, provider: str, voice: str):
        """Record a TTS request"""
        with self._lock:
            key = f"{provider}:{voice}"
            self.tts_requests_total[key] += 1

    def record_cache_hit(self):
        """Record a cache hit"""
        with self._lock:
            self.cache_hits_total += 1

    def record_cache_miss(self):
        """Record a cache miss"""
        with self._lock:
            self.cache_misses_total += 1

    def record_error(self, error_code: str):
        """Record an error by code"""
        with self._lock:
            self.errors_total[error_code] += 1

    def record_latency(self, provider: str, latency_ms: float):
        """Record TTS latency"""
        with self._lock:
            self.latency_samples[provider].append(latency_ms)
            # Keep only last 1000 samples per provider
            if len(self.latency_samples[provider]) > 1000:
                self.latency_samples[provider] = self.latency_samples[provider][-1000:]

    def update_cache_size(self, size: int):
        """Update current cache size"""
        with self._lock:
            self.cache_size = size

    def update_queue_depth(self, depth: int):
        """Update current queue depth"""
        with self._lock:
            self.queue_depth = depth

    def get_cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        with self._lock:
            total = self.cache_hits_total + self.cache_misses_total
            if total == 0:
                return 0.0
            return self.cache_hits_total / total

    def get_avg_latency(self, provider: str) -> float:
        """Get average latency for a provider"""
        with self._lock:
            samples = self.latency_samples.get(provider, [])
            if not samples:
                return 0.0
            return sum(samples) / len(samples)

    def get_p95_latency(self, provider: str) -> float:
        """Get p95 latency for a provider"""
        with self._lock:
            samples = self.latency_samples.get(provider, [])
            if not samples:
                return 0.0
            sorted_samples = sorted(samples)
            idx = int(len(sorted_samples) * 0.95)
            return sorted_samples[idx] if idx < len(sorted_samples) else sorted_samples[-1]

    def get_metrics_dict(self) -> dict[str, Any]:
        """
        Get all metrics as a dictionary

        Returns:
            Dictionary with all current metrics
        """
        with self._lock:
            uptime_seconds = (utc_now() - self.session_start).total_seconds()

            return {
                # Counters
                "tts_requests_total": dict(self.tts_requests_total),
                "cache_hits_total": self.cache_hits_total,
                "cache_misses_total": self.cache_misses_total,
                "errors_total": dict(self.errors_total),
                # Derived metrics
                "cache_hit_rate": self.get_cache_hit_rate(),
                # Gauges
                "cache_size": self.cache_size,
                "cache_max": self.cache_max,
                "queue_depth": self.queue_depth,
                # Latency stats by provider
                "latency_avg_ms": {
                    provider: self.get_avg_latency(provider)
                    for provider in self.latency_samples.keys()
                },
                "latency_p95_ms": {
                    provider: self.get_p95_latency(provider)
                    for provider in self.latency_samples.keys()
                },
                # Session info
                "uptime_seconds": uptime_seconds,
            }

    def get_prometheus_format(self) -> str:
        """
        Get metrics in Prometheus text format

        Returns:
            String in Prometheus exposition format
        """
        metrics = self.get_metrics_dict()
        lines = []

        # TTS requests by provider:voice
        lines.append("# HELP audio_tts_requests_total Total TTS requests by provider and voice")
        lines.append("# TYPE audio_tts_requests_total counter")
        for key, count in metrics["tts_requests_total"].items():
            provider, voice = key.split(":", 1)
            lines.append(
                f'audio_tts_requests_total{{provider="{provider}",voice="{voice}"}} {count}'
            )

        # Cache hits
        lines.append("# HELP audio_cache_hits_total Total cache hits")
        lines.append("# TYPE audio_cache_hits_total counter")
        lines.append(f"audio_cache_hits_total {metrics['cache_hits_total']}")

        # Cache misses
        lines.append("# HELP audio_cache_misses_total Total cache misses")
        lines.append("# TYPE audio_cache_misses_total counter")
        lines.append(f"audio_cache_misses_total {metrics['cache_misses_total']}")

        # Errors by code
        lines.append("# HELP audio_errors_total Total errors by error code")
        lines.append("# TYPE audio_errors_total counter")
        for code, count in metrics["errors_total"].items():
            lines.append(f'audio_errors_total{{error_code="{code}"}} {count}')

        # Cache hit rate (gauge)
        lines.append("# HELP audio_cache_hit_rate Cache hit rate (0-1)")
        lines.append("# TYPE audio_cache_hit_rate gauge")
        lines.append(f"audio_cache_hit_rate {metrics['cache_hit_rate']:.4f}")

        # Cache size
        lines.append("# HELP audio_cache_size Current cache size")
        lines.append("# TYPE audio_cache_size gauge")
        lines.append(f"audio_cache_size {metrics['cache_size']}")

        # Queue depth
        lines.append("# HELP audio_queue_depth Current queue depth")
        lines.append("# TYPE audio_queue_depth gauge")
        lines.append(f"audio_queue_depth {metrics['queue_depth']}")

        # Average latency by provider
        lines.append("# HELP audio_tts_latency_avg_ms Average TTS latency by provider")
        lines.append("# TYPE audio_tts_latency_avg_ms gauge")
        for provider, latency in metrics["latency_avg_ms"].items():
            lines.append(f'audio_tts_latency_avg_ms{{provider="{provider}"}} {latency:.2f}')

        # P95 latency by provider
        lines.append("# HELP audio_tts_latency_p95_ms P95 TTS latency by provider")
        lines.append("# TYPE audio_tts_latency_p95_ms gauge")
        for provider, latency in metrics["latency_p95_ms"].items():
            lines.append(f'audio_tts_latency_p95_ms{{provider="{provider}"}} {latency:.2f}')

        # Uptime
        lines.append("# HELP audio_subsystem_uptime_seconds Audio subsystem uptime")
        lines.append("# TYPE audio_subsystem_uptime_seconds counter")
        lines.append(f"audio_subsystem_uptime_seconds {metrics['uptime_seconds']:.0f}")

        return "\n".join(lines) + "\n"


# Global metrics instance
audio_metrics = AudioMetrics()
