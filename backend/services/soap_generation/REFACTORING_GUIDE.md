# Ollama Client Refactoring Guide

## Overview

The Ollama client for SOAP extraction has been completely refactored into a modern, modular architecture with separated concerns, dependency injection, and comprehensive type safety using Pydantic.

## Architecture

### Component Separation

The refactored implementation divides responsibilities across specialized modules:

```
ollama_client.py          → HTTP orchestration & public API
├── prompt_builder.py     → System & user prompt management
├── response_parser.py    → JSON extraction & validation
└── soap_models.py        → Pydantic data models for SOAP structure
```

## Files Overview

### 1. `soap_models.py` - Pydantic Data Models

Defines the expected SOAP note structure with validation:

```python
from backend.services.soap_generation.soap_models import SOAPNote

# Validates structure automatically
soap = SOAPNote(**parsed_json)
```

**Classes:**
- `SubjetiveData`: Patient-reported information (motivo_consulta, historia_actual, antecedentes)
- `ObjetivoData`: Clinician observations (signos_vitales, examen_fisico)
- `AnalisisData`: Assessment (diagnosticos_diferenciales, diagnostico_principal)
- `PlanData`: Treatment plan (tratamiento, seguimiento, estudios)
- `SOAPNote`: Complete note with all four sections

**Features:**
- Auto-converts string values to lists where needed (e.g., `diagnosticos_diferenciales`)
- `validate_completeness()`: checks for empty/whitespace-only fields
- `to_dict()`: serialization support

### 2. `prompt_builder.py` - Prompt Management

Loads and builds prompts from external files:

```python
from backend.services.soap_generation.prompt_builder import OllamaPromptBuilder

builder = OllamaPromptBuilder()
system_prompt = builder.load_system_prompt()
user_prompt = builder.build_user_prompt(transcription)
```

**Features:**
- Loads prompts from `prompts/` directory
- In-memory caching to avoid repeated file I/O
- External prompt files (not hardcoded in Python)
- `clear_cache()` for testing or reload scenarios

**Prompt File:** `prompts/medical_soap_extraction.txt`

### 3. `response_parser.py` - JSON Extraction & Validation

Extracts JSON from Ollama responses and validates against SOAP model:

```python
from backend.services.soap_generation.response_parser import OllamaResponseParser

parser = OllamaResponseParser()
soap_dict = parser.parse_response(response_text)

# With strict validation
soap_dict = parser.parse_response(response_text, strict=True)

# Direct conversion to model
soap_note = parser.validate_and_convert(soap_dict)
```

**Features:**
- Multiple extraction strategies:
  1. Simple bracket matching (fastest)
  2. Regex-based detection for nested JSON
  3. Markdown code block extraction
  4. Automatic trailing comma fixes
- Pydantic validation with clear error messages
- Comprehensive error handling and logging

### 4. `ollama_client.py` - Main Client (Refactored)

Modern HTTP client with dependency injection:

```python
from backend.services.soap_generation.ollama_client import OllamaClient

# Default usage (no changes needed from old API)
client = OllamaClient()
soap_dict = client.extract_soap(transcription)

# With type safety
soap_note = client.extract_soap_validated(transcription)

# Custom dependencies for testing
client = OllamaClient(
    http_client=mock_http,
    prompt_builder=custom_builder,
    response_parser=custom_parser,
)
```

**Key Changes:**
- Dependencies injected via constructor
- Sensible defaults (requests, OllamaPromptBuilder, OllamaResponseParser)
- Two extraction methods:
  - `extract_soap()`: Returns `dict[str, Any]` (backward compatible)
  - `extract_soap_validated()`: Returns `SOAPNote` (type-safe)
- Protocol-based HTTP client interface (`HttpClient`)

## Migration Guide

### For Existing Code

The new client is **backward compatible**:

```python
# Old code still works
client = OllamaClient()
result = client.extract_soap(transcription)
assert isinstance(result, dict)
```

### For New Code

Prefer the type-safe version:

```python
# New recommendation
client = OllamaClient()
soap_note = client.extract_soap_validated(transcription)

# Access fields with type hints
print(soap_note.subjetivo.motivo_consulta)
print(soap_note.plan.tratamiento)

# Serialize to dict if needed
soap_dict = soap_note.to_dict()
```

## Error Handling

All extraction errors inherit from `OllamaExtractionError`:

```python
from backend.services.soap_generation.response_parser import OllamaExtractionError

try:
    soap = client.extract_soap_validated(transcription)
except OllamaExtractionError as e:
    # Handle extraction/validation failures
    logger.error(f"SOAP extraction failed: {e}")
```

## Testing

Comprehensive test suite with 24 tests covering:

```bash
# Run all tests
python3 -m pytest backend/tests/test_ollama_client.py -v

# Test specific component
python3 -m pytest backend/tests/test_ollama_client.py::TestOllamaPromptBuilder -v
python3 -m pytest backend/tests/test_ollama_client.py::TestOllamaResponseParser -v
python3 -m pytest backend/tests/test_ollama_client.py::TestSOAPModels -v
python3 -m pytest backend/tests/test_ollama_client.py::TestOllamaClient -v
```

**Test Categories:**
- Prompt loading, caching, formatting
- JSON extraction from various formats
- SOAP model validation
- HTTP client orchestration
- Error scenarios

## Logging

Structured logging integrated throughout:

```python
logger.info("SOAP_EXTRACTED_FROM_OLLAMA", model="mistral", response_length=1234)
logger.warning("OLLAMA_COMPLETENESS_WARNING", errors="field1, field2")
logger.error("SOAP_VALIDATION_FAILED", errors=[...])
```

## Configuration

All configuration is environment-based (no hardcoded values):

```python
OLLAMA_BASE_URL = "http://localhost:11434"  # Configurable
OLLAMA_MODEL = "mistral"                     # Configurable
OLLAMA_TIMEOUT = 120                         # Configurable
```

Override via constructor:

```python
client = OllamaClient(
    base_url="http://custom-ollama:11434",
    model="llama2",
    timeout=300,
)
```

## Benefits of Refactoring

✅ **Separation of Concerns**: Each class has a single responsibility
✅ **Testability**: All components can be tested in isolation
✅ **Type Safety**: Pydantic models catch structural errors early
✅ **Dependency Injection**: Easy to mock dependencies for testing
✅ **Maintainability**: Clear interfaces and responsibilities
✅ **Extensibility**: Can swap components without changing main client
✅ **Backward Compatibility**: Existing code continues to work
✅ **External Configuration**: Prompts loaded from files, not hardcoded
✅ **Error Clarity**: Pydantic validation with detailed error messages
✅ **Performance**: Prompt caching, efficient JSON extraction

## Future Enhancements

- [ ] Async support with `httpx`
- [ ] Custom prompt templates per model
- [ ] Response streaming support
- [ ] Retry logic with exponential backoff
- [ ] Request/response caching
- [ ] OpenTelemetry instrumentation
- [ ] Schema versioning for SOAP model evolution
