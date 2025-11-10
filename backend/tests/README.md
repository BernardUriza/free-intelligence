# Backend Tests

Test suite for Free Intelligence backend (FastAPI)

## Structure

```
backend/tests/
├── conftest.py              # Pytest fixtures and configuration
│
├── api/                     # API endpoint tests (FastAPI routes)
│   ├── test_diarization_api.py          (25 tests - SKIPPED - endpoint disabled)
│   ├── test_katniss_api.py              (KATNISS Ollama integration)
│   ├── test_timeline_verify_api.py      (Timeline verification)
│   ├── test_api_integration.py          (Integration tests)
│   └── test_api_diarization_job_endpoint.py
│
├── services/                # Business logic tests
│   ├── test_audit_service.py
│   ├── test_corpus_service.py           (3 tests SKIPPED - needs HDF5)
│   ├── test_diarization_job_service.py
│   ├── test_export_service.py           (2 tests SKIPPED - needs HDF5)
│   ├── test_sessions_service.py
│   └── test_transcription_service.py
│
├── infrastructure/          # Infrastructure/DI tests
│   ├── test_container.py                (Dependency injection)
│   ├── test_repositories.py             (Data layer)
│   └── test_audit_sink.py               (Parquet audit sink)
│
└── unit/                    # Unit tests (utilities)
    ├── test_ollama_client.py
    ├── test_chunk_layering.py
    └── test_stream_chunk_robustness.py
```

## Running Tests

```bash
# Run all tests
pytest backend/tests

# Run by layer
pytest backend/tests/api/              # API endpoint tests
pytest backend/tests/services/         # Service layer tests
pytest backend/tests/infrastructure/   # Infrastructure tests
pytest backend/tests/unit/             # Unit tests

# Run specific test file
pytest backend/tests/api/test_katniss_api.py

# Run with coverage
pytest backend/tests --cov=backend --cov-report=html

# Collect only (no execution)
pytest backend/tests --collect-only
```

## Test Status

| Category | Count | Skipped | Active |
|----------|-------|---------|--------|
| **API** | 50+ | 25 | 25+ |
| **Services** | 70+ | 5 | 65+ |
| **Infrastructure** | 30+ | 0 | 30+ |
| **Unit** | 30+ | 1 | 29+ |
| **TOTAL** | **181** | **31** | **150** |

### Skipped Tests

- `api/test_diarization_api.py` (25 tests) - Diarization endpoint disabled, pending refactor
- `services/test_corpus_service.py` (3 tests) - Require HDF5 schema initialization
- `services/test_export_service.py` (2 tests) - Require HDF5 corpus data
- `unit/test_stream_chunk_robustness.py` (1 test) - Requires ffprobe

## Test Conventions

- **Fixtures**: Defined in `conftest.py`
- **Naming**: `test_<feature>_<scenario>.py`
- **Markers**: Use `@pytest.mark.skip()` for temporarily disabled tests
- **Mocking**: Use `unittest.mock` for external dependencies
- **Coverage**: Target ≥70% (enforced in CI)

## CI Integration

Tests run automatically on:
- Push to `main` or `develop`
- Pull requests
- Pre-commit hooks (type checking, linting)

**Pipeline**: `.github/workflows/backend-ci.yml`

## Adding New Tests

1. Determine the correct category (api/services/infrastructure/unit)
2. Create test file: `test_<feature>.py`
3. Follow existing test patterns
4. Run locally before committing
5. Ensure coverage doesn't drop

## References

- Pytest docs: https://docs.pytest.org
- FastAPI testing: https://fastapi.tiangolo.com/tutorial/testing/
- Coverage reports: `htmlcov/index.html` (after `--cov-report=html`)
