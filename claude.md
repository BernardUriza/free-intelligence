Free Intelligence · Kernel Context (Compact)

Owner: Bernard Uriza Orozco
Version: 0.1.0 (Fase 1)
Updated: 2025-10-29
TZ: America/Mexico_City

⸻

🗣️ Comunicación
	•	**NO_MD=1** — Prohibido crear/editar .md > 150 líneas (excepto README.md, claude.md).
	•	Responder en chat (bullets, 10–15 líneas, sin fluff).
	•	Crear archivo solo si es documentación permanente (arquitectura, políticas) → artefacto ejecutable (YAML/JSON/Python/test).
	•	Estilo: técnico, preciso, citando rutas/commits cuando aplique.

⚠️ Reglas Críticas
	•	Cada sesión debe tener ID único (session_YYYYMMDD_HHMMSS).
	•	HDF5 (storage/corpus.h5) = fuente de verdad. Solo append; sin mutaciones.
	•	Archivar antes de responder.
	•	Operación LAN-only; sin dependencias cloud para runtime.
	•	Logs/auditoría obligatorios para acciones sensibles (export, verify, delete, search).

♻️ Workflow Innegociable
	•	Nunca dejar ⚙️ In Progress vacío.
	1.	Si queda vacío, mover de inmediato la siguiente card prioritaria (P0>P1>P2).
	2.	Registrar movimiento en bitácora.

🧱 Arquitectura (resumen)

free-intelligence/
  backend/  (Python 3.11+, FastAPI)
    config_loader.py  logger.py  corpus_schema.py  corpus_ops.py
  storage/  corpus.h5  (HDF5, append-only)
  config/   config.yml
  tests/    (pytest)
  scripts/  sprint-close.sh  generate_test_data.py
  docs/

Stack: FastAPI · h5py · structlog · (Front futuro: Next.js/React + Tailwind)

✅ Estado Snapshot
	•	Config, Logger, Esquema HDF5, Corpus Ops, Identity, Append-only, Mutation/LLM policies, Audit/Export operativos (tests 100% OK).
	•	Bitácora activa (append-only).
	•	Timeline API (9002) implementada y con tests.

🏷️ Convenciones
	•	IDs: session_YYYYMMDD_HHMMSS, interaction_id=UUIDv4, model_id="claude-3-5-sonnet-20241022".
	•	Cards Trello (título): FI-[AREA]-[TYPE]-[NUM]: Title (prioridad via labels, no en título).
	•	Commits: Conventional Commits + Task ID.

🔐 Secrets
	•	En env/variables; nunca en repo ni Trello.
	•	config.yml referencia ${VAR} (sin valores directos).

✅ DoD (Definition of Done)
	•	AC cumplidos · Tests básicos OK · Logs/instrumentación · **Artefacto ejecutable verificado** · Commit descriptivo con Task ID.
	•	Verificar con: `python3 tools/verify_artifact.py`

🗓️ Sprints (modelo)
	•	4 sprints de 4 días (16 días totales).
	•	Labels de Sprint (S1–S4) + Prioridad (P0/P1/P2) + Área.

🧰 Comandos Esenciales

# Timeline API (dev)
uvicorn backend.timeline_api:app --reload --port 9002 --host 0.0.0.0

# Trello CLI (Board: Free Intelligence)
BOARD_ID=68fbfeeb7f8614df2eb61e42
trello board-overview $BOARD_ID
trello move-card <CARD_ID> <LIST_ID>
trello add-label <CARD_ID> "red" "P0"

🔗 Referencias Rápidas
	•	Backend: backend/*
	•	Corpus HDF5: storage/corpus.h5
	•	Policies: config/*.yaml (ejecutables)
	•	Observability: observability/*.yaml, observability/*.prom
	•	Evaluation: eval/ (prompts.csv, run_eval.py, Makefile)
	•	Archive: docs/archive/ (MDs > 150 líneas)

⸻

📝 Bitácora (append-only)

2025-10-29 — NO_MD Fase 2: Políticas, Tests, Pre-commit, Guard, Trello DoD
	•	Políticas actualizadas con parámetros específicos:
		- config/fi.policy.yaml: sovereignty.egress=deny, privacy.phi=false, llm.budgets.monthly_usd=200, timeline.auto=false, agents=false, reactions=quarantine/audit/alert_warn
		- config/redaction_style.yaml: max_preview_chars=60, stop_terms (PII), patterns CURP/RFC, sensitive_sources=[asr,llm,ui]
		- config/decision_rules.yaml: triage_red→DECISION_APPLIED, contains_pii→quarantine+redact, latency>2000→SLO_BREACH
	•	Tests pytest actualizados y pasando (20 tests):
		- test_redaction.py: +2 tests (max_preview_chars, CURP/RFC mexican IDs)
		- test_decision_rules.py: +3 tests específicos (triage red, PII quarantine, latency SLO breach)
		- Exit: 20 passed in 0.20s
	•	Pre-commit instalado con linters:
		- black, ruff, isort (Python formatters)
		- .git-hooks/reject_large_md.py: bloquea commits con MDs >150 líneas
		- yaml-syntax-check, json-syntax-check
		- Instalado: pre-commit install (hooks activos)
	•	Guard verify_artifact.py: ya existente y funcional (12/12 artefactos válidos)
	•	Card FI-GOV-TOOL-001 creada:
		- ID: 690263e71410a16cfd67ffd2
		- Labels: P0 (red), Governance (blue), tool (green)
		- AC documentados: script usage, workflow integration, evidencia
	•	Trello DoD hardening: 9 P0 cards actualizadas con comentario estándar
		- Template: "Política NO_MD activa. DoD=artefacto ejecutable verificado. Adjunta evidencia/ruta."
		- Cards actualizadas: FI-CORE-FEAT-001, FI-RELIABILITY-STR-001, FI-UX-STR-001, FI-OBS-RES-001, FI-PHI-ART-001, FI-CLI-FEAT-002, FI-SEC-FEAT-002, FI-POLICY-STR-001, FI-GOV-TOOL-001
	•	Validaciones pasadas:
		- pytest -q: 20 passed ✅
		- pre-commit install: hooks activos ✅
		- YAML/JSON parsing: sin errores ✅
		- verify_artifact.py: 12/12 válidos ✅

2025-10-29 — Política NO_MD Activada
	•	NO_MD=1 establecido: Prohibido crear/editar .md > 150 líneas
	•	71 MDs archivados → docs/archive/ (reviews, playbooks, tests, arquitectura detallada)
	•	Stubs creados: eval/README.md, docs/README.md (≤10 líneas)
	•	Artefactos ejecutables creados:
		- eval/: prompts.csv, metrics.schema.json, run_eval.py, Makefile
		- observability/: error_budgets.yaml, alerts.prom
		- config/: fi.policy.yaml, redaction_style.yaml, decision_rules.yaml
		- tests/: test_redaction.py, test_decision_rules.py
		- tools/: verify_artifact.py
	•	Pre-commit hook instalado: rechaza MDs > 150 líneas (.git/hooks/pre-commit)
	•	Pre-commit config: .pre-commit-config.yaml (YAML/JSON validators)
	•	Verificación: 12/12 artefactos válidos (tools/artifact_verification.json)
	•	DoD actualizado: incluye "Artefacto ejecutable verificado"
	•	Board ID registrado: 68fbfeeb7f8614df2eb61e42

2025-10-29 — Corpus Hermeticum → Trello (10 EPICs)
	•	Creadas 10 cards filosóficas (FI-PHI-MAN-001, FI-RELIABILITY-STR-001, FI-UX-STR-001, FI-PHI-STR-001, FI-OBS-RES-001, FI-PHI-ART-001, FI-UX-ART-001, FI-POLICY-STR-001, FI-OBS-STR-001, FI-GTM-ART-001)
	•	6 P0 movidas a "🚀 Sprint" (SPR-44-2025: 2025-10-29 → 2025-11-19)
	•	4 P1 quedan en "📚 Philosophy & Architecture" (groomed)
	•	Labels aplicados: Área (PHI, Reliability, UX/UI, Policy, Observabilidad, GTM), Tipo (manifesto, strategy, research, artifact), Prioridad (P0/P1), Sprint (SPR-44-2025)
	•	Dependencias identificadas: (1) alimenta todas; (2) depende de métricas base; (8) depende de (1)
	•	Comentarios estándar añadidos a P0 con plan start→due

⸻

Nota: Este kernel es guía operativa mínima; las bitácoras y reportes viven en la conversación salvo docs permanentes.
