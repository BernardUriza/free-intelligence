"""Ollama LLM client for SOAP extraction.

Modern, refactored HTTP client for communicating with Ollama service.
Implements separation of concerns with dependency injection for testing.
Validates responses against Pydantic models for type safety.
"""

from __future__ import annotations

from typing import Any, Protocol

import requests

from backend.logger import get_logger
from backend.services.soap_generation.prompt_builder import OllamaPromptBuilder
from backend.services.soap_generation.response_parser import (
    OllamaExtractionError,
    OllamaResponseParser,
)
from backend.services.soap_generation.soap_models import SOAPNote

__all__ = ["OllamaClient", "OllamaExtractionError"]

logger = get_logger(__name__)

# Ollama configuration
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "mistral"
OLLAMA_TIMEOUT = 120


class HttpClient(Protocol):
    """Protocol for HTTP client implementations.

    Allows dependency injection of different HTTP clients (requests, httpx, etc.)
    """

    def post(
        self,
        url: str,
        json: dict[str, Any],
        timeout: int,
    ) -> Any:
        """Execute POST request."""

        ...


class OllamaClient:
    """Client for Ollama LLM service.

    Modern refactored implementation with separated concerns:
    - OllamaPromptBuilder: manages system and user prompts
    - OllamaResponseParser: extracts and validates JSON responses
    - OllamaClient: orchestrates HTTP communication

    Supports dependency injection for custom HTTP clients and prompt builders.
    """

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        model: str = OLLAMA_MODEL,
        timeout: int = OLLAMA_TIMEOUT,
        http_client: Optional[HttpClient] = None,
        prompt_builder: Optional[OllamaPromptBuilder] = None,
        response_parser: Optional[OllamaResponseParser] = None,
    ):
        """Initialize Ollama client.

        Args:
            base_url: Ollama service base URL
            model: Model name (e.g., "mistral", "llama2")
            timeout: Request timeout in seconds
            http_client: Custom HTTP client (uses requests.post by default)
            prompt_builder: Custom prompt builder (uses default by default)
            response_parser: Custom response parser (uses default by default)
        """
        self.base_url = base_url
        self.model = model
        self.timeout = timeout

        # Dependency injection with sensible defaults
        self.http_client = http_client or requests
        self.prompt_builder = prompt_builder or OllamaPromptBuilder()
        self.response_parser = response_parser or OllamaResponseParser()

        logger.info(
            "OllamaClient initialized",
            base_url=base_url,
            model=model,
            timeout=timeout,
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
            OllamaExtractionError: If extraction fails or returns invalid JSON
        """
        try:
            # Build prompts using dedicated builder
            system_prompt = self.prompt_builder.load_system_prompt()
            user_prompt = self.prompt_builder.build_user_prompt(transcription)

            # Make HTTP request
            response = self.http_client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": user_prompt,
                    "system": system_prompt,
                    "stream": False,
                },
                timeout=self.timeout,
            )

            if response.status_code != 200:
                raise OllamaExtractionError(
                    f"Ollama request failed with status {response.status_code}: {response.text}"
                )

            result = response.json()
            response_text: str = result.get("response", "")

            # Parse and validate response using dedicated parser
            soap_data = self.response_parser.parse_response(response_text)

            logger.info(
                "SOAP_EXTRACTED_FROM_OLLAMA",
                model=self.model,
                response_length=len(response_text),
            )

            return soap_data

        except OllamaExtractionError:
            raise
        except Exception as e:
            logger.error("OLLAMA_EXTRACTION_FAILED", error=str(e))
            raise OllamaExtractionError(f"Failed to extract SOAP from Ollama: {str(e)}") from e

    def extract_soap_validated(
        self,
        transcription: str,
    ) -> SOAPNote:
        """Extract SOAP sections and return validated SOAPNote model.

        This method provides additional type safety by returning a Pydantic model.

        Args:
            transcription: Full medical consultation transcription (any language)

        Returns:
            Validated SOAPNote instance

        Raises:
            OllamaExtractionError: If extraction or validation fails
        """
        soap_dict = self.extract_soap(transcription)
        return self.response_parser.validate_and_convert(soap_dict)
