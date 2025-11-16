"""LLM client for SOAP extraction - Provider-agnostic implementation.

Uses Claude Sonnet 4.5 via llm_router for medical SOAP note extraction.
Supports any LLM provider configured in fi.policy.yaml.
"""

from __future__ import annotations

from typing import Any, Optional

from backend.logger import get_logger
from backend.providers.llm import llm_generate
from backend.services.soap_generation.prompt_builder import OllamaPromptBuilder
from backend.services.soap_generation.response_parser import (
    OllamaExtractionError,
    OllamaResponseParser,
)

__all__ = ["LLMClient", "SOAPExtractionError"]

logger = get_logger(__name__)

# Alias for consistency
SOAPExtractionError = OllamaExtractionError


class LLMClient:
    """Provider-agnostic LLM client for SOAP extraction.

    Uses llm_router to support multiple LLM providers (Claude, Ollama, OpenAI).
    Configured via backend/config/fi.policy.yaml.

    Modern architecture:
    - Prompt management: OllamaPromptBuilder (reusable)
    - Response parsing: OllamaResponseParser (reusable)
    - LLM interaction: llm_generate from llm_router
    """

    def __init__(
        self,
        provider: str = "claude",
        prompt_builder: Optional[OllamaPromptBuilder] = None,
        response_parser: Optional[OllamaResponseParser] = None,
    ):
        """Initialize LLM client.

        Args:
            provider: LLM provider ("claude", "ollama", "openai")
            prompt_builder: Custom prompt builder (uses default if None)
            response_parser: Custom response parser (uses default if None)
        """
        self.provider = provider

        # Dependency injection with sensible defaults
        self.prompt_builder = prompt_builder or OllamaPromptBuilder()
        self.response_parser = response_parser or OllamaResponseParser()

        logger.info(
            "LLMClient initialized",
            provider=provider,
        )

    def extract_soap(self, transcription: str) -> dict[str, Any]:
        """Extract SOAP sections from medical transcription.

        Accepts medical consultation transcriptions in ANY language.
        Extracts SOAP data without translating medical content.
        Returns standardized JSON with English field names (medical standard).

        Args:
            transcription: Full medical consultation transcription (any language)

        Returns:
            Dictionary with SOAP sections in English field names

        Raises:
            SOAPExtractionError: If extraction fails or returns invalid JSON
        """
        try:
            # Build prompts using dedicated builder
            system_prompt = self.prompt_builder.load_system_prompt()
            user_prompt = self.prompt_builder.build_user_prompt(transcription)

            # Combine system and user prompts for Claude
            # (Claude doesn't use separate system/user in Messages API the same way)
            full_prompt = f"""{system_prompt}

{user_prompt}"""

            logger.info(
                "SOAP_EXTRACTION_START",
                provider=self.provider,
                transcription_length=len(transcription),
            )

            # Use llm_generate from llm_router (supports all providers)
            response = llm_generate(
                full_prompt,
                provider=self.provider,
                max_tokens=4096,  # SOAP notes can be long
                temperature=0.3,  # Balanced: structured but not too rigid
            )

            response_text = response.content.strip()

            logger.debug(
                "LLM_RESPONSE_RECEIVED",
                provider=self.provider,
                response_length=len(response_text),
                response_preview=response_text[:200],
            )

            # Parse and validate response using dedicated parser
            soap_data = self.response_parser.parse_response(response_text)

            logger.info(
                "SOAP_EXTRACTION_SUCCESS",
                provider=self.provider,
                response_length=len(response_text),
            )

            return soap_data

        except SOAPExtractionError:
            raise
        except Exception as e:
            logger.error(
                "SOAP_EXTRACTION_FAILED",
                provider=self.provider,
                error=str(e),
                exc_info=True,
            )
            raise SOAPExtractionError(f"Failed to extract SOAP from LLM: {e!s}") from e
