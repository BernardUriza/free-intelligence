"""
Free Intelligence - Ollama Provider (STUB)

Local Ollama adapter - NOT IMPLEMENTED YET.

File: backend/providers/ollama.py
Created: 2025-10-28

Status: STUB - Returns 501 NOT IMPLEMENTED
"""

from typing import Iterator, Optional

from backend.llm_adapter import (
    LLMAdapter,
    LLMBudget,
    LLMRequest,
    LLMResponse,
    NotImplementedProviderError,
)
from backend.logger import get_logger

logger = get_logger(__name__)


class OllamaAdapter(LLMAdapter):
    """
    Ollama local LLM adapter.

    Status: STUB - Not implemented yet.

    Will support:
    - Local models (llama3.2, mistral, etc.)
    - No API key required
    - Fully local execution
    - generate(), stream(), summarize()

    Current behavior:
    - All methods raise NotImplementedProviderError with 501 status
    - Returns documentation for future implementation
    """

    def __init__(
        self,
        model: str = "llama3.2",
        budget: Optional[LLMBudget] = None,
        max_retries: int = 3,
        ollama_host: str = "http://localhost:11434",
    ):
        super().__init__(
            provider_name="ollama",
            model=model,
            budget=budget,
            max_retries=max_retries,
        )
        self.ollama_host = ollama_host

    def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate response (NOT IMPLEMENTED).

        Raises:
            NotImplementedProviderError: Always (stub)
        """
        logger.warning(
            "OLLAMA_NOT_IMPLEMENTED",
            method="generate",
            model=self.model,
            message="Ollama provider is a stub. Use provider='claude' instead.",
        )

        raise NotImplementedProviderError(
            "Ollama provider not implemented yet. "
            "This is a stub that returns 501 NOT IMPLEMENTED. "
            "Use provider='claude' for actual LLM calls. "
            "\n\n"
            "Future implementation will support:\n"
            "- Local Ollama models (llama3.2, mistral, etc.)\n"
            "- No API key required\n"
            "- Fully local execution\n"
            "- Same interface as Claude adapter\n"
            "\n"
            "To implement: Install ollama, run 'ollama serve', "
            "and implement OllamaAdapter.generate() using requests library."
        )

    def stream(self, request: LLMRequest) -> Iterator[str]:
        """
        Stream response (NOT IMPLEMENTED).

        Raises:
            NotImplementedProviderError: Always (stub)
        """
        logger.warning(
            "OLLAMA_NOT_IMPLEMENTED",
            method="stream",
            model=self.model,
            message="Ollama provider is a stub.",
        )

        raise NotImplementedProviderError(
            "Ollama streaming not implemented yet. Use provider='claude' instead."
        )
