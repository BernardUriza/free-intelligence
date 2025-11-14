"""Usage examples for the refactored Ollama SOAP extraction client.

Demonstrates practical patterns for integrating the modern client
into your medical consultation processing pipeline.
"""

from __future__ import annotations

from typing import List, Optional

# ============================================================================
# Example 1: Basic Usage (Backward Compatible)
# ============================================================================


def example_basic_usage() -> None:
    """Simple extraction returning a dictionary."""
    from backend.services.soap_generation.ollama_client import OllamaClient

    client = OllamaClient()

    transcription = """
    Patient reports persistent headache for 3 days.
    Pain level 7/10. Associated with nausea.
    Previous history of migraines.
    """

    # Returns dict[str, Any]
    soap_dict = client.extract_soap(transcription)

    print("Subjective:", soap_dict["subjetivo"])
    print("Objective:", soap_dict["objetivo"])
    print("Assessment:", soap_dict["analisis"])
    print("Plan:", soap_dict["plan"])


# ============================================================================
# Example 2: Type-Safe Usage with Pydantic Models
# ============================================================================


def example_type_safe_usage() -> None:
    """Extract with full type safety using Pydantic models."""
    from backend.services.soap_generation.ollama_client import OllamaClient
    from backend.services.soap_generation.soap_models import SOAPNote

    client = OllamaClient()

    transcription = """
    Patient: 45-year-old male with fever (38.5C) for 2 days.
    Complains of sore throat and cough.
    No significant past medical history.
    Examination shows red pharynx, no exudate.
    """

    # Returns SOAPNote instance with full type hints
    soap_note: SOAPNote = client.extract_soap_validated(transcription)

    # Access with IDE autocomplete
    print(f"Chief Complaint: {soap_note.subjetivo.motivo_consulta}")
    print(f"Temperature: {soap_note.objetivo.signos_vitales}")
    print(f"Primary Diagnosis: {soap_note.analisis.diagnostico_principal}")
    print(f"Treatment: {soap_note.plan.tratamiento}")

    # Validate completeness
    errors = soap_note.validate_completeness()
    if errors:
        print(f"Incomplete fields: {errors}")

    # Serialize back to dict if needed
    _result_dict = soap_note.to_dict()


# ============================================================================
# Example 3: Error Handling
# ============================================================================


def example_error_handling() -> None:
    """Handle extraction errors gracefully."""
    from backend.logger import get_logger
    from backend.services.soap_generation.ollama_client import OllamaClient
    from backend.services.soap_generation.response_parser import OllamaExtractionError

    logger = get_logger(__name__)
    client = OllamaClient()

    try:
        _soap_note = client.extract_soap_validated("Some medical transcription")
    except OllamaExtractionError as e:
        logger.error(
            "SOAP_EXTRACTION_FAILED",
            error=str(e),
            type=type(e).__name__,
        )
        # Fallback: create empty/partial SOAP note
        return None


# ============================================================================
# Example 4: Custom Configuration
# ============================================================================


def example_custom_configuration() -> None:
    """Use custom Ollama endpoints and models."""
    from backend.services.soap_generation.ollama_client import OllamaClient

    # Connect to different Ollama instance
    client = OllamaClient(
        base_url="http://ollama-server.lan:11434",
        model="llama2",  # Different model
        timeout=300,  # Longer timeout for larger models
    )

    _result = client.extract_soap("transcription text")


# ============================================================================
# Example 5: Dependency Injection for Testing
# ============================================================================


def example_testing_with_mocks() -> None:
    """Mock dependencies for unit testing."""
    from backend.services.soap_generation.ollama_client import OllamaClient

    from unittest.mock import Mock

    # Create mock HTTP client
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "response": """{
            "subjetivo": {
                "motivo_consulta": "Fever",
                "historia_actual": "3 days",
                "antecedentes": "None"
            },
            "objetivo": {
                "signos_vitales": "38C",
                "examen_fisico": "Red throat"
            },
            "analisis": {
                "diagnosticos_diferenciales": ["Strep"],
                "diagnostico_principal": "Pharyngitis"
            },
            "plan": {
                "tratamiento": "Antibiotics",
                "seguimiento": "7 days",
                "estudios": []
            }
        }"""
    }

    mock_http_client = Mock()
    mock_http_client.post.return_value = mock_response

    # Inject mocked client
    client = OllamaClient(http_client=mock_http_client)
    result = client.extract_soap("test")

    assert result["subjetivo"]["motivo_consulta"] == "Fever"


# ============================================================================
# Example 6: Pipeline Integration
# ============================================================================


def example_pipeline_integration(
    audio_file_path: str,
) -> dict[str, Optional[str]]:
    """Integration in a full processing pipeline."""
    from backend.logger import get_logger
    from backend.services.soap_generation.ollama_client import OllamaClient
    from backend.services.soap_generation.response_parser import OllamaExtractionError

    logger = get_logger(__name__)

    # Step 1: Transcribe audio (pseudo-code)
    # transcription = whisper_service.transcribe(audio_file_path)

    # Step 2: Extract SOAP
    client = OllamaClient()

    try:
        # Use type-safe extraction
        soap_note = client.extract_soap_validated("transcription text")

        # Step 3: Validate completeness
        errors = soap_note.validate_completeness()
        if errors:
            logger.warning(
                "INCOMPLETE_SOAP",
                errors=errors,
                file=audio_file_path,
            )

        # Step 4: Store result
        return {
            "file": audio_file_path,
            "chief_complaint": soap_note.subjetivo.motivo_consulta,
            "diagnosis": soap_note.analisis.diagnostico_principal,
            "plan": soap_note.plan.tratamiento,
        }

    except OllamaExtractionError as e:
        logger.error(
            "PIPELINE_FAILED",
            error=str(e),
            file=audio_file_path,
        )
        return {
            "file": audio_file_path,
            "error": str(e),
            "chief_complaint": None,
        }


# ============================================================================
# Example 7: Batch Processing
# ============================================================================


def example_batch_processing(transcriptions: List[str]) -> list[dict]:
    """Process multiple transcriptions efficiently."""
    from backend.services.soap_generation.ollama_client import OllamaClient
    from backend.services.soap_generation.response_parser import OllamaExtractionError

    client = OllamaClient()
    results = []

    for i, transcription in enumerate(transcriptions):
        try:
            soap_note = client.extract_soap_validated(transcription)
            results.append(
                {
                    "index": i,
                    "status": "success",
                    "diagnosis": soap_note.analisis.diagnostico_principal,
                }
            )
        except OllamaExtractionError as e:
            results.append(
                {
                    "index": i,
                    "status": "failed",
                    "error": str(e),
                }
            )

    return results


# ============================================================================
# Example 8: Using Response Parser Directly
# ============================================================================


def example_response_parser_direct() -> None:
    """Use the parser component independently."""
    from backend.services.soap_generation.response_parser import OllamaResponseParser

    parser = OllamaResponseParser()

    # Raw response from Ollama
    raw_response = """
    Based on the transcription, here's the SOAP note:

    {
        "subjetivo": {
            "motivo_consulta": "Chest pain",
            "historia_actual": "Sudden onset",
            "antecedentes": "Hypertension"
        },
        "objetivo": {
            "signos_vitales": "BP elevated",
            "examen_fisico": "Normal cardiac exam"
        },
        "analisis": {
            "diagnosticos_diferenciales": ["MI", "Anxiety"],
            "diagnostico_principal": "Acute coronary syndrome"
        },
        "plan": {
            "tratamiento": "Hospital admission",
            "seguimiento": "Cardiac monitoring",
            "estudios": ["EKG", "Troponin"]
        }
    }

    The patient should be admitted immediately.
    """

    # Parser extracts JSON even with surrounding text
    soap_dict = parser.parse_response(raw_response)
    print(soap_dict)


# ============================================================================
# Example 9: Prompt Builder Direct Usage
# ============================================================================


def example_prompt_builder_usage() -> None:
    """Use prompt builder to manage prompts."""
    from backend.services.soap_generation.prompt_builder import OllamaPromptBuilder

    builder = OllamaPromptBuilder()

    # Load system prompt
    system_prompt = builder.load_system_prompt()
    print(f"System prompt loaded: {len(system_prompt)} chars")

    # Build user prompt with medical transcription
    user_prompt = builder.build_user_prompt("Patient reports fever and cough")
    print(f"User prompt: {user_prompt}")

    # Cache is automatic - loading again is fast
    system_prompt_2 = builder.load_system_prompt()
    assert system_prompt == system_prompt_2


# ============================================================================
# Example 10: Async Usage (Future)
# ============================================================================


async def example_async_usage_future() -> None:
    """
    Future example: async support with httpx.

    This is not yet implemented but shows the intended API.
    """
    # from backend.services.soap_generation.ollama_client_async import (
    #     OllamaClientAsync,
    # )
    #
    # async with OllamaClientAsync() as client:
    #     soap = await client.extract_soap_validated(transcription)


if __name__ == "__main__":
    # Run examples (replace with actual usage)
    print("=== Example 1: Basic Usage ===")
    # example_basic_usage()

    print("\n=== Example 2: Type-Safe Usage ===")
    # example_type_safe_usage()

    print("\n=== Example 5: Testing with Mocks ===")
    example_testing_with_mocks()

    print("\nAll examples completed!")
