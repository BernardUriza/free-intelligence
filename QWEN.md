# Free Intelligence Project Context

## Project Overview

Free Intelligence (codename: AURITY - Advanced Universal Reliable Intelligence for Telemedicine Yield) is a local-first AI consultation system designed for healthcare environments. It implements an event-sourced architecture with append-only data storage using HDF5 format. The system provides medical AI assistance, audio transcription, and SOAP note generation while maintaining HIPAA compliance and data sovereignty.

**Key Features:**
- AI-powered medical assistant with Claude integration
- Audio transcription using Azure Whisper/Deepgram
- SOAP note generation (Subjective, Objective, Assessment, Plan)
- HDF5-based append-only storage with integrity verification
- HIPAA-compliant authentication and audit trails
- Monorepo architecture with Python backend and Next.js frontend

## Architecture

The system follows a layered architecture with distinct API layers:
- **Public API** (`/api/workflows/aurity/*`): CORS-enabled, handles orchestration
- **Internal API** (`/internal/*`): Localhost-only in production, handles atomic resources
- **Workers**: ThreadPoolExecutor-based task processing

**Technology Stack:**
- **Backend**: Python 3.11+, FastAPI, uvicorn
- **Storage**: HDF5 with h5py, append-only design
- **Frontend**: Next.js, TypeScript, React
- **Authentication**: Auth0 with JWT tokens and RBAC
- **Database**: PostgreSQL for user/patient data
- **Audio Processing**: Azure Whisper/Deepgram for transcription
- **LLM Integration**: Anthropic Claude API, Ollama for local models
- **Build System**: Turborepo with pnpm, Makefile for development

## Building and Running

### Development Setup
```bash
# Clone and initialize the monorepo
make setup                    # Full setup (dependencies + corpus init)

# Run services separately
make run                      # Start backend API (port 7001)
make run-gateway             # Start AURITY Gateway (port 7002)
make frontend:dev            # Start Next.js frontend (port 9000)

# Or run all services with Turborepo
pnpm dev                     # Start all services
make dev-all                 # Alternative all-services command
```

### Production Deployment
```bash
# Build and deploy
pnpm build                   # Build all applications
pm2 start ecosystem.config.js # Start services with PM2
make ci-deploy              # Deploy via CI/CD
```

### Key Commands
```bash
make test                    # Run Python tests
make lint                    # Lint code
make type-check             # Type check with Pyright
make format                 # Format code with Black
make health-check           # Check service health
make corpus-stats           # Show HDF5 corpus statistics
```

## Development Conventions

### Security Policies
- **No production SSH editing**: Never modify files directly on production servers
- **Secret management**: Use environment variables, never commit credentials
- **CORS policy**: Restrictive in production, development allows localhost
- **API access**: Internal endpoints blocked by middleware for external requests

### Code Structure
- **Backend**: `/backend/` directory with layered architecture (API, services, storage)
- **Frontend**: `/apps/aurity/` as Next.js application
- **Storage**: `/storage/corpus.h5` as primary HDF5 data store
- **Configuration**: YAML files in `/config/`, environment variables for deployment

### Testing and Quality
- **259+ tests** with 100% pass rate
- **Pre-commit hooks** enforce policies (6 validators)
- **Type checking** with Pyright and Mypy
- **Policy enforcement**: Append-only, no-mutation, audit requirements

## API Endpoints

### Public API (CORS-enabled)
- `POST /api/workflows/aurity/sessions/{session_id}/assistant` - AI assistant
- `GET/PUT /api/workflows/aurity/sessions/{session_id}/soap` - SOAP notes
- `POST /api/workflows/aurity/stream` - Audio upload
- `GET /api/workflows/aurity/sessions` - Session listing

### Internal API (Localhost-only in production)
- `GET/POST /internal/audit/*` - Audit operations
- `POST /internal/diarization/*` - Audio diarization
- `GET/POST /internal/transcribe/*` - Transcription services
- `POST /internal/llm/*` - LLM middleware

## Special Considerations

### Data Integrity
- HDF5 files use append-only policy with atomic rename operations
- SHA256 verification for data integrity
- Structured logging with timezone awareness
- Audit logs for all LLM interactions

### HIPAA Compliance
- RBAC with Auth0 authentication
- JWT tokens with role claims
- PHI protection with AES-GCM-256 encryption
- Audit trails for all operations

### Production Security
- SSH policy prohibits direct file modifications
- Pre-receive hooks block credential commits
- Rate limiting and CORS protection
- Internal-only middleware blocks direct access to sensitive endpoints
