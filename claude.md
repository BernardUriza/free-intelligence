Free Intelligence · Kernel Context (Ultra‑Compact v0.5)

AURITY = Advanced Universal Reliable Intelligence for Telemedicine Yield (computational contract, not branding)

FI-STRIDE Hackathon 2025 (20-Card Sprint, Full Compliance):
	• KATNISS (Oficial): Keeper Artificial Trainer Nurturing Intelligence Sportive Spark
	  └─ Integrado en FI-STRIDE-SESION-05 (post-sesión: Ollama analysis + motivation)
	• Arquitectura: Kernel Artificial Token Neural Intelligence System Serverless
	  └─ PWA (9050) + Ollama local + IndexedDB + Offline-first
	• 20 FI-STRIDE Cards (Sprint backlog):
	  ├─ QA-01 (Philosophy): PWA + Dead-Drop Relay (TDD) ✅ [Moved to Philosophy]
	  ├─ PWA-BASE-01 (Testing): Shell PWA, routing, a11y ✅ [IMPLEMENTADO]
	  ├─ ONBOARDING-02 (Testing): Consentimiento accesible ✅ [IMPLEMENTADO: AthleteFlow]
	  ├─ T21-PACK-03 (Testing): Plugin T21 - UI pack
	  ├─ SESION-04/05 (Testing): Sesión viva + check-in emocional + KATNISS
	  ├─ OFFLINE-06 (Sprint): Biblioteca ejercicios
	  ├─ OFFLINE-07 (Sprint): Modo offline - cola/reintentos
	  ├─ PRIVACIDAD-08 (Sprint): Panel privacidad
	  ├─ DASHBOARD-09/14 (Sprint): Coach dashboard + KPIs
	  ├─ CRYPTO-15/16 (Sprint): AES-GCM + Dead-Drop Relay
	  ├─ RELAY-17 (Sprint): Relay NAS - WORM lógico
	  ├─ INFRA-18 (Sprint): CI/CD + Netlify deploy
	  └─ POLISH-19/20 (Sprint): i18n + Plan B

Owner: Bernard Uriza Orozco
Version: 0.1.0 (Fase 1)
Updated: 2025‑11‑06
TZ: America/Mexico_City

⸻

🗣️ Comunicación
	•	NO_MD=1 — Prohibido crear/editar .md > 150 líneas (excepto README.md, claude.md).
	•	Responder en chat: bullets técnicos (10–15 líneas), sin fluff.
	•	Crear archivo solo si es documentación permanente → artefacto ejecutable (YAML/JSON/Python/test).
	•	Estilo: preciso, citar rutas/commits cuando aplique.

⚠️ Reglas Críticas
	•	session_id único session_YYYYMMDD_HHMMSS.
	•	HDF5 (storage/corpus.h5) = fuente de verdad: append‑only; sin mutaciones.
	•	Archivar antes de responder; auditoría obligatoria en acciones sensibles (export/verify/delete/search).
	•	LAN‑only, sin dependencias cloud en runtime.

🏗️ Arquitectura Layering (CRÍTICO)
	•	PUBLIC (/api/workflows/*) = Orquestadores PUROS
	  └─ NUNCA usar Services directamente
	  └─ SOLO llamar endpoints /internal/*
	  └─ SOLO coordinar flujos y devolver job_id
	•	INTERNAL (/api/internal/*) = Recursos atómicos
	  └─ Estos SÍ usan Services
	  └─ Estos SÍ hacen append a HDF5
	  └─ Endpoints: /transcribe, /sessions, /diarization, etc.
	•	WORKERS (background) = Procesamiento asíncrono
	  └─ Celery tasks, threading
	  └─ Frontend polling con job_id

♻️ Workflow Innegociable
	•	Nunca dejar ⚙️ In Progress vacío.
	1.	Si queda vacío → mover de inmediato la siguiente card prioritaria (P0>P1>P2).
	2.	Registrar movimiento en bitácora.

🧱 Arquitectura (App Mapping)

free-intelligence/
  🔧 backend/ (Python 3.11+, FastAPI port 7001)
    API Routes (backend/api/*):
      ├─ diarization.py     [POST /upload, GET /jobs/{id}, /result, /export, /soap, /restart]
      ├─ transcribe.py      [Transcription endpoints]
      ├─ triage.py          [Triage intake flow]
      ├─ audit.py           [Audit logs API]
      ├─ sessions.py        [Session mgmt]
      ├─ timeline_verify.py [Timeline verification]
      └─ kpis.py            [KPIs aggregation]
    Core Services:
      ├─ diarization_service.py      [Main diarization logic]
      ├─ diarization_jobs.py         [Job state management]
      ├─ diarization_worker_lowprio.py [Background worker + CPU scheduler]
      ├─ diarization_service_v2.py   [Parallel optimization]
      ├─ whisper_service.py          [Whisper model wrapper]
      ├─ fi_consult_service.py       [LLM consultation + routing]
      ├─ services/soap_generation_service.py [SOAP extraction]
      └─ services/diarization_job_service.py [Job control (restart/cancel)]
    Infrastructure:
      ├─ llm_middleware.py           [Main app + LLM routing]
      ├─ main.py                     [Entry point (uses llm_middleware)]
      ├─ corpus_ops.py               [HDF5 append operations]
      ├─ corpus_schema.py            [Schema definitions]
      ├─ policy_enforcer.py          [Security policies]
      ├─ logger.py & logger_structured.py
      └─ config_loader.py

  📁 storage/
    ├─ corpus.h5              [Main corpus HDF5 (append-only)]
    │   ├─ /interactions/     [LLM interactions]
    │   ├─ /embeddings/       [Vector embeddings]
    │   └─ /sessions/{session_id}/tasks/  [Task-based architecture (2025-11-14)]
    ├─ diarization.h5         [DEPRECATED - migrated to corpus.h5]
    └─ audio/                 [Session audio files]

  📦 HDF5 Task-Based Schema (Refactored 2025-11-14):
    Philosophy:
      - 1 Session = 1 consulta médica con catálogo único de tasks
      - 1 Task Type máximo por session (no duplicados)
      - Cada task contiene: chunks/ (data) + metadata (JSON)

    Structure:
      /sessions/{session_id}/tasks/{TASK_TYPE}/
        ├─ chunks/          [Task-specific data chunks]
        │   └─ chunk_{idx}/ [Individual chunk with typed datasets]
        └─ metadata         [Job execution metadata: status, progress, etc.]

    Task Types (backend/models/task_type.py):
      - TRANSCRIPTION    : Whisper ASR transcription
      - DIARIZATION      : Speaker classification + text improvement
      - SOAP_GENERATION  : Clinical notes extraction
      - EMOTION_ANALYSIS : Patient emotion detection
      - ENCRYPTION       : AES-GCM audio encryption

    TRANSCRIPTION Chunk Schema:
      /sessions/{session_id}/tasks/TRANSCRIPTION/chunks/chunk_{idx}/
        ├─ transcript       : utf-8 string (h5py.string_dtype)
        ├─ audio_hash       : utf-8 string (SHA256)
        ├─ duration         : float64 (seconds)
        ├─ language         : utf-8 string (es, en)
        ├─ timestamp_start  : float64 (seconds from start)
        ├─ timestamp_end    : float64 (seconds from start)
        ├─ confidence       : float64 (0-1, Whisper confidence)
        ├─ audio_quality    : float64 (0-1, heuristic quality)
        └─ created_at       : utf-8 string (ISO 8601)

    API:
      - backend/storage/task_repository.py (NEW, production)
      - backend/storage/session_chunks_schema.py (DEPRECATED, backward compat)
      - backend/repositories/job_repository.py (DEPRECATED, backward compat)

    Migration:
      - tools/migrate_jobs_to_tasks.py (58 sessions migrated ✅)
      - Old schemas (jobs/, production/) still readable via compat layer

  🎨 apps/aurity/ (Next.js/React port 9000)
    ├─ pages/dashboard        [Main UI]
    ├─ pages/triage           [Intake flow]
    └─ components/            [Reusable React components]

  🧪 tests/ & backend/tests/  [pytest test suite]

  📜 scripts/
    ├─ restart_diarization_job.py      [Manual job restart]
    ├─ process_remaining_chunks.py     [Chunk completion]
    └─ sprint-close.sh                 [Sprint utilities]

Stack: FastAPI · h5py · structlog · Next.js/React · Tailwind · Ollama/Claude

✅ Estado Snapshot
	•	Config, Logger, Esquema HDF5, Corpus Ops, Identity, Append‑only, Mutation/LLM policies, Audit/Export operativos (tests OK).
	•	Bitácora activa (append‑only).
	•	Timeline API (9002) implementada y testeada.

🏷️ Convenciones
	•	IDs: session_YYYYMMDD_HHMMSS, interaction_id=UUIDv4, model_id="claude-3-5-sonnet-20241022".
	•	Trello: FI-[AREA]-[TYPE]-[NUM]: Título (prioridad por labels, no en título).
	•	Commits: Conventional Commits + Task ID.

🔐 Secrets
	•	En variables de entorno; nunca en repo ni Trello.
	•	config.yml referencia ${VAR} (sin valores directos).

✅ Definition of Done (DoD)
	•	AC cumplidos · tests básicos OK · logs/instrumentación · artefacto ejecutable verificado · commit con Task ID.
	•	Verificación: python3 tools/verify_artifact.py.

🗓️ Sprints
	•	4 sprints × 4 días (16 días).
	•	Labels: Sprint (S1–S4) + Prioridad (P0/P1/P2) + Área.

🧰 Comandos Esenciales

# 🚀 ARRANCAR SERVICIOS (DevOps-Optimized)
make dev-all                   # Un solo comando → Backend + Frontend
                               # Backend: http://localhost:7001
                               # Frontend: http://localhost:9000
                               # Auto-reload · Ctrl+C detiene todo

# 📋 MODO MANUAL (terminales separadas)
make run                       # Terminal 1: Backend API (puerto 7001)
pnpm dev                       # Terminal 2: Frontend (puerto 9000)

# 🧪 TESTING
make test                      # pytest backend/tests
pnpm test                      # tests frontend

# 🔍 TYPE CHECKING (Pylance/Pyright CLI)
make type-check                # Quick check (2 sec) - Pyright solo
make type-check-all            # Completo (15 sec) - Pyright + Mypy + Ruff
make type-check-batch          # Export JSON + batch report
make type-check-export         # Export para Claude Code batch fixing

# 🏗️ BUILD & DEPLOY
pnpm build                     # Build producción (Turborepo)
pm2 start ecosystem.config.js  # Deploy NAS (PM2)

# 🖥️ NAS DEPLOYMENT (DS923+)
./scripts/validate-nas-deployment.sh  # Validate artifacts (7 checks)
./scripts/deploy-ds923.sh             # Automated deploy: Ollama + ASR worker
docker compose -f docker-compose.ollama.yml up -d  # Ollama only
docker compose -f docker-compose.asr.yml up -d     # ASR worker only

# 📋 TRELLO CLI v2.2.0 - WITH CLAUDE AI ANALYSIS ⭐
BOARD_ID=68fbfeeb7f8614df2eb61e42

## Discovery Commands (START HERE)
trello help-json                        # All commands in JSON
trello board-overview $BOARD_ID         # Complete board structure
trello board-ids $BOARD_ID              # Quick ID reference
trello search-cards $BOARD_ID "query"   # Search across board

## CARD MOVEMENTS WITH INTELLIGENT ANALYSIS (NEW IN v2.2)
trello move-card <card_id> <list_id>    # Move card (includes Claude AI context)
trello quick-start <card_id>            # Start work (auto-finds In Progress + analysis)
trello quick-test <card_id>             # Move to Testing (auto-finds Testing + analysis)
trello quick-done <card_id>             # Move to Done (auto-finds Done + analysis)

## WORKFLOW: Each movement includes Claude AI analysis
# Example:
trello quick-start FI-STRIDE-SESION-04
# Output:
# ✅ Card moved to '⚙️ In Progress'
# 💡 CLAUDE AI ANALYSIS: [Contextual intelligence about the work]

🔬 Type Checking Automation (Pylance/Pyright)
	•	CLI Tool: python3 tools/detect_type_errors.py backend/ (auto-detección)
	•	Baseline: 821 errors + 57 warnings, 57 files (mostly h5py + attribute access issues)
	•	Top Issues: reportAttributeAccessIssue (362), reportIndexIssue (253), reportArgumentType (155)
	•	Top Files: audit_logs.py (152), fi_exporter.py (136), search.py (105), corpus_ops.py (102)
	•	Strategy: Pyright (2 sec) → Export JSON → Batch fix con Claude Code
	•	Config: pyrightconfig.json (standard mode, strict type checking)
	•	Docs: docs/TYPE_CHECKING_QUICKSTART.md (profesional workflow)
	•	Commands: make type-check (quick) | make type-check-all (15s) | make type-check-export (JSON)
	•	Next: Remediate critical errors (reportArgumentType, reportAssignmentType) → CI/CD enforcement

🔗 Referencias Rápidas
	•	Backend: backend/*
	•	Corpus HDF5: storage/corpus.h5
	•	Policies: config/*.yaml (ejecutables)
	•	Observability: observability/*
	•	Evaluation: eval/ (prompts.csv, run_eval.py, Makefile)
	•	Archive: docs/archive/ (MDs > 150 líneas)
	•	Type Checking: tools/detect_type_errors.py, docs/TYPE_CHECKING_QUICKSTART.md

⸻

📝 Bitácora (highlights, append‑only)
	•	Deepgram STT Integration (2025-11-15) ✅: Replaced Whisper offline with cloud-based Deepgram API for instant transcription (1-2s vs 10-30s). Created backend/services/deepgram_service.py (async API client), backend/workers/deepgram_transcription_task.py (Celery task), added aiohttp to requirements.txt. Updated TranscriptionService to dispatch deepgram_transcribe_chunk instead of transcribe_chunk_task. Benefits: no GPU needed, $0.0043/min, 50k free minutes/month. Setup: export DEEPGRAM_API_KEY=... (get from console.deepgram.com). See DEEPGRAM_SETUP.md for full configuration.
	•	Python 3.9 Type Annotation Fix (2025-11-15) ✅: Fixed 29 files with Python 3.10+ union syntax (float | None) incompatible with Python 3.9. All files already had from __future__ import annotations, but FastAPI was evaluating types at route registration. Converted all | unions to Optional[]/Union[] syntax. Backend now loads without TypeError.
	•	Chunk Polling Root Cause Analysis (2025-11-15) ✅: Identified why polling stayed "pending": Celery worker received tasks but never executed them (received ✅ but no "started" log). Audio was stored in HDF5 correctly, but worker wasn't processing. Root cause: Whisper worker had issues; migrated to Deepgram instead.
	•	Tailwind/PostCSS Monorepo Fix (2025-11-04) ✅: Fixed "Unexpected character '@' en globals.css" error in apps/aurity (Next 14, Turborepo/pnpm). Created tailwind.config.ts (content paths, darkMode), updated globals.css to contain only @tailwind directives, removed duplicate tailwind.css import from layout.tsx, added postcss.config.js en root for workspace compatibility. Rule: Each app in monorepo must have local postcss.config.js + tailwind.config.ts; shared packages export pre-compiled CSS (no @tailwind directives).
	•	Diarization Job Restoration (2025-11-05) ✅: Cancelled job f2667c96-105b-42c7-b385-2e20417a7fff restarted from chunk 24 (85%→100%), SOAP generated, both scripts created (restart_diarization_job.py, process_remaining_chunks.py). Fixed corpus_ops.py syntax errors (paréntesis faltantes), registered diarization router in llm_middleware.
	•	DevOps Strategy Complete ✅: make dev-all (script unificado), PM2 NAS deployment, DEVOPS_STRATEGY.md creado.
	•	Policy Integration + Dashboard KPIs ✅: enforcement end‑to‑end; KPIs UI y API listas.
	•	LOCK‑DONE: cards requieren evidencia QA + verify_artifact; rollback automático si falta.
	•	NO_MD activada: MDs >150 líneas a docs/archive/; artefactos ejecutables creados.
	•	Sessions API + CORS ✅: backend 7001; .env.local apunta a 7001.
	•	Triage API ✅: /api/triage/intake + manifest + audit.
	•	Timeline API Integration (UI) ✅: timeout/retry/cache; p95 < 300ms.
	•	Interaction Viewer ✅: split view, export JSON/MD, toggle "no spoilers".
	•	Security Fix Pack v1 ✅: egress allowlist exacto, DI para PolicyEnforcer, tests de bypass.
	•	KPIs API ✅: agregador in‑memory, p95 2ms, chips/timeseries.
	•	NAS Deploy (Turborepo + PM2): scripts/productión sin cloud.
	•	NAS DS923+ Deployment Stack ✅: Ollama (11434) + ASR worker (faster-whisper INT8), scripts automatizados, validation 7/7.
	•	Type Checking Automation ✅: pyright CLI integration, tools/detect_type_errors.py, make type-check* commands, JSON export para batch fixing con Claude Code (821 errors baseline → remediation plan ready).
	•	Python 3.9 Compatibility + Datetime Fix ✅: from __future__ imports (82 files), datetime.utcnow() → datetime.now(timezone.utc) (22 files), h5py type ignore (13 files).
	•	Chunk Transcription Layering (AUR-PROMPT-4.2) ✅: PUBLIC → INTERNAL → WORKER arquitectura implementada. PUBLIC /consult/stream (pure orchestrator, NO Services), INTERNAL /transcribe/chunks (job creation + 202), Worker transcribe_chunk_task (ffmpeg + ASR + HDF5 append). HDF5 schema /sessions/{session_id}/chunks/chunk_{idx} con typed dtypes (NO object). Tests: backend/tests/test_chunk_layering.py. Docs: CLAUDE.md actualizado.
	•	HDF5 Task-Based Architecture Refactor (2025-11-14) ✅: Migración completa de jobs/+production/ a tasks/{TASK_TYPE}/. Filosofía: 1 Session = 1 consulta médica con catálogo único de tasks (max 1 por tipo). Created backend/models/task_type.py (TaskType enum), backend/storage/task_repository.py (500+ líneas, 8 funciones), tools/migrate_jobs_to_tasks.py. Deprecated job_repository.py + session_chunks_schema.py (wrappers con backward compat). Updated workers: transcription_tasks.py, diarization_tasks.py. Migration: 58 sessions, 37 migrated, 0 errors. Tests: backend/tests/test_task_repository.py (13 tests, 100% pass). UTC fix: 23+ files (datetime.now(timezone.utc)). Schema: /sessions/{id}/tasks/TRANSCRIPTION|DIARIZATION|SOAP_GENERATION|EMOTION_ANALYSIS|ENCRYPTION. Docs: CLAUDE.md actualizado con nueva estructura.

Nota: Este kernel es guía operativa mínima; las bitácoras y reportes viven en la conversación salvo docs permanentes.
