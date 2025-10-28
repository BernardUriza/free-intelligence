"""
Free Intelligence - LLM Router with Multi-Provider Abstraction

Provides a unified interface for LLM interactions, supporting multiple providers:
- Claude (Anthropic) - Primary for MVP
- Ollama (Local inference) - Future offline-first goal
- OpenAI - Future optional

Philosophy: Provider-agnostic design. No vendor lock-in.
"""

import os
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import numpy as np
import anthropic
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

from backend.logger import get_logger
from backend.llm_audit_policy import require_audit_log
from backend.audit_logs import append_audit_log
from backend.policy_loader import get_policy_loader

logger = get_logger(__name__)


class LLMProviderType(Enum):
    """Supported LLM providers"""
    CLAUDE = "claude"
    OLLAMA = "ollama"
    OPENAI = "openai"


@dataclass
class LLMResponse:
    """Unified response format from any LLM provider"""
    content: str
    model: str
    provider: str
    tokens_used: int
    cost_usd: Optional[float] = None
    latency_ms: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """
        Generate text completion from prompt.

        Args:
            prompt: Input text prompt
            **kwargs: Provider-specific parameters (temperature, max_tokens, etc.)

        Returns:
            LLMResponse with content and metadata
        """
        pass

    @abstractmethod
    def embed(self, text: str) -> np.ndarray:
        """
        Generate embedding vector for text.

        Args:
            text: Input text to embed

        Returns:
            numpy array with embedding vector
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return provider name (claude, ollama, openai)"""
        pass


class ClaudeProvider(LLMProvider):
    """Anthropic Claude provider implementation"""

    # Pricing per 1M tokens (as of 2025-10)
    PRICING = {
        "claude-3-5-sonnet-20241022": {
            "input": 3.00,   # $3 per 1M input tokens
            "output": 15.00  # $15 per 1M output tokens
        },
        "claude-3-5-haiku-20241022": {
            "input": 0.80,   # $0.80 per 1M input tokens
            "output": 4.00   # $4 per 1M output tokens
        }
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        api_key = os.getenv("CLAUDE_API_KEY")
        if not api_key:
            raise ValueError("CLAUDE_API_KEY environment variable not set")

        self.client = anthropic.Anthropic(api_key=api_key)
        self.default_model = self.config.get("model", "claude-3-5-sonnet-20241022")
        self.timeout = self.config.get("timeout_seconds", 30)
        self.logger.info("CLAUDE_PROVIDER_INITIALIZED", model=self.default_model)

    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate completion using Claude API"""
        model = kwargs.get("model", self.default_model)
        max_tokens = kwargs.get("max_tokens", self.config.get("max_tokens", 4096))
        temperature = kwargs.get("temperature", self.config.get("temperature", 0.7))

        self.logger.info("CLAUDE_GENERATE_STARTED",
                        model=model,
                        prompt_length=len(prompt))

        start_time = datetime.utcnow()

        try:
            message = self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
                timeout=self.timeout
            )

            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            # Extract response content
            content = message.content[0].text if message.content else ""

            # Calculate cost
            input_tokens = message.usage.input_tokens
            output_tokens = message.usage.output_tokens
            total_tokens = input_tokens + output_tokens

            pricing = self.PRICING.get(model, self.PRICING["claude-3-5-sonnet-20241022"])
            cost_usd = (
                (input_tokens / 1_000_000) * pricing["input"] +
                (output_tokens / 1_000_000) * pricing["output"]
            )

            self.logger.info("CLAUDE_GENERATE_COMPLETED",
                           model=model,
                           tokens_used=total_tokens,
                           cost_usd=round(cost_usd, 6),
                           latency_ms=round(latency_ms, 2))

            return LLMResponse(
                content=content,
                model=model,
                provider="claude",
                tokens_used=total_tokens,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                metadata={
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "stop_reason": message.stop_reason
                }
            )

        except anthropic.APITimeoutError as e:
            self.logger.error("CLAUDE_TIMEOUT_ERROR", error=str(e), timeout=self.timeout)
            raise
        except anthropic.APIConnectionError as e:
            self.logger.error("CLAUDE_CONNECTION_ERROR", error=str(e))
            raise
        except anthropic.RateLimitError as e:
            self.logger.error("CLAUDE_RATE_LIMIT_ERROR", error=str(e))
            raise
        except anthropic.APIError as e:
            self.logger.error("CLAUDE_API_ERROR", error=str(e), status_code=getattr(e, 'status_code', None))
            raise

    def embed(self, text: str) -> np.ndarray:
        """
        Claude doesn't provide embeddings API.
        Fall back to sentence-transformers.
        """
        self.logger.warning("CLAUDE_EMBED_NOT_SUPPORTED",
                          message="Claude doesn't support embeddings, falling back to sentence-transformers")

        # Import here to avoid loading model unless needed
        from sentence_transformers import SentenceTransformer

        # Use lightweight model
        model = SentenceTransformer('all-MiniLM-L6-v2')
        embedding = model.encode(text, convert_to_numpy=True)

        return embedding

    def get_provider_name(self) -> str:
        return "claude"


class OllamaProvider(LLMProvider):
    """Ollama local inference provider (FUTURE - Sprint 3 of roadmap)"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.base_url = self.config.get("base_url", "http://localhost:11434")
        self.default_model = self.config.get("model", "qwen2:7b-instruct-q4_0")
        self.logger.info("OLLAMA_PROVIDER_INITIALIZED",
                        base_url=self.base_url,
                        model=self.default_model)

    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate completion using Ollama API"""
        # TODO: Implement in Sprint 3 of roadmap (Offline CPU)
        raise NotImplementedError(
            "OllamaProvider will be implemented in Sprint 3 of roadmap. "
            "See docs/ROADMAP_OFFLINE_FIRST.md"
        )

    def embed(self, text: str) -> np.ndarray:
        """Generate embedding using Ollama"""
        # TODO: Implement in Sprint 3 of roadmap
        raise NotImplementedError(
            "OllamaProvider embeddings will be implemented in Sprint 3 of roadmap"
        )

    def get_provider_name(self) -> str:
        return "ollama"


def get_provider(provider_name: str, config: Optional[Dict[str, Any]] = None) -> LLMProvider:
    """
    Factory function to get LLM provider instance.

    Args:
        provider_name: "claude", "ollama", or "openai"
        config: Provider-specific configuration

    Returns:
        LLMProvider instance

    Raises:
        ValueError: If provider not supported
    """
    provider_map = {
        "claude": ClaudeProvider,
        "ollama": OllamaProvider,
        # "openai": OpenAIProvider,  # Future
    }

    provider_class = provider_map.get(provider_name.lower())
    if not provider_class:
        raise ValueError(
            f"Unknown provider: {provider_name}. "
            f"Supported: {list(provider_map.keys())}"
        )

    return provider_class(config)


@require_audit_log
def llm_generate(
    prompt: str,
    provider: Optional[str] = None,
    provider_config: Optional[Dict[str, Any]] = None,
    **kwargs
) -> LLMResponse:
    """
    Generate text completion using specified LLM provider.

    This is the main entry point for LLM text generation in Free Intelligence.
    Automatically logs to audit_logs.

    Args:
        prompt: Input text prompt
        provider: Provider name ("claude", "ollama", "openai"). If None, uses primary_provider from policy.
        provider_config: Provider-specific configuration (model, timeout, etc.). If None, uses policy config.
        **kwargs: Additional provider-specific parameters (override policy defaults)

    Returns:
        LLMResponse with content and metadata

    Example:
        >>> # Use policy defaults
        >>> response = llm_generate("What is Free Intelligence?")

        >>> # Override provider
        >>> response = llm_generate(
        ...     "What is Free Intelligence?",
        ...     provider="claude",
        ...     temperature=0.7,
        ...     max_tokens=1024
        ... )
    """
    # Load policy
    policy_loader = get_policy_loader()

    # Use primary provider from policy if not specified
    if provider is None:
        provider = policy_loader.get_primary_provider()
        logger.info("LLM_PROVIDER_FROM_POLICY", provider=provider)

    # Load provider config from policy if not specified
    if provider_config is None:
        provider_config = policy_loader.get_provider_config(provider)
        logger.info("LLM_CONFIG_FROM_POLICY", provider=provider, model=provider_config.get('model'))

    logger.info("LLM_GENERATE_STARTED", provider=provider, prompt_length=len(prompt))

    try:
        # Get provider instance
        llm_provider = get_provider(provider, provider_config)

        # Generate response
        response = llm_provider.generate(prompt, **kwargs)

        # Log to audit_logs
        from backend.config_loader import load_config
        config = load_config()
        corpus_path = config['storage']['corpus_path']

        append_audit_log(
            corpus_path=corpus_path,
            operation="LLM_GENERATE",
            user_id="system",  # TODO: Get from session context
            endpoint=f"llm_router.llm_generate({provider})",
            payload={"prompt": prompt[:100], "provider": provider},  # First 100 chars
            result={"content": response.content[:100], "tokens": response.tokens_used},
            status="SUCCESS",
            metadata={
                "provider": provider,
                "model": response.model,
                "tokens_used": response.tokens_used,
                "cost_usd": response.cost_usd,
                "latency_ms": response.latency_ms
            }
        )

        logger.info("LLM_GENERATE_COMPLETED",
                   provider=provider,
                   model=response.model,
                   tokens=response.tokens_used)

        return response

    except Exception as e:
        logger.error("LLM_GENERATE_FAILED", provider=provider, error=str(e))

        # Log failure to audit_logs
        from backend.config_loader import load_config
        config = load_config()
        corpus_path = config['storage']['corpus_path']

        append_audit_log(
            corpus_path=corpus_path,
            operation="LLM_GENERATE",
            user_id="system",
            endpoint=f"llm_router.llm_generate({provider})",
            payload={"prompt": prompt[:100], "provider": provider},
            result=None,
            status="FAILED",
            metadata={"error": str(e), "provider": provider}
        )

        raise


def llm_embed(
    text: str,
    provider: str = "claude",
    provider_config: Optional[Dict[str, Any]] = None
) -> np.ndarray:
    """
    Generate embedding vector for text.

    Note: Claude doesn't support embeddings, falls back to sentence-transformers.
    Ollama (future) will support embeddings natively.

    Args:
        text: Input text to embed
        provider: Provider name
        provider_config: Provider-specific configuration

    Returns:
        numpy array with embedding vector (typically 384 or 768 dimensions)
    """
    logger.info("LLM_EMBED_STARTED", provider=provider, text_length=len(text))

    try:
        llm_provider = get_provider(provider, provider_config)
        embedding = llm_provider.embed(text)

        logger.info("LLM_EMBED_COMPLETED",
                   provider=provider,
                   embedding_dim=len(embedding))

        return embedding

    except Exception as e:
        logger.error("LLM_EMBED_FAILED", provider=provider, error=str(e))
        raise


if __name__ == "__main__":
    """Demo script"""
    print("🧠 Free Intelligence - LLM Router Demo")
    print("=" * 50)

    # Test 1: Get provider
    print("\n1️⃣  Testing provider factory...")
    try:
        claude = get_provider("claude")
        print(f"   ✅ ClaudeProvider initialized: {claude.get_provider_name()}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 2: Generate with Claude using policy defaults (requires API key)
    if os.getenv("CLAUDE_API_KEY"):
        print("\n2️⃣  Testing Claude generation (using policy defaults)...")
        try:
            response = llm_generate(
                prompt="What is 2+2? Answer in one sentence.",
                max_tokens=50  # Override only max_tokens, everything else from policy
            )
            print(f"   ✅ Response: {response.content}")
            print(f"   📋 Provider: {response.provider}")
            print(f"   🤖 Model: {response.model}")
            print(f"   💰 Cost: ${response.cost_usd:.6f}")
            print(f"   ⏱️  Latency: {response.latency_ms:.2f}ms")
            print(f"   🔢 Tokens: {response.tokens_used}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    else:
        print("\n2️⃣  Skipping Claude test (CLAUDE_API_KEY not set)")

    # Test 3: Embedding
    print("\n3️⃣  Testing embedding...")
    try:
        embedding = llm_embed("Free Intelligence is awesome", provider="claude")
        print(f"   ✅ Embedding generated: {len(embedding)} dimensions")
        print(f"   📊 First 5 values: {embedding[:5]}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    print("\n" + "=" * 50)
    print("Demo complete!")
