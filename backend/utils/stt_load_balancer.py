"""STT Load Balancer - Intelligent provider selection.

Philosophy:
  - Distribute chunks across multiple STT providers to maximize throughput
  - Avoid rate limiting by alternating between Azure Whisper and Deepgram
  - Thread-safe round-robin selection
  - Automatic fallback if provider fails

Strategy:
  - Chunk 0 → Azure Whisper
  - Chunk 1 → Deepgram
  - Chunk 2 → Azure Whisper
  - Chunk 3 → Deepgram
  - etc.

This keeps Azure Whisper at ~2 RPM (under 3 RPM limit) and uses Deepgram
for the rest, achieving ~2x throughput without hitting rate limits.

Created: 2025-11-15
Author: Bernard Uriza Orozco
Card: STT Load Balancing
"""

from __future__ import annotations

import os
import threading
from typing import Optional

from backend.logger import get_logger

logger = get_logger(__name__)


class STTLoadBalancer:
    """Intelligent load balancer for STT providers."""

    def __init__(
        self,
        providers: Optional[list[str]] = None,
        strategy: str = "round_robin",
    ):
        """Initialize load balancer.

        Args:
            providers: List of provider names (default: ["azure_whisper", "deepgram"])
            strategy: Load balancing strategy (default: "round_robin")
                - "round_robin": Alternate between providers
                - "random": Random selection
                - "weighted": Weighted by provider speed
        """
        self.providers = providers or self._get_available_providers()
        self.strategy = strategy
        self.current_index = 0
        self.lock = threading.Lock()

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

    def select_provider(self, chunk_number: Optional[int] = None) -> str:
        """Select next provider using configured strategy.

        Args:
            chunk_number: Optional chunk number for deterministic selection

        Returns:
            Provider name (e.g., "azure_whisper" or "deepgram")

        Strategy:
            - round_robin: Alternates providers sequentially
            - chunk_number-based: Uses chunk_number % num_providers for determinism
        """
        if not self.providers:
            raise ValueError("No providers available")

        if len(self.providers) == 1:
            return self.providers[0]

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
        """Get load balancer statistics.

        Returns:
            Dict with provider stats
        """
        return {
            "providers": self.providers,
            "strategy": self.strategy,
            "num_providers": len(self.providers),
            "current_index": self.current_index,
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
