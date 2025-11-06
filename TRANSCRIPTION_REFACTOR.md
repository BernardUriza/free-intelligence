# Transcription Service Refactor - Clean Architecture Guide

## Overview

The transcription service has been refactored into a clean, modular architecture with:
- ✅ Modern Python typing (PEP 604: `str | None` instead of `Optional[str]`)
- ✅ Proper separation of concerns (whisper, storage, services)
- ✅ Comprehensive pytest test suite with mocking
- ✅ Type checking automation (MyPy, Pyright, Ruff)
- ✅ Full docstrings with examples

## Folder Structure

```
backend/
├── whisper/
│   ├── __init__.py                 # Clean exports
│   └── whisper_utils.py            # Whisper transcription logic
├── storage/
│   ├── __init__.py                 # Clean exports
│   ├── audio_storage.py            # Audio file storage
│   ├── corpus_ops.py               # HDF5 corpus operations
│   └── ...
├── services/
│   └── transcription_service.py    # Service orchestration (REFACTORED)
├── api/
│   └── transcribe.py               # FastAPI endpoint (UPDATED)
└── tests/
    └── test_transcription_service.py # Comprehensive pytest suite (NEW)
```

## Key Improvements

### 1. Modern Python Typing (PEP 604)

**Before:**
```python
from typing import Optional, Dict, Any

def transcribe(language: Optional[str] = None) -> Dict[str, Any]:
    metadata: Optional[dict[str, Any]] = None
```

**After:**
```python
def transcribe(language: str | None = None) -> dict[str, Any]:
    metadata: dict[str, Any] | None = None
```

### 2. Proper Module Organization

**Whisper package** (`backend/whisper/`):
- `whisper_utils.py`: Core transcription logic
  - `is_whisper_available()`: Check if Whisper is installed
  - `get_whisper_model()`: Lazy-load singleton model
  - `transcribe_audio()`: Main transcription function
  - `convert_audio_to_wav()`: Format conversion
- `__init__.py`: Clean public API

**Storage module** (`backend/storage/`):
- Already established (no changes needed)
- Audio file storage with session organization
- SHA256 hashing and manifests

**Service layer** (`backend/services/`):
- `TranscriptionService`: Orchestrates audio validation, storage, and transcription
- High-level API for controllers/endpoints

### 3. Comprehensive Docstrings

All functions include:
- Purpose and behavior
- Args with types and descriptions
- Returns with dict/object structure
- Raises documentation
- Examples and notes

```python
def transcribe_audio(
    audio_path: Path,
    language: str | None = None,
    vad_filter: bool = True,
) -> dict[str, Any]:
    """Transcribe audio file using Whisper.

    Args:
        audio_path: Path to audio file (WAV, MP3, M4A, WEBM supported).
        language: Language code (default: None for auto-detect).
            Examples: "es", "en", "fr".
        vad_filter: Enable Voice Activity Detection filtering (default: True).

    Returns:
        Dict with:
            - text: Full transcription (joined segments)
            - segments: List of segments with timestamps
            - language: Detected or forced language
            - duration: Audio duration in seconds
            - available: Whether transcription succeeded

    Raises:
        ValueError: If transcription fails due to file not found or read error.
    """
```

## Running Tests

### Install Development Dependencies

```bash
pip install -e ".[dev]"
```

This installs:
- pytest >= 7.4.0
- pytest-cov >= 4.1.0
- pytest-asyncio >= 0.21.0
- mypy >= 1.7.0
- ruff >= 0.1.0

### Run All Tests

```bash
pytest backend/tests/test_transcription_service.py -v
```

### Run Specific Test Class

```bash
pytest backend/tests/test_transcription_service.py::TestAudioFileValidation -v
```

### Run Specific Test

```bash
pytest backend/tests/test_transcription_service.py::TestAudioFileValidation::test_validate_audio_file_valid -v
```

### Run with Coverage

```bash
pytest backend/tests/test_transcription_service.py --cov=backend.services.transcription_service --cov-report=term-missing
```

### Run Tests in Watch Mode (auto-rerun on changes)

```bash
pytest-watch backend/tests/test_transcription_service.py -v
```

## Type Checking

### Quick Type Check (Pyright)

```bash
pyright backend/services/transcription_service.py backend/whisper/whisper_utils.py
```

### Full Type Check (MyPy + Pyright + Ruff)

```bash
mypy backend/services/transcription_service.py backend/whisper/whisper_utils.py
pyright backend/
ruff check backend/ --select I,UP,N
```

### Type Check with Configuration

Configuration in `pyproject.toml`:
- MyPy: Strict mode with h5py/faster_whisper exceptions
- Pyright: Standard mode for gradual adoption
- Ruff: Import sorting and upgrade linting

## Test Suite Coverage

### Unit Tests (48+ assertions)

**Session Validation** (4 tests):
- Valid UUID4 format
- Invalid formats (empty, non-UUID)
- None handling

**Audio File Validation** (4 tests):
- Valid files for all supported formats
- Invalid MIME types, extensions, sizes
- Size limit enforcement (100 MB)

**Audio Storage** (3 tests):
- Successful storage with metadata
- Storage error handling
- File path and hash generation

**Audio Conversion** (3 tests):
- Successful WAV conversion
- Conversion failures and exceptions
- ffmpeg unavailability handling

**Transcription** (5 tests):
- Successful transcription
- Graceful degradation when Whisper unavailable
- Auto-detected language
- Error handling

**End-to-End Processing** (4 tests):
- Full workflow integration
- Invalid session ID rejection
- Invalid file type rejection
- Size limit enforcement

**Health Check** (2 tests):
- Status when Whisper available
- Status when Whisper unavailable

### Test Examples

#### Basic Mocking

```python
@patch("backend.services.transcription_service.is_whisper_available")
def test_transcribe_whisper_unavailable(mock_available):
    mock_available.return_value = False

    service = TranscriptionService()
    result = service.transcribe(Path("test.wav"))

    assert result["available"] is False
    assert "(Transcription unavailable" in result["text"]
```

#### Fixture-based Tests

```python
@pytest.fixture
def valid_session_id() -> str:
    return str(uuid4())

def test_save_audio_file(service, valid_session_id):
    with patch("backend.services.transcription_service.save_audio_file") as mock:
        mock.return_value = {
            "file_path": f"storage/audio/{valid_session_id}/123.webm",
            ...
        }
        result = service.save_audio_file(...)
        assert result["file_path"].startswith("storage/audio/")
```

#### Parametrized Tests

```python
@pytest.mark.parametrize(
    "filename,content_type,file_size,error_msg",
    [
        ("test.txt", "text/plain", 1024, "Invalid audio format"),
        ("test.webm", "text/plain", 1024, "Invalid audio format"),
        ("test.exe", "audio/webm", 1024, "Invalid file extension"),
        ("test.webm", "audio/webm", 101 * 1024 * 1024, "exceeds limit"),
    ],
)
def test_validate_audio_file_invalid(service, filename, content_type, size, msg):
    with pytest.raises(ValueError, match=msg):
        service.validate_audio_file(filename, content_type, size)
```

## API Endpoint Updates

### FastAPI Endpoint (`backend/api/transcribe.py`)

```python
from typing import Any  # Modern imports only

@router.post("/api/transcribe")
async def transcribe_audio_endpoint(
    request: Request,
    audio: UploadFile = File(...),
    x_session_id: str | None = Header(None),  # Modern typing
) -> TranscriptionResponse:
    """Upload audio file and get transcription."""
    if not x_session_id:
        raise HTTPException(status_code=400, detail="Missing X-Session-ID header")

    service = get_container().get_transcription_service()
    result = service.process_transcription(
        session_id=x_session_id,
        audio_content=await audio.read(),
        filename=audio.filename or "audio",
        content_type=audio.content_type or "audio/wav",
    )
    return TranscriptionResponse(**result)
```

## Configuration

### Environment Variables

```bash
# Whisper Model Configuration
WHISPER_MODEL_SIZE=small          # small (default), tiny, base, medium, large-v3
WHISPER_COMPUTE_TYPE=int8         # int8 (fastest), float16, float32
WHISPER_DEVICE=cpu                # cpu or cuda
WHISPER_LANGUAGE=None             # None (auto-detect) or language code (e.g., "es")
WHISPER_BEAM_SIZE=5               # 1 (fast), 5 (default), 10+ (accurate)
WHISPER_VAD_FILTER=true           # Voice Activity Detection

# Audio Storage
FI_AUDIO_ROOT=./storage/audio     # Audio file storage path
AUDIO_TTL_DAYS=7                  # Audio file TTL in days

# CPU Optimization (NAS: DS923+ Ryzen R1600)
ASR_CPU_THREADS=3                 # 1 less than available
ASR_NUM_WORKERS=1                 # Single worker for CPU

# ffmpeg Configuration
WHISPER_CACHE_DIR=~/.cache/huggingface  # Model cache directory
```

### Type Checking Config (`pyproject.toml`)

```toml
[tool.mypy]
python_version = "3.12"
warn_return_any = true
check_untyped_defs = true
ignore_missing_imports = true

[[tool.mypy.overrides]]
module = ["h5py.*", "faster_whisper.*", "ffmpeg.*"]
ignore_missing_imports = true

[tool.pyright]
typeCheckingMode = "standard"
pythonVersion = "3.12"
reportMissingTypeStubs = false

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "A", "C4", "SIM"]
ignore = ["E501", "UP006", "UP007"]  # Allow PEP 604 unions
```

## Troubleshooting

### Import Errors

If you see `ImportError: cannot import name 'convert_audio_to_wav'`:

1. Verify `backend/whisper/__init__.py` exists and exports the function
2. Check that `backend/whisper/whisper_utils.py` contains the function
3. Clear Python cache: `find . -type d -name __pycache__ -exec rm -r {} +`

### Type Checking Errors

**h5py type errors**: Ignored via `[[tool.mypy.overrides]]` in `pyproject.toml`

**Missing type stubs**: Add `# type: ignore` on imports if needed:
```python
from faster_whisper import WhisperModel  # type: ignore
```

### Test Failures

If tests fail with mock issues:

```bash
# Check mocking paths match your imports
grep -r "patch(" backend/tests/test_transcription_service.py

# Verify patches target the actual import location
# backend/services/transcription_service.py imports from backend.whisper
# So patches should target backend.services.transcription_service.is_whisper_available
```

## References

- **Python Typing**: https://peps.python.org/pep-0604/ (Union with |)
- **pytest**: https://docs.pytest.org/
- **MyPy**: https://mypy.readthedocs.io/
- **Pyright**: https://microsoft.github.io/pyright/
- **Ruff**: https://docs.astral.sh/ruff/

## Cards & References

- **FI-BACKEND-FEAT-003**: Transcription service implementation
- **FI-UI-FEAT-210**: Audio upload and transcription
- **FI-BACKEND-FEAT-206**: Whisper model cold start optimization

## Summary of Changes

| File | Change | Status |
|------|--------|--------|
| `backend/whisper/__init__.py` | Created - clean exports | ✅ New |
| `backend/whisper/whisper_utils.py` | Created - modern typing, comprehensive docs | ✅ New |
| `backend/services/transcription_service.py` | Refactored - modern typing, fixed imports | ✅ Updated |
| `backend/api/transcribe.py` | Updated - modern typing, clean imports | ✅ Updated |
| `backend/storage/__init__.py` | Updated - clean exports | ✅ Updated |
| `backend/tests/test_transcription_service.py` | Created - 48+ assertions, mocking examples | ✅ New |
| `pyproject.toml` | Enhanced - type checking config | ✅ Updated |
