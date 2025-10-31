Free Intelligence · Kernel Context (Ultra‑Compact v0.5)

AURITY = Advanced Universal Reliable Intelligence for Telemedicine Yield (computational contract, not branding)

Owner: Bernard Uriza Orozco
Version: 0.1.0 (Fase 1)
Updated: 2025‑10‑29
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

♻️ Workflow Innegociable
	•	Nunca dejar ⚙️ In Progress vacío.
	1.	Si queda vacío → mover de inmediato la siguiente card prioritaria (P0>P1>P2).
	2.	Registrar movimiento en bitácora.

🧱 Arquitectura (resumen)

free-intelligence/
  backend/ (Python 3.11+, FastAPI)
    config_loader.py  logger.py  corpus_schema.py  corpus_ops.py
  storage/  corpus.h5  (HDF5, append-only)
  config/   config.yml
  tests/    (pytest)
  scripts/  sprint-close.sh  generate_test_data.py
  docs/

Stack: FastAPI · h5py · structlog · (Front: Next.js/React + Tailwind)

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

# 🏗️ BUILD & DEPLOY
pnpm build                     # Build producción (Turborepo)
pm2 start ecosystem.config.js  # Deploy NAS (PM2)

# 🖥️ NAS DEPLOYMENT (DS923+)
./scripts/validate-nas-deployment.sh  # Validate artifacts (7 checks)
./scripts/deploy-ds923.sh             # Automated deploy: Ollama + ASR worker
docker compose -f docker-compose.ollama.yml up -d  # Ollama only
docker compose -f docker-compose.asr.yml up -d     # ASR worker only

# 📋 TRELLO CLI
BOARD_ID=68fbfeeb7f8614df2eb61e42
trello board-overview $BOARD_ID

🔗 Referencias Rápidas
	•	Backend: backend/*
	•	Corpus HDF5: storage/corpus.h5
	•	Policies: config/*.yaml (ejecutables)
	•	Observability: observability/*
	•	Evaluation: eval/ (prompts.csv, run_eval.py, Makefile)
	•	Archive: docs/archive/ (MDs > 150 líneas)

⸻

📝 Bitácora (highlights, append‑only)
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

Nota: Este kernel es guía operativa mínima; las bitácoras y reportes viven en la conversación salvo docs permanentes.
