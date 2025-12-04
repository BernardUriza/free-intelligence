Free Intelligence · Kernel Context (v0.7.2)

AURITY — Advanced Universal Reliable Intelligence for Telemedicine Yield

Owner: Bernard Uriza Orozco
Version: 0.1.1 (Production)
Updated: 2025-12-03
TZ: America/Mexico_City

⸻

⚡ Executive Kernel
	•	Single Entry: PUBLIC → INTERNAL → WORKER (no excepciones).
	•	Only PUBLIC routes bajo /api/workflows/aurity/*.
	•	Append‑only en datos clínicos (HDF5); integridad por sha256 + rename atómico.
	•	Zero trust entre capas; RBAC Auth0 en ADMIN.
	•	SLOs explícitos; observabilidad por defecto; kill‑switch listo.

⸻

🌐 Production

Live: https://app.aurity.io/
Backend: https://app.aurity.io/api/
SSL: Let’s Encrypt (auto‑renew)
DNS: app.aurity.io → 104.131.175.65
Legacy: fi-aurity.duckdns.org (deprecated)

Edge Topology

graph LR
  B[Browser (HTTPS:443)] --> N[Nginx (SSL termination)]
  N --> F[Static Frontend (Next.js)]
  N --> A[/api/* → FastAPI:7001]

CORS (backend/app/main.py)

Allow: http://localhost:9000, http://localhost:9050, https://app.aurity.io
Location: main.py:#125

⸻

🏛️ Layering (Critical)

❌ Regla Absoluta

/api/internal/* prohibido para clientes externos.
	•	Frontend/curl nunca llama /internal/*.
	•	InternalOnlyMiddleware ⇒ 403.
	•	Si ves /internal/* en una URL pública ⇒ BUG.

✅ Capas Válidas

1) PUBLIC — /api/workflows/aurity/* (única puerta)
2) INTERNAL — recursos atómicos; solo invocados por PUBLIC
3) WORKERS — ejecución (ThreadPoolExecutor)

PUBLIC Endpoints (catálogo vivo)

POST /api/workflows/aurity/stream                      # Upload chunk
GET  /api/workflows/aurity/sessions/{id}/monitor       # Real-time progress
POST /api/workflows/aurity/sessions/{id}/checkpoint    # Concatenate audio
POST /api/workflows/aurity/sessions/{id}/diarization   # Start diarization
POST /api/workflows/aurity/sessions/{id}/soap          # Generate SOAP notes
POST /api/workflows/aurity/sessions/{id}/finalize      # Encrypt & finalize

Nota: Workflows RealtimeTalk siguen el mismo prefijo; ver sección Speech → ASR → LLM → TTS.

WORKERS (2025-11-15)
	•	4 × transcription, 2 × diarization.
	•	Sin Docker/Redis/Celery; simplificado a ThreadPoolExecutor.

⸻

📦 Storage (HDF5) — Invariantes
	•	Un H5 por sesión; append‑only; single‑writer; SWMR opcional para lectura en vivo.
	•	Integridad: sha256 por sesión, publicado en manifest/DB.
	•	Cierre: escribir a *.h5.part → fsync → rename atómico a .h5.
	•	TTL configurable por tipo de sesión (p. ej., RealtimeTalk efímero).

Schema base

/sessions/{id}/tasks/{TASK_TYPE}/
  ├─ chunks/        # datos
  └─ metadata       # json/attrs

Task types: TRANSCRIPTION, DIARIZATION, SOAP_GENERATION, EMOTION_ANALYSIS, ENCRYPTION.

⸻

🗣️ Speech → ASR → LLM → TTS (RealtimeTalk)

Contrato operativo (resumen):
	1.	Frontend sube audio/* → 202 + jobId.
	2.	Worker ejecuta ASR → LLM → TTS, persiste en talk-<sid>.h5.part (append‑only).
	3.	Al Finalize: consolida dos mensajes (user, assistant) al H5 longitudinal del chat y borra el H5 temporal.

Eventos append‑only: user.audio, asr.partial, asr.final, assistant.delta, assistant.text, tts.audio, interrupt.

SLO RealtimeTalk: p95_total ≤ 5s, dropout_rate < 1%.

⸻

🔐 Security & Compliance Core
	•	RBAC (Auth0): ruta ADMIN /admin/users (rol FI-superadmin).
	•	JWT con claim de roles: https://aurity.app/roles.
	•	Data sovereignty: on‑prem, AES‑GCM‑256 at‑rest, HTTPS in‑transit.
	•	Public Safety: rate‑limit por IP/sesión; kill‑switch; CORS estricto.
	•	Logs: structlog sin PII/PHI; WORM para auditoría crítica.

⛔️ Production SSH Policy (ENFORCED)

```
# ════════════════════════════════════════════════════════════════════════════
# AURITY PRODUCTION SECURITY POLICY
# ════════════════════════════════════════════════════════════════════════════
# This policy is MACHINE-ENFORCED via:
#   - scripts/hooks/pre-receive-prod (blocks direct git push)
#   - scripts/hooks/prod-integrity-check.sh (cron every 5min)
#   - .github/workflows/deploy-production.yml (pre-deploy integrity check)
# ════════════════════════════════════════════════════════════════════════════

ALLOWED on production server:
  ✅ SSH for READ-ONLY audit (tail logs, check status)
  ✅ Viewing files: cat, less, head, tail
  ✅ Process inspection: ps, top, htop, lsof
  ✅ Log analysis: journalctl, tail -f /tmp/backend.log
  ✅ Health checks: curl localhost:7001/api/health

FORBIDDEN on production server:
  ❌ vim, nano, emacs, or ANY text editor
  ❌ echo "..." > file (file modification)
  ❌ git commit, git push (blocked by pre-receive hook)
  ❌ pip install (use CI/CD)
  ❌ systemctl stop/restart (use CI/CD rollback)
  ❌ Adding print() or debug statements
  ❌ "Quick fixes" of any kind

VIOLATION RESPONSE:
  1. Integrity monitor detects change within 5 minutes
  2. Alert sent to Slack + logged to /var/log/aurity-security.log
  3. Next CI/CD deploy auto-resets production to clean state
  4. Repeat violations = revoked SSH access

CLAUDE CODE DIRECTIVE:
  Claude must NEVER suggest:
  - "Just SSH in and edit..."
  - "Quick fix on prod..."
  - "Temporarily add a print statement..."
  - Any command that modifies production files directly

  Instead, Claude must ALWAYS suggest:
  - "Push to GitHub, CI/CD will deploy"
  - "Use make ci-deploy for immediate deployment"
  - "Create a hotfix branch and merge to prod"
```

🚨 CREDENTIAL & SECRET SECURITY (MANDATORY)

```
# ════════════════════════════════════════════════════════════════════════════
# SECRET MANAGEMENT POLICY - ZERO TOLERANCE
# ════════════════════════════════════════════════════════════════════════════
# This policy exists because a hardcoded API key in documentation caused
# real-world consequences. NEVER repeat this mistake.
# ════════════════════════════════════════════════════════════════════════════

ABSOLUTE RULES:

1. NEVER commit secrets to git:
   ❌ API keys (Azure, AWS, Deepgram, OpenAI, Auth0, etc.)
   ❌ Passwords or tokens
   ❌ Private keys or certificates
   ❌ Database connection strings with credentials
   ❌ Any string that looks like: sk-*, api_*, key=*, token=*

2. NEVER put secrets in documentation:
   ❌ README.md, CLAUDE.md, or any .md file
   ❌ Code comments
   ❌ Example files (use <PLACEHOLDER> instead)
   ❌ Curl examples with real keys

3. ALWAYS use environment variables:
   ✅ .env files (gitignored)
   ✅ .env.example with placeholders
   ✅ Secret managers (Auth0, GitHub Secrets, etc.)

CLAUDE CODE DIRECTIVE - CREDENTIALS:

  When Claude sees ANY of these patterns, it MUST:
  1. REFUSE to commit the file
  2. WARN the user immediately
  3. Suggest moving to .env

  Patterns to detect:
  - export.*API.*KEY.*=.*["'][a-zA-Z0-9]{20,}["']
  - AZURE_API_KEY, OPENAI_API_KEY, DEEPGRAM_API_KEY, AWS_SECRET
  - Bearer [a-zA-Z0-9]{20,}
  - sk-[a-zA-Z0-9]{20,}
  - Any 32+ character hexadecimal or base64 string in quotes

  Claude must NEVER:
  - Commit files with hardcoded credentials
  - Create "reference" or "example" files with real keys
  - Suggest "just for testing" with real credentials
  - Allow curl examples with actual API keys

  Claude must ALWAYS:
  - Use .env.example with <YOUR_API_KEY_HERE> placeholders
  - Check staged files for credential patterns before commit
  - Suggest git-secrets or pre-commit hooks for detection
  - Recommend rotating any key that may have been exposed

RECOVERY PROCEDURE:

  If a secret is committed:
  1. IMMEDIATELY rotate the exposed credential
  2. Run: git filter-repo --invert-paths --path <file> --force
  3. Force push: git push --force --all
  4. Notify affected services (Azure, AWS, etc.)
  5. Review access logs for unauthorized usage
```

⸻

📊 SLOs & Observabilidad

Servicio	p95 (ms)	Error rate	Métricas clave
PUBLIC API	800	<1%	requests_total, latency_ms_bucket, errors_total, rate_limited_total
RealtimeTalk	5000	<1%	asr_ms, llm_ms, tts_ms, total_ms
SOAP Gen	1500	<1%	soap_latency_ms, soap_failures_total

Dashboards: API Latency · Error Budget · Voice Pipeline
Alertas: p95 > SLO 3m ⇒ page on‑call
Tracing: workflow_id, session_id, idempotency_key

⸻

🧰 Dev & Ops

Dev

make dev-all    # Backend (7001) + Frontend (9000)
make test       # pytest
make type-check # Pyright
pnpm dev        # Next.js

Prod Deploy

cd apps/aurity && pnpm build && python3 ../../scripts/deploy-scp.py
python3 scripts/deploy-backend-cors-fix.py
python3 scripts/setup-https-letsencrypt.py

Nginx (/etc/nginx/sites-enabled/aurity)

server {
  listen 443 ssl;
  server_name fi-aurity.duckdns.org;
  ssl_certificate /etc/letsencrypt/live/fi-aurity.duckdns.org/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/fi-aurity.duckdns.org/privkey.pem;
  root /opt/free-intelligence/apps/aurity/out;
  location /api/ { proxy_pass http://localhost:7001; proxy_set_header Host $host; proxy_set_header X-Forwarded-Proto $scheme; }
  location / { try_files $uri $uri/ /index.html; }
}


⸻

🛠️ Development Tools

Qwen Code CLI

⚠️ IMPORTANTE: "qwen-code" ≠ "qwen-coder"
	•	qwen-code = CLI tool (similar a Claude Code) para agentic coding
	•	qwen-coder = modelo LLM de Alibaba (Qwen2.5-Coder, Qwen3-Coder)
	•	qwen-code usa el modelo Qwen3-Coder para operaciones de código

Instalación local (Mac):
	•	Ubicación: /opt/homebrew/lib/node_modules/@qwen-code/qwen-code/cli.js
	•	Alias: qwen-code → node /opt/homebrew/lib/node_modules/@qwen-code/qwen-code/cli.js
	•	Verificar: which qwen-code

Uso no-interactivo:
qwen-code "tu prompt aquí"                  # one-shot mode
qwen-code -p "tu prompt" --yolo             # auto-approve all
qwen-code --help                            # ver todas las opciones

Recursos:
	•	GitHub: https://github.com/QwenLM/qwen-code
	•	Documentación: https://qwenlm.github.io/blog/qwen3-coder/
	•	Contexto: "Vibe coding" con Qwen3-Coder-480B (256K context)

⸻

📂 Repo Layout

free-intelligence/
├─ backend/
│  ├─ app/main.py                     # CORS/entry
│  ├─ api/public/workflows/           # PUBLIC
│  ├─ api/internal/                   # INTERNAL (bloqueado)
│  ├─ workers/sync_workers.py         # ThreadPoolExecutor
│  └─ storage/task_repository.py      # HDF5 ops
├─ apps/aurity/
│  ├─ .env.production                 # NEXT_PUBLIC_BACKEND_URL
│  ├─ next.config.static.js           # output:'export'
│  └─ out/                            # static build
├─ storage/
│  └─ corpus.h5
└─ scripts/
   ├─ deploy-scp.py
   ├─ deploy-backend-cors-fix.py
   ├─ setup-https-letsencrypt.py
   └─ deploy-https-complete.py


⸻

🧱 Frontend Primitives

Chat Widget (components/chat/)
	•	Modos: normal | expanded | minimized | fullscreen.
	•	UX: infinite scroll ↑, autoscroll ↓ (100ms), response_mode: explanatory|concise.
	•	Storage por usuario (Auth0): fi_chat_widget_{user.sub}.
	•	Config: config/chat.config.ts, config/chat-messages.config.ts.
	•	Banner: GlobalPolicyBanner — “100% Local • HIPAA Ready • Append‑Only” (auto‑dismiss 5s).

User Management (components/admin/UserManagement.tsx)
	•	Ruta: /admin/users (rol FI-superadmin).
	•	Backend: /internal/admin/users + verificador JWT.

⸻

🔧 Configuración

Env Vars (extract)

# Backend
ALLOWED_ORIGINS="http://localhost:9000,...,https://fi-aurity.duckdns.org"
DEEPGRAM_API_KEY="..."  # STT

# Frontend
NEXT_PUBLIC_BACKEND_URL=https://fi-aurity.duckdns.org
NEXT_PUBLIC_API_BASE=https://fi-aurity.duckdns.org


⸻

📝 Changelog (reciente)

2025-11-20 — UX + RBAC + Voice
	•	Página /admin/users funcional; rol FI-superadmin.
	•	useChatVoiceRecorder + VoiceMicButton con VAD.
	•	Fix props de voz en /chat/ (ChatToolbar:172‑180).
	•	Import absolutos @/ unificados.
	•	UX: expand hide/minimize restore; autoscroll suave.

2025-11-17 — HTTPS prod
	•	DuckDNS + Let’s Encrypt; reverse proxy; CORS prod.

2025-11-15 — Sin Docker/Redis/Celery
	•	Workers via ThreadPoolExecutor; tracking HDF5.

2025-11-14 — HDF5 por tareas
	•	Migración jobs/ → tasks/{TASK_TYPE}/ (58 sesiones).

⸻

🧩 Troubleshooting (conciso)
	•	Turbopack: limpiar .next .turbo .swc node_modules/.cache y reiniciar.
	•	Imports: absolutos para cross‑dir (@/…).
	•	Auth0 403: verificar claim https://aurity.app/roles incluye FI-superadmin; reloguear.
	•	Scroll: usar ref local, no getElementById.
	•	Puertos: lsof -ti:9000 | xargs kill -9.

⸻

🏷️ Conventions & Comm
	•	NO_MD=1: evitar MD > 150 líneas (excepto README.md, CLAUDE.md).
	•	Responder en chat con bullets técnicos (10–15 líneas).
	•	Documentos permanentes → artefactos ejecutables.
	•	Commits: Conventional Commits + Task ID.
	•	Trello: FI-[AREA]-[TYPE]-[NUM]: Title + labels.

⸻

📚 Referencias
	•	Claude Code Excellence: /mnt/data/claude-code-excellence.md
	•	AURITY FRAMEWORK: /mnt/data/AURITY FRAMEWORK.md
	•	MCP Hub multi‑LLM: /mnt/data/MCP como capa de interoperabilidad en un Hub multi‑LLM.pdf
	•	AURITY Prompt Engineer (img): /mnt/data/AurityPromptEngineer.png

⸻

Este kernel context existe para que cualquier persona (humana o máquina) entienda cómo se mueve el sistema en 2 minutos: entradas, límites, garantías y rutas de escape. Si rompes una de estas invariantes, deja de ser AURITY.
