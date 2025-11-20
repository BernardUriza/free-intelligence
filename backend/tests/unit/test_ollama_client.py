"""Unit tests for refactored Ollama client components.

Tests cover prompt building, response parsing, and SOAP extraction.
Includes mocking for HTTP requests and comprehensive error scenarios.
"""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from backend.services.soap_generation.llm_client import (
    LLMClient as OllamaClient,  # Alias for backward compat
)
from backend.services.soap_generation.llm_client import (
    SOAPExtractionError as OllamaExtractionError,
)
from backend.services.soap_generation.prompt_builder import OllamaPromptBuilder
from backend.services.soap_generation.response_parser import OllamaResponseParser
from backend.services.soap_generation.soap_models import SOAPNote


class TestOllamaPromptBuilder:
    """Tests for OllamaPromptBuilder class."""

    def test_load_system_prompt_from_file(self, tmp_path: Path) -> None:
        """Test loading system prompt from external file."""
        # Create temporary prompt file
        prompt_dir = tmp_path / "prompts"
        prompt_dir.mkdir()
        prompt_file = prompt_dir / "test_prompt.txt"
        prompt_content = "You are a test prompt."
        prompt_file.write_text(prompt_content)

        # Load prompt
        builder = OllamaPromptBuilder(prompt_dir)
        loaded = builder.load_system_prompt("test_prompt.txt")

        assert loaded == prompt_content

    def test_prompt_file_not_found(self, tmp_path: Path) -> None:
        """Test error when prompt file doesn't exist."""
        prompt_dir = tmp_path / "prompts"
        prompt_dir.mkdir()

        builder = OllamaPromptBuilder(prompt_dir)

        with pytest.raises(FileNotFoundError):
            builder.load_system_prompt("nonexistent.txt")

    def test_prompt_caching(self, tmp_path: Path) -> None:
        """Test that prompts are cached in memory."""
        prompt_dir = tmp_path / "prompts"
        prompt_dir.mkdir()
        prompt_file = prompt_dir / "test.txt"
        prompt_file.write_text("Cached prompt")

        builder = OllamaPromptBuilder(prompt_dir)

        # First load
        result1 = builder.load_system_prompt("test.txt")
        # Modify file
        prompt_file.write_text("Modified prompt")
        # Second load should return cached version
        result2 = builder.load_system_prompt("test.txt")

        assert result1 == result2 == "Cached prompt"

    def test_clear_cache(self, tmp_path: Path) -> None:
        """Test cache clearing."""
        prompt_dir = tmp_path / "prompts"
        prompt_dir.mkdir()
        prompt_file = prompt_dir / "test.txt"
        prompt_file.write_text("Original")

        builder = OllamaPromptBuilder(prompt_dir)
        result1 = builder.load_system_prompt("test.txt")

        # Modify file and clear cache
        prompt_file.write_text("Modified")
        builder.clear_cache()
        result2 = builder.load_system_prompt("test.txt")

        assert result1 == "Original"
        assert result2 == "Modified"

    def test_build_user_prompt(self) -> None:
        """Test user prompt formatting."""
        builder = OllamaPromptBuilder()
        transcription = "Patient reports fever"

        prompt = builder.build_user_prompt(transcription)

        assert "Medical consultation transcription:" in prompt
        assert transcription in prompt


class TestOllamaResponseParser:
    """Tests for OllamaResponseParser class."""

    @pytest.fixture
    def valid_soap_dict(self) -> dict:
        """Valid SOAP response dictionary with English field names."""
        return {
            "subjective": {
                "chief_complaint": "Fever",
                "history_present_illness": "Patient has had fever for 3 days",
                "past_medical_history": "No relevant medical history",
            },
            "objective": {
                "vital_signs": "BP: 120/80, Temp: 38.5C, HR: 90",
                "physical_exam": "Throat redness observed",
            },
            "assessment": {
                "differential_diagnoses": ["Strep throat", "Viral infection"],
                "primary_diagnosis": "Acute pharyngitis",
            },
            "plan": {
                "treatment": "Antibiotics prescribed",
                "follow_up": "Return in 7 days",
                "studies": ["Throat culture"],
            },
        }

    def test_parse_simple_json_response(
        self,
        valid_soap_dict: dict,
    ) -> None:
        """Test parsing simple JSON response."""
        response_text = json.dumps(valid_soap_dict)
        parser = OllamaResponseParser()

        result = parser.parse_response(response_text)

        assert result == valid_soap_dict

    def test_parse_json_with_surrounding_text(
        self,
        valid_soap_dict: dict,
    ) -> None:
        """Test parsing JSON embedded in surrounding text."""
        json_str = json.dumps(valid_soap_dict)
        response_text = f"Here is the SOAP note:\n{json_str}\nEnd of note."
        parser = OllamaResponseParser()

        result = parser.parse_response(response_text)

        assert result == valid_soap_dict

    def test_parse_json_in_markdown_block(
        self,
        valid_soap_dict: dict,
    ) -> None:
        """Test parsing JSON from markdown code block."""
        json_str = json.dumps(valid_soap_dict)
        response_text = f"```json\n{json_str}\n```"
        parser = OllamaResponseParser()

        result = parser.parse_response(response_text)

        assert result == valid_soap_dict

    def test_parse_invalid_json(self) -> None:
        """Test error when JSON is malformed."""
        response_text = "{ invalid json }"
        parser = OllamaResponseParser()

        with pytest.raises(OllamaExtractionError):
            parser.parse_response(response_text)

    def test_parse_no_json_found(self) -> None:
        """Test error when no JSON in response."""
        response_text = "No JSON here, just plain text."
        parser = OllamaResponseParser()

        with pytest.raises(OllamaExtractionError):
            parser.parse_response(response_text)

    def test_parse_empty_response(self) -> None:
        """Test error when response is empty."""
        parser = OllamaResponseParser()

        with pytest.raises(OllamaExtractionError):
            parser.parse_response("")

    def test_validate_and_convert_valid_soap(
        self,
        valid_soap_dict: dict,
    ) -> None:
        """Test validation and conversion to SOAPNote model."""
        parser = OllamaResponseParser()

        soap_note = parser.validate_and_convert(valid_soap_dict)

        assert isinstance(soap_note, SOAPNote)
        assert soap_note.subjective.chief_complaint == "Fever"
        assert soap_note.assessment.primary_diagnosis == "Acute pharyngitis"

    def test_validate_and_convert_missing_required_field(self) -> None:
        """Test error when required field is missing."""
        invalid_dict = {
            "subjective": {
                "chief_complaint": "Fever",
                # Missing required fields (history_present_illness, past_medical_history)
            },
        }
        parser = OllamaResponseParser()

        with pytest.raises(OllamaExtractionError):
            parser.validate_and_convert(invalid_dict)

    def test_fix_trailing_commas(self) -> None:
        """Test fixing JSON with trailing commas."""
        json_with_trailing_comma = '{"key": "value",}'
        parser = OllamaResponseParser()

        result = parser._parse_json_string(json_with_trailing_comma)  # pyright: ignore[reportPrivateUsage]

        assert result == {"key": "value"}


class TestSOAPModels:
    """Tests for SOAP Pydantic models."""

    def test_soap_note_creation(self) -> None:
        """Test creating SOAPNote instance with English field names."""
        data = {
            "subjective": {
                "chief_complaint": "Headache",
                "history_present_illness": "Persistent headache",
                "past_medical_history": "Migraine history",
            },
            "objective": {
                "vital_signs": "BP normal",
                "physical_exam": "No abnormalities",
            },
            "assessment": {
                "differential_diagnoses": ["Migraine", "Tension headache"],
                "primary_diagnosis": "Chronic migraine",
            },
            "plan": {
                "treatment": "Prophylactic medication",
                "follow_up": "Follow-up in 4 weeks",
                "studies": [],
            },
        }

        soap_note = SOAPNote(**data)

        assert soap_note.subjective.chief_complaint == "Headache"
        assert len(soap_note.assessment.differential_diagnoses) == 2

    def test_soap_to_dict(self) -> None:
        """Test converting SOAPNote back to dict."""
        data = {
            "subjective": {
                "chief_complaint": "Cough",
                "history_present_illness": "Dry cough",
                "past_medical_history": "No history",
            },
            "objective": {
                "vital_signs": "Normal",
                "physical_exam": "Clear lungs",
            },
            "assessment": {
                "differential_diagnoses": ["URI", "Allergies"],
                "primary_diagnosis": "Common cold",
            },
            "plan": {
                "treatment": "Rest and fluids",
                "follow_up": "Monitor symptoms",
                "studies": [],
            },
        }

        soap_note = SOAPNote(**data)
        result = soap_note.to_dict()

        assert result["subjective"]["chief_complaint"] == "Cough"
        assert result["plan"]["treatment"] == "Rest and fluids"

    def test_soap_completeness_check(self) -> None:
        """Test completeness validation with whitespace-only fields."""
        data = {
            "subjective": {
                "chief_complaint": "   ",  # Whitespace only
                "history_present_illness": "Description",
                "past_medical_history": "History",
            },
            "objective": {
                "vital_signs": "Normal",
                "physical_exam": "Good",
            },
            "assessment": {
                "differential_diagnoses": [],
                "primary_diagnosis": "Diagnosis",
            },
            "plan": {
                "treatment": "Plan",
                "follow_up": "Follow-up",
                "studies": [],
            },
        }

        soap_note = SOAPNote(**data)
        errors = soap_note.validate_completeness()

        # Completeness check should flag whitespace-only content
        assert len(errors) > 0
        assert any("chief_complaint" in e for e in errors)


@pytest.mark.skip(reason="LLMClient refactored - old Ollama-specific API removed (http_client, base_url, model params)")
class TestOllamaClient:
    """Tests for refactored OllamaClient.

    DEPRECATED: LLMClient was refactored to be provider-agnostic.
    Old Ollama-specific API removed:
      - __init__(base_url, model, http_client) parameters
      - base_url, model, timeout attributes
      - HTTP client dependency injection

    These tests need rewriting to test the new LLMClient API which uses
    provider configuration from policy.yaml instead of constructor parameters.
    """

    def test_client_initialization(self) -> None:
        """Test client initialization with defaults."""
        client = OllamaClient()

        assert client.base_url == "http://localhost:11434"
        assert client.model == "mistral"
        assert client.timeout == 120

    def test_client_with_custom_params(self) -> None:
        """Test client initialization with custom parameters."""
        # DEPRECATED: Old API (base_url, model, timeout) no longer exists in LLMClient
        client = OllamaClient(  # type: ignore[call-arg]
            base_url="http://custom:11434",  # type: ignore[call-arg]
            model="custom-model",  # type: ignore[call-arg]
            timeout=300,  # type: ignore[call-arg]
        )

        assert client.base_url == "http://custom:11434"  # type: ignore[attr-defined]
        assert client.model == "custom-model"  # type: ignore[attr-defined]
        assert client.timeout == 300  # type: ignore[attr-defined]

    def test_client_with_dependency_injection(self) -> None:
        """Test client with injected dependencies."""
        mock_http = Mock()
        mock_builder = Mock(spec=OllamaPromptBuilder)
        mock_parser = Mock(spec=OllamaResponseParser)

        # DEPRECATED: http_client parameter no longer exists in LLMClient
        client = OllamaClient(
            http_client=mock_http,  # type: ignore[call-arg]
            prompt_builder=mock_builder,
            response_parser=mock_parser,
        )

        assert client.http_client is mock_http  # type: ignore[attr-defined]
        assert client.prompt_builder is mock_builder
        assert client.response_parser is mock_parser

    def test_extract_soap_success(self) -> None:
        """Test successful SOAP extraction."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": '{"subjective": {"chief_complaint": "Test", "history_present_illness": "Test", "past_medical_history": "Test"}, "objective": {"vital_signs": "Test", "physical_exam": "Test"}, "assessment": {"differential_diagnoses": [], "primary_diagnosis": "Test"}, "plan": {"treatment": "Test", "follow_up": "Test", "studies": []}}'
        }

        mock_http = Mock()
        mock_http.post.return_value = mock_response

        mock_builder = Mock(spec=OllamaPromptBuilder)
        mock_builder.load_system_prompt.return_value = "System prompt"
        mock_builder.build_user_prompt.return_value = "User prompt"

        # DEPRECATED: http_client parameter no longer exists in LLMClient
        client = OllamaClient(
            http_client=mock_http,  # type: ignore[call-arg]
            prompt_builder=mock_builder,
        )

        result = client.extract_soap("Test transcription")

        assert isinstance(result, dict)
        assert "subjective" in result
        mock_http.post.assert_called_once()

    def test_extract_soap_http_error(self) -> None:
        """Test error handling for HTTP failures."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Server error"

        mock_http = Mock()
        mock_http.post.return_value = mock_response

        mock_builder = Mock(spec=OllamaPromptBuilder)
        mock_builder.load_system_prompt.return_value = "System"
        mock_builder.build_user_prompt.return_value = "User"

        # DEPRECATED: http_client parameter no longer exists in LLMClient
        client = OllamaClient(
            http_client=mock_http,  # type: ignore[call-arg]
            prompt_builder=mock_builder,
        )

        with pytest.raises(OllamaExtractionError):
            client.extract_soap("Test")

    def test_extract_soap_json_parse_error(self) -> None:
        """Test error handling for JSON parsing failures."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Not JSON"}

        mock_http = Mock()
        mock_http.post.return_value = mock_response

        mock_builder = Mock(spec=OllamaPromptBuilder)
        mock_builder.load_system_prompt.return_value = "System"
        mock_builder.build_user_prompt.return_value = "User"

        # DEPRECATED: http_client parameter no longer exists in LLMClient
        client = OllamaClient(
            http_client=mock_http,  # type: ignore[call-arg]
            prompt_builder=mock_builder,
        )

        with pytest.raises(OllamaExtractionError):
            client.extract_soap("Test")

    def test_extract_soap_validated(self) -> None:
        """Test extract_soap_validated returns SOAPNote model."""
        valid_response = {
            "subjective": {
                "chief_complaint": "Fever",
                "history_present_illness": "3 days",
                "past_medical_history": "None",
            },
            "objective": {
                "vital_signs": "38C",
                "physical_exam": "Red throat",
            },
            "assessment": {
                "differential_diagnoses": ["Strep"],
                "primary_diagnosis": "Pharyngitis",
            },
            "plan": {
                "treatment": "Antibiotics",
                "follow_up": "7 days",
                "studies": [],
            },
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": json.dumps(valid_response)}

        mock_http = Mock()
        mock_http.post.return_value = mock_response

        mock_builder = Mock(spec=OllamaPromptBuilder)
        mock_builder.load_system_prompt.return_value = "System"
        mock_builder.build_user_prompt.return_value = "User"

        # DEPRECATED: http_client parameter no longer exists in LLMClient
        client = OllamaClient(
            http_client=mock_http,  # type: ignore[call-arg]
            prompt_builder=mock_builder,
        )

        result = client.extract_soap_validated("Test")

        assert isinstance(result, SOAPNote)
        assert result.subjective.chief_complaint == "Fever"
