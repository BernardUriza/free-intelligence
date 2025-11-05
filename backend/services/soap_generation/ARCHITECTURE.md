# SOAP Generation Package - Architecture Deep Dive

## Directory Structure

```
backend/services/
├── soap_generation_service.py          ← Backward-compatible wrapper (DEPRECATED)
└── soap_generation/                    ← Modern modular package
    ├── __init__.py                     ← Public API exports
    ├── service.py                      ← Main orchestrator
    ├── reader.py                       ← HDF5 I/O
    ├── ollama_client.py                ← LLM HTTP client
    ├── soap_builder.py                 ← Model construction
    ├── completeness.py                 ← Scoring logic
    ├── defaults.py                     ← Fallback structures
    ├── tests.py                        ← Example tests
    ├── README.md                       ← Usage guide
    └── ARCHITECTURE.md                 ← This file
```

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│  Client Code                                                 │
│  (API endpoint, worker, etc.)                                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │ SOAPGenerationService      │ ◄─── Orchestrator
        │ (service.py)               │      (Single Responsibility)
        │                            │
        │ Main workflow:             │
        │ 1. Read transcription      │
        │ 2. Extract SOAP            │
        │ 3. Build models            │
        │ 4. Calculate score         │
        │ 5. Return SOAPNote         │
        └────────┬───────────┬───────┘
                 │           │
        ┌────────▼──┐  ┌─────▼──────────┐
        │ Reader    │  │ OllamaClient   │
        │           │  │                │
        │ HDF5 I/O  │  │ HTTP Request   │
        │ (disk I/O)│  │ JSON parsing   │
        └────────┬──┘  └─────┬──────────┘
                 │           │
        ┌────────▼───────────▼────────┐
        │ SOAPBuilder                 │
        │                             │
        │ - Subjetivo construction    │
        │ - Objetivo construction     │
        │ - Analisis construction     │
        │ - Plan construction         │
        │ - Type conversions          │
        └────────────┬────────────────┘
                     │
        ┌────────────▼──────────────┐
        │ CompletenessCalculator    │
        │                           │
        │ Score: 0-100              │
        └────────────┬──────────────┘
                     │
        ┌────────────▼──────────────┐
        │ SOAPNote (Pydantic)       │
        │                           │
        │ Complete medical data     │
        │ Fully typed & validated   │
        └───────────────────────────┘
```

## Module Responsibilities

### service.py - Orchestration
**Responsibility:** Coordinate the entire workflow

```python
SOAPGenerationService
├── __init__(h5_path, ollama_base_url, ollama_model)
├── generate_soap_for_job(job_id) → SOAPNote
└── _extract_soap_data(transcription) → dict
    ├── Delegates to TranscriptionReader
    ├── Delegates to OllamaClient
    ├── Delegates to SOAPBuilder
    ├── Delegates to CompletenessCalculator
    └── Handles failures gracefully
```

**Properties:**
- Pure orchestration (no business logic)
- Error aggregation & logging
- Graceful fallback to defaults
- Clear separation of concerns

### reader.py - I/O (HDF5)
**Responsibility:** Read transcriptions from HDF5 storage

```python
TranscriptionReader
├── __init__(h5_path)
├── read(job_id) → str
├── _extract_texts(chunks_dataset) → list[str]
└── Custom Exception: TranscriptionReadError
```

**Concerns:**
- HDF5 file access
- Chunk concatenation
- Bytes ↔ UTF-8 encoding
- Error handling (missing chunks, I/O errors)

**Why Separate?**
- Isolates file I/O from business logic
- Easy to mock for testing
- Reusable in other contexts
- Single responsibility: reading data

### ollama_client.py - LLM Integration
**Responsibility:** HTTP communication with Ollama LLM service

```python
OllamaClient
├── __init__(base_url, model, timeout)
├── extract_soap(transcription) → dict
├── _parse_json_from_response(response_text) → dict
├── _get_system_prompt() → str
└── Custom Exception: OllamaExtractionError
```

**Concerns:**
- HTTP POST requests
- JSON response parsing
- System prompt engineering
- Error handling (network, JSON parsing, HTTP errors)

**Why Separate?**
- Encapsulates external service dependency
- Easy to swap LLM backend (add alternative client)
- Testable via mocking requests
- Handles language-agnostic extraction

### soap_builder.py - Model Construction
**Responsibility:** Build Pydantic models from extracted JSON

```python
SOAPBuilder
├── build(job_id, soap_data) → (Subjetivo, Objetivo, Analisis, Plan)
├── build_note(job_id, ..., completeness) → SOAPNote
├── _build_subjetivo(soap_data) → Subjetivo
├── _build_objetivo(soap_data) → Objetivo
├── _build_analisis(soap_data) → Analisis
├── _build_plan(soap_data) → Plan
├── _build_diagnosticos_diferenciales(diferenciales_raw) → list
├── _to_int(val) → int | None
├── _to_float(val) → float | None
└── Custom Exception: SOAPBuildError
```

**Concerns:**
- Pydantic model instantiation
- Type conversions (str → int, str → float)
- Default value assignment
- Nested structure handling
- Validation error handling

**Why Separate?**
- Complex transformation logic in one place
- Easy to test type conversions
- Handles ambiguous data gracefully
- Clear error messages for validation

### completeness.py - Scoring
**Responsibility:** Calculate SOAP note completeness score

```python
CompletenessCalculator
├── calculate(subjetivo, objetivo, analisis, plan) → float
└── SCORE_CONFIG: dict (weights for each section)
```

**Scoring System:**
```
motivo_consulta         : 15 points
historia_actual         : 10 points
signos_vitales          : 15 points
exploracion_fisica      : 10 points
diagnostico_principal   : 20 points
diagnosticos_diferenciales: 10 points
tratamiento_farmacologico: 15 points
─────────────────────────────────────
Total                   : 100 points (max)
```

**Why Separate?**
- Pure function (no state)
- Easy to adjust weights
- Testable in isolation
- Reusable scoring algorithm

### defaults.py - Fallback Data
**Responsibility:** Provide default structures for error recovery

```python
get_default_soap_structure() → dict
```

**Why Separate?**
- Central place for defaults
- Easy to maintain structure consistency
- Used when Ollama fails

## Design Patterns Used

### 1. Single Responsibility Principle (SRP)
Each module has exactly one reason to change:
- **reader.py**: Changes to HDF5 schema or I/O strategy
- **ollama_client.py**: Changes to Ollama API or LLM backend
- **soap_builder.py**: Changes to SOAP model structure
- **completeness.py**: Changes to scoring weights
- **service.py**: Changes to workflow orchestration

### 2. Dependency Injection
Service accepts dependencies:
```python
service = SOAPGenerationService(
    h5_path="storage/diarization.h5",
    ollama_base_url="http://localhost:11434",
    ollama_model="mistral"
)
```

Makes testing easier and configuration flexible.

### 3. Custom Exceptions
Domain-specific error handling:
```python
try:
    text = reader.read(job_id)
except TranscriptionReadError:
    # Handle HDF5 errors
    pass

try:
    soap_data = llm.extract_soap(text)
except OllamaExtractionError:
    # Handle LLM errors, fallback to defaults
    pass
```

### 4. Static Methods for Pure Functions
Pure logic as static methods:
```python
# Stateless utility functions
score = CompletenessCalculator.calculate(...)
soap_data = get_default_soap_structure()
int_val = SOAPBuilder._to_int(value)
```

### 5. Factory-like Builder
SOAPBuilder acts as factory for SOAP models:
```python
subjetivo, objetivo, analisis, plan = SOAPBuilder.build(
    job_id, soap_data
)
soap_note = SOAPBuilder.build_note(
    job_id, subjetivo, objetivo, analisis, plan, completeness
)
```

## Error Handling Strategy

```
┌─────────────────────────────────────────┐
│ Client calls service.generate_soap_for_job
└──────────────────┬──────────────────────┘
                   │
        ┌──────────▼──────────┐
        │ TranscriptionReader │
        └──────────┬──────────┘
                   │
        ┌──────────▼─────────────────┐
        │ TranscriptionReadError ◄───┤
        │ → Re-raise to client      │
        └──────────────────────────┘
                   │
        ┌──────────▼──────────┐
        │ OllamaClient.extract│
        └──────────┬──────────┘
                   │
        ┌──────────▼─────────────────┐
        │ OllamaExtractionError       │
        │ → Caught, use defaults ◄───┤
        │   Continue pipeline        │
        └──────────────────────────┘
                   │
        ┌──────────▼──────────┐
        │ SOAPBuilder.build   │
        └──────────┬──────────┘
                   │
        ┌──────────▼─────────────────┐
        │ SOAPBuildError ◄───────────┤
        │ → Re-raise to client        │
        └──────────────────────────┘
                   │
                   ▼
        Return SOAPNote or Exception
```

**Philosophy:**
- Reader errors → Propagate (data unavailable)
- Ollama errors → Recover gracefully (use defaults)
- Builder errors → Propagate (invalid models)

## Extensibility Points

### Alternative HDF5 Stores
Replace `TranscriptionReader`:
```python
class DatabaseTranscriptionReader:
    def read(self, job_id: str) -> str:
        # Read from SQL database instead
```

### Alternative LLM Backends
Create new clients alongside `OllamaClient`:
```python
class ClaudeClient:
    def extract_soap(self, transcription: str) -> dict:
        # Use Claude API instead

class OpenAIClient:
    def extract_soap(self, transcription: str) -> dict:
        # Use OpenAI API instead
```

### Custom Scoring
Extend `CompletenessCalculator`:
```python
class AdvancedCompletenessCalculator:
    @staticmethod
    def calculate(...) -> float:
        # Custom weighted scoring with clinical relevance
```

## Testing Strategy

### Unit Testing
Test each module in isolation with mocks:
```python
# Mock HDF5
@patch("reader.h5py.File")
def test_reader(mock_h5):
    ...

# Mock HTTP
@patch("ollama_client.requests.post")
def test_ollama(mock_post):
    ...

# Direct testing (no mocks)
def test_scoring():
    score = CompletenessCalculator.calculate(...)
```

### Integration Testing
Test workflows with real dependencies:
```python
@pytest.mark.integration
def test_full_pipeline(h5_file, ollama_server):
    service = SOAPGenerationService(h5_file, ...)
    result = service.generate_soap_for_job(job_id)
```

### Error Scenarios
Test graceful degradation:
```python
def test_missing_transcription():
    # Reader fails → service raises TranscriptionReadError

def test_ollama_failure():
    # Ollama fails → service uses defaults, continues

def test_invalid_soap_data():
    # Builder fails → service raises SOAPBuildError
```

## Performance Characteristics

| Component | Latency | Bottleneck |
|-----------|---------|-----------|
| Reader | ~100ms | Disk I/O, HDF5 parsing |
| OllamaClient | ~30-60s | Network, LLM inference |
| SOAPBuilder | ~10ms | Pydantic validation |
| CompletenessCalculator | ~1ms | Pure computation |
| **Total** | **~30-60s** | **Ollama LLM** |

## Future Evolution

### Phase 1: Current (MVP)
- Single LLM backend (Ollama)
- Synchronous processing
- Local HDF5 storage

### Phase 2: Scalability
- [ ] Async/streaming Ollama responses
- [ ] Caching layer (Redis) for repeated jobs
- [ ] Batch processing support
- [ ] Message queue integration (Celery)

### Phase 3: Intelligence
- [ ] Plugin system for alternative LLM backends
- [ ] Multi-model consensus (multiple LLMs)
- [ ] Fine-tuned models for domain-specific tasks
- [ ] Prompt optimization via feedback

### Phase 4: Enterprise
- [ ] Database persistence
- [ ] Audit trail & compliance
- [ ] Multi-tenant support
- [ ] API versioning
- [ ] Rate limiting & quotas
