"""Parser for Ollama responses.

Extracts and validates JSON from LLM responses with comprehensive error handling.
Converts parsed JSON to Pydantic models for type safety.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict

from pydantic import ValidationError

from backend.logger import get_logger
from backend.services.soap_generation.soap_models import SOAPNote

__all__ = ["OllamaExtractionError", "OllamaResponseParser"]

logger = get_logger(__name__)


class OllamaExtractionError(Exception):
    """Raised when Ollama response parsing or validation fails."""

    pass


class OllamaResponseParser:
    """Parses and validates Ollama LLM responses.

    Extracts JSON from responses, handles various formats, and validates
    against the SOAP data model.
    """

    # Regex to find JSON blocks in text (handles nested braces)
    JSON_BLOCK_PATTERN = re.compile(r"\{(?:[^{}]|(?:\{[^{}]*\}))*\}", re.DOTALL)

    def parse_response(
        self,
        response_text: str,
        strict: bool = False,
    ) -> dict[str, Any]:
        """Parse Ollama response and extract JSON.

        Handles cases where JSON is embedded in other text, markdown code blocks,
        or wrapped in explanatory text.

        Args:
            response_text: Full response text from Ollama
            strict: If True, validate against SOAPNote model immediately

        Returns:
            Parsed JSON dictionary

        Raises:
            OllamaExtractionError: If JSON cannot be found or parsed
        """
        if not response_text or not response_text.strip():
            logger.warning("EMPTY_RESPONSE_TEXT")
            raise OllamaExtractionError("Ollama returned empty response")

        # Try to extract JSON from response
        json_dict = self._extract_json(response_text)

        if strict:
            self._validate_soap_structure(json_dict)

        logger.debug(
            "RESPONSE_PARSED_SUCCESSFULLY",
            response_length=len(response_text),
            extracted_keys=list(json_dict.keys()),
        )

        return json_dict

    def _extract_json(self, text: str) -> dict[str, Any]:
        """Extract JSON from text.

        Tries multiple strategies:
        1. Simple bracket matching (find first { and last })
        2. Regex-based JSON block detection
        3. Markdown code block extraction
        4. JSON validity fixing (trailing commas, etc.)

        Args:
            text: Text containing JSON

        Returns:
            Parsed JSON dictionary

        Raises:
            OllamaExtractionError: If no valid JSON found
        """
        # Strategy 1: Simple bracket matching
        json_dict = self._try_simple_extraction(text)
        if json_dict is not None:
            return json_dict

        # Strategy 2: Regex-based extraction
        json_dict = self._try_regex_extraction(text)
        if json_dict is not None:
            return json_dict

        # Strategy 3: Markdown code block extraction
        json_dict = self._try_markdown_extraction(text)
        if json_dict is not None:
            return json_dict

        # All strategies failed
        logger.error(
            "NO_JSON_FOUND",
            response_preview=text[:300],
        )
        raise OllamaExtractionError(
            f"Could not extract valid JSON from response. Preview: {text[:200]}"
        )

    def _try_simple_extraction(self, text: str) -> dict[str, Any] | None:
        """Try simple bracket matching extraction.

        Args:
            text: Text to extract from

        Returns:
            Parsed dict or None if extraction fails
        """
        json_start = text.find("{")
        json_end = text.rfind("}") + 1

        if json_start == -1 or json_end <= json_start:
            return None

        json_str = text[json_start:json_end]
        return self._parse_json_string(json_str)

    def _try_regex_extraction(self, text: str) -> dict[str, Any] | None:
        """Try regex-based JSON extraction.

        Args:
            text: Text to extract from

        Returns:
            Parsed dict or None if extraction fails
        """
        matches = self.JSON_BLOCK_PATTERN.findall(text)
        for match in matches:
            result = self._parse_json_string(match)
            if result is not None:
                return result

        return None

    def _try_markdown_extraction(self, text: str) -> dict[str, Any] | None:
        """Try to extract JSON from markdown code blocks.

        Handles ```json ... ``` and similar markdown blocks.

        Args:
            text: Text to extract from

        Returns:
            Parsed dict or None if extraction fails
        """
        # Look for json code blocks
        md_pattern = r"```(?:json)?\s*(\{[\s\S]*?\})\s*```"
        matches = re.findall(md_pattern, text)

        for match in matches:
            result = self._parse_json_string(match)
            if result is not None:
                return result

        return None

    def _parse_json_string(self, json_str: str) -> dict[str, Any] | None:
        """Attempt to parse a JSON string.

        Args:
            json_str: String to parse

        Returns:
            Parsed dict or None if parsing fails
        """
        if not json_str or not json_str.strip():
            return None

        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Try to fix common issues
            try:
                # Fix trailing commas
                fixed_str = re.sub(r",(\s*[}\]])", r"\1", json_str)
                return json.loads(fixed_str)
            except json.JSONDecodeError:
                return None

    def _validate_soap_structure(self, data: Dict[str, Any]) -> None:
        """Validate that parsed JSON matches SOAP structure.

        Uses Pydantic model validation for type safety.

        Args:
            data: Parsed JSON dictionary

        Raises:
            OllamaExtractionError: If validation fails
        """
        try:
            soap_note = SOAPNote(**data)

            # Additional completeness checks
            errors = soap_note.validate_completeness()
            if errors:
                error_msg = "; ".join(errors)
                logger.warning("SOAP_COMPLETENESS_WARNING", errors=error_msg)
                # Don't raise here - allow partially filled forms

            logger.info("SOAP_VALIDATION_PASSED")

        except ValidationError as e:
            logger.error(
                "SOAP_VALIDATION_FAILED",
                errors=e.errors(),
            )
            raise OllamaExtractionError(f"SOAP response failed validation: {e!s}") from e

    def validate_and_convert(
        self,
        data: Dict[str, Any],
    ) -> SOAPNote:
        """Validate and convert raw dict to SOAPNote model.

        Args:
            data: Raw parsed JSON dictionary

        Returns:
            Validated SOAPNote instance

        Raises:
            OllamaExtractionError: If validation fails
        """
        try:
            return SOAPNote(**data)
        except ValidationError as e:
            logger.error(
                "SOAP_CONVERSION_FAILED",
                errors=e.errors(),
            )
            raise OllamaExtractionError(f"Failed to convert to SOAP model: {e!s}") from e
