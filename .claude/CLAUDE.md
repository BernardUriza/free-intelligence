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

## 🐍 Python 3.14 (Obligatorio)

**Versión requerida:** Python 3.14.0+ (lanzado octubre 2025)

### Por qué 3.14

AURITY requiere Python 3.14 para aprovechar:
- **JIT compiler experimental** - 3-5% más rápido (crítico para pipelines RealtimeTalk)
- **t-strings** - Interpolación eficiente para prompts LLM
- **Lazy annotations** - Mejor rendimiento con Pydantic v2
- **InterpreterPoolExecutor** - Paralelismo en workers sin GIL bottleneck
- **compression.zstd** - Compresión superior para HDF5 chunks

### Setup Local

```bash
# Verificar versión
python --version  # Debe mostrar 3.14.x

# Instalar con pyenv (recomendado)
pyenv install 3.14.0
pyenv local 3.14.0

# Verificar configuración
python -c "import sys; assert sys.version_info >= (3, 14), 'Python 3.14+ requerido'"
```

### Features Relevantes

**1. t-strings (Template Strings)**
```python
# Antes (3.13)
prompt = f"Patient: {name}\nSymptoms: {symptoms}"

# Ahora (3.14) - con evaluación diferida
prompt = t"Patient: {name}\nSymptoms: {symptoms}"
```

**2. Lazy Annotations**
```python
# Mejora rendimiento de import en módulos con muchos type hints
from __future__ import annotations

def process_session(data: SessionData) -> SOAPNote:
    # Annotations no se evalúan hasta uso
    ...
```

**3. InterpreterPoolExecutor**
```python
# Útil para workers CPU-bound (transcription, diarization)
from concurrent.futures import InterpreterPoolExecutor

with InterpreterPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(transcribe_chunk, chunk) for chunk in chunks]
    results = [f.result() for f in futures]
```

### Recursos

- **Docs oficiales:** https://docs.python.org/3/whatsnew/3.14.html
- **Tutorial:** https://docs.python.org/3/tutorial/index.html
- **Real Python 2025:** https://realpython.com/popular-python-tutorials-2025/
- **PEP 745 (Release Schedule):** https://peps.python.org/pep-0745/

### Compatibilidad CI/CD

⚠️ **CRÍTICO**: CI/CD debe usar Python 3.14, no 3.11.

Verificar en `.github/workflows/pr-gate.yml`:
```yaml
env:
  PYTHON_VERSION: "3.14"  # ✅ Debe coincidir con pyproject.toml
```

⸻

🎯 FLUJO DE TRABAJO CON BERNARD - REGLA CRÍTICA

```
# ════════════════════════════════════════════════════════════════════════════
# CÓMO TRABAJAR CON BERNARD - ENFOQUE SIMPLE
# ════════════════════════════════════════════════════════════════════════════
# Bernard valora: simplicidad, enfoque, no tangentes, resultados rápidos.
# Claude debe seguir este flujo SIEMPRE:
# ════════════════════════════════════════════════════════════════════════════

FLUJO SIMPLE (seguir en orden):
  1. Entender qué se pide (NO asumir más)
  2. Hacer el cambio mínimo necesario
  3. Verificar localmente (curl, make dev-all)
  4. Commit → Push → PR
  5. LISTO. No agregar más.

❌ PROHIBIDO:
  - Ir por tangentes ("y también podríamos...")
  - Ofrecer soluciones no pedidas
  - Complicar lo simple
  - Hacer deploy manual cuando existe CI/CD
  - Preguntar sobre cosas no relacionadas
  - Perder el enfoque del task original

✅ CORRECTO:
  - Enfocarse SOLO en lo que se pidió
  - Verificar local → commit → PR → LISTO
  - Si hay duda, PREGUNTAR antes de actuar
  - Mantener respuestas cortas cuando Bernard está irritado

EJEMPLO DE ERROR (NO HACER):
  Bernard: "Revisa que /downloads existe"
  Claude: *intenta deploy con rsync, pregunta sobre DMG, va por tangentes*

EJEMPLO CORRECTO:
  Bernard: "Revisa que /downloads existe"
  Claude: curl localhost:9000/downloads/ → "Existe ✅" → fin
```

⸻

🚨 GIT WORKFLOW - REGLA INVIOLABLE 🚨

```
# ════════════════════════════════════════════════════════════════════════════
# FLUJO DE GIT OBLIGATORIO - SIN EXCEPCIONES
# ════════════════════════════════════════════════════════════════════════════
# Esta regla es ABSOLUTA. Claude NUNCA debe violarla bajo ninguna circunstancia.
# ════════════════════════════════════════════════════════════════════════════

FLUJO OBLIGATORIO:
  1. Trabajar SIEMPRE en rama `dev`
  2. Commit cambios a `dev`
  3. Push a `dev`
  4. Crear PR de `dev` → `main`
  5. Esperar aprobación del AI Gatekeeper (GPT-5)
  6. Merge PR (nunca push directo)

❌ PROHIBIDO - NUNCA HACER:
  - git push origin main (PROHIBIDO)
  - git commit directamente en main (PROHIBIDO)
  - Bypass de PR review (PROHIBIDO)
  - --force push a main (PROHIBIDO)

✅ CORRECTO - SIEMPRE HACER:
  - git checkout dev
  - git add . && git commit -m "mensaje"
  - git push origin dev
  - gh pr create --base main --head dev
  - gh pr merge (después de aprobación)

RAZÓN:
  - main es la rama de PRODUCCIÓN
  - dev es la rama de DESARROLLO
  - El AI Gatekeeper (GPT-5) revisa TODOS los cambios
  - Push directo a main deja dev desincronizada
  - Viola el flujo de CI/CD establecido

SI CLAUDE VIOLA ESTA REGLA:
  - Es un ERROR GRAVE
  - Debe disculparse inmediatamente
  - Debe sincronizar dev con main: git checkout dev && git merge main
  - Debe documentar el incidente

CLAUDE DEBE VERIFICAR ANTES DE CADA PUSH:
  1. ¿Estoy en la rama correcta? (debe ser dev)
  2. ¿Voy a crear un PR? (debe ser sí)
  3. ¿Voy a esperar review? (debe ser sí)
```

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

🤖 FI Cloud vs FI Edge Architecture

```
# ════════════════════════════════════════════════════════════════════════════
# DEPLOYMENT ARCHITECTURE (2025-01-04)
# ════════════════════════════════════════════════════════════════════════════
#
# FI Cloud (Production - app.aurity.io)
# ─────────────────────────────────────
# DO Droplet (1GB RAM) hosts:
#   - Nginx (SSL termination)
#   - Next.js static frontend
#   - FastAPI backend (port 7001)
#
# LLM Inference with Multi-Host Fallback (FI-BACKEND-FALLBACK-001)
# ─────────────────────────────────────────────────────────────────
# Priority order:
#   1. Windows tunnel (i9+RTX4060) - Primary, permanent tunnel
#   2. Mac localhost - Fallback when traveling/developing
#
# Flow:
#   Request → Try Windows Tunnel (retry 3x) → Try Mac localhost (retry 3x) → Error
#
# FI Edge Windows (Primary - Home)
# ─────────────────────────────────
#   - PC with i9 + RTX4060 (GPU acceleration)
#   - Ollama with Qwen3:1.7b, larger models
#   - Cloudflare Tunnel running permanently
#   - CORS: OLLAMA_ORIGINS="*" OLLAMA_HOST="0.0.0.0:11434"
#
# FI Edge Mac (Fallback - Travel)
# ───────────────────────────────
#   - MacBook for development
#   - Ollama local (localhost:11434)
#   - No tunnel, CPU inference only
#   - Used when Windows is unreachable
#
# Configuration:
#   - Tunnel URL: /tmp/ollama-tunnel-url.txt or OLLAMA_TUNNEL_URL env var
#   - Mac fallback: OLLAMA_MAC_FALLBACK env var (default: localhost:11434)
#   - Override (disable fallback): OLLAMA_HOST env var
#
# ════════════════════════════════════════════════════════════════════════════

Tunnel Management Script:
  ./scripts/ollama-tunnel.sh start    # Start tunnel + update DO
  ./scripts/ollama-tunnel.sh stop     # Stop tunnel
  ./scripts/ollama-tunnel.sh status   # Show status
  ./scripts/ollama-tunnel.sh restart  # Restart with new URL

Multi-Host Fallback:
  - OllamaProvider tries hosts in priority order
  - Each host has independent circuit breaker (5 failures → open 60s)
  - Response metadata includes hosts_tried for debugging
  - Reset all circuits: reset_all_ollama_circuit_breakers()

Requirements:
  - cloudflared: brew install cloudflared
  - ollama: brew install ollama
  - SSH access to DO: root@104.131.175.65

Cost Savings:
  - GPU Droplet (RTX 4000 Ada): $565/month
  - FI Edge (local hardware): $0/month
  - Cloudflare Tunnel: Free tier
```

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
  ❌ rsync, scp para deployment (SIEMPRE usar CI/CD)
  ❌ Copiar archivos manualmente al servidor
  ❌ "Es más rápido si lo hago manual" (NO, NUNCA)

DEPLOYMENT - REGLA ABSOLUTA:
  ❌ PROHIBIDO: rsync ./out/ root@servidor:/path/
  ❌ PROHIBIDO: scp archivo.dmg root@servidor:/path/
  ❌ PROHIBIDO: ssh root@servidor "mkdir && cp..."

  ✅ CORRECTO: git push → CI/CD deploya automáticamente
  ✅ CORRECTO: GitHub Releases para artifacts (.dmg, .AppImage)
  ✅ CORRECTO: DO Spaces / S3 via CI/CD para binarios grandes

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

# Frontend deployment
cd apps/aurity && pnpm build
PYTHONPATH=backend/src python3 -m fi_cli deploy deploy-frontend-eruda

# Backend config/restart
PYTHONPATH=backend/src python3 -m fi_cli deploy restart-backend-production

# HTTPS/SSL setup
PYTHONPATH=backend/src python3 -m fi_cli deploy setup-https-production

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

🧪 Smoke Tests (LLM / Ollama)

```bash
# ════════════════════════════════════════════════════════════════════════════
# OLLAMA + QWEN3 SMOKE TESTS
# ════════════════════════════════════════════════════════════════════════════
# Qwen3 usa "thinking mode" por defecto. DEBE usarse /api/chat (no /api/generate)
# con el parámetro "think" para controlar el comportamiento.
# ════════════════════════════════════════════════════════════════════════════

# 1. Verificar Ollama corriendo
curl -s http://localhost:11434/api/tags | jq '.models[].name'

# 2. Test básico Qwen3 (SIN thinking - respuesta directa)
curl -s http://localhost:11434/api/chat -d '{
  "model": "qwen3:1.7b",
  "messages": [{"role": "user", "content": "Di hola"}],
  "think": false,
  "stream": false
}' | jq '{content: .message.content, seconds: (.total_duration / 1000000000)}'
# Esperado: ~2-7s en M1/GPU, respuesta en .content

# 3. Test CON thinking (separa razonamiento de respuesta)
curl -s http://localhost:11434/api/chat -d '{
  "model": "qwen3:1.7b",
  "messages": [{"role": "user", "content": "Di hola"}],
  "think": true,
  "stream": false
}' | jq '{thinking: .message.thinking, content: .message.content}'
# Esperado: .thinking tiene el razonamiento, .content la respuesta

# 4. Test del backend completo (después de iniciar)
curl -s -X POST "http://localhost:7001/api/workflows/aurity/assistant/chat" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"hola"}],"persona":"general_assistant"}'

# ⚠️ ERRORES COMUNES:
# - Respuesta vacía → Usar /api/chat en vez de /api/generate
# - Timeout en CPU → Qwen3 requiere GPU o mucha RAM (4GB+ sin swap)
# - "think" no funciona → Actualizar Ollama a v0.9+
```

⸻

🌿 Git Workflow (2-Branch Model)

```
RAMAS PERMITIDAS (solo estas dos):
  • dev  → Desarrollo activo (multi-feature, multi-agent)
  • main → Producción (protegida, requiere PR + CI)

FLUJO DE TRABAJO:
  ┌─────────────────────────────────────┐
  │              dev                     │
  │  Trabajas aquí (caos controlado)    │
  │  CI corre en cada push              │
  └──────────────┬──────────────────────┘
                 │ PR cuando esté listo
                 ▼
  ┌─────────────────────────────────────┐
  │              main                    │
  │  Producción (protegida)             │
  │  Requiere: PR + CI pasando          │
  └─────────────────────────────────────┘

COMANDOS DIARIOS:
  git checkout dev                    # Siempre trabajar en dev
  git add . && git commit -m "..."    # Commits frecuentes
  git push origin dev                 # CI valida automáticamente

⚠️ SINCRONIZACIÓN CRÍTICA (después de merge a main):
  # Cuando un PR se mergea a main, dev queda BEHIND
  # SIEMPRE sincronizar antes de crear nuevos PRs

  git checkout dev
  git fetch origin
  git merge origin/main -m "chore: sync dev with main after PR #XX merge"
  git push origin dev

  # Verificar que dev está actualizado
  git log origin/main..origin/dev    # Debe estar vacío después de sync

  ❌ PROBLEMA: Si no sincronizas, los PRs quedarán en estado "BEHIND" y no podrán mergearse
  ✅ SOLUCIÓN: Sincronizar dev con main después de CADA merge

DEPLOY A PRODUCCIÓN:
  gh pr create --base main --head dev --title "Release: descripción"
  # Esperar CI ✅ → Merge → Deploy manual

REGLAS PARA CLAUDE:
  ❌ NUNCA crear ramas adicionales (no feature branches)
  ❌ NUNCA pushear directo a main
  ✅ Siempre trabajar en dev
  ✅ Usar PR para subir a main
  ✅ Verificar que CI pase antes de merge
  ✅ CRÍTICO: Sincronizar dev con main después de CADA merge (git merge origin/main)
     - Esto previene estado "BEHIND" en PRs futuros
     - Ejecutar SIEMPRE después de mergear un PR a main

💡 OPTIMIZACIÓN: No necesitas main local
  • Este workflow usa 2 branches REMOTAS (origin/dev, origin/main)
  • Pero solo necesitas 1 branch LOCAL (dev)
  • main local queda desactualizado y causa confusión ("behind 16 commits")

  Beneficios de borrar main local:
  ✅ Imposible commitear accidentalmente a main
  ✅ origin/main siempre es truth source (actualizado)
  ✅ Menos confusión mental (solo una rama local)
  ✅ git diff origin/main..dev funciona igual

  Cómo borrar main local:
  git checkout dev                    # Asegurar que estás en dev
  git branch -D main                  # Borrar main local (safe, no afecta remoto)

  Después de borrar, el workflow es idéntico:
  git fetch origin                    # Actualizar referencias remotas
  git merge origin/main               # Sincronizar desde remoto (no main local)
  git diff origin/main..dev           # Comparar con remoto (no main local)
```

CI (pr-gate.yml) - Valida antes de merge

```
Bloquea merge si:
  ❌ Errores de sintaxis Python
  ❌ Imports críticos rotos (fi_common, fi_storage, fi_auth, fi_workflow)

Reporta pero NO bloquea:
  📝 Lint warnings (Ruff)

Frontend: Se valida localmente con `cd apps/aurity && pnpm build`
```

AI Gatekeeper (GPT-5 Security Review) - OBLIGATORIO

```
🤖 Modelo: Azure OpenAI GPT-5-mini
🎯 Rol: Security-focused code reviewer con poder REAL de bloqueo
🔒 Estado: Required check (enforce_admins: true)

Qué revisa (CRITICAL issues only):
  ❌ SQL injection, XSS, command injection, path traversal
  ❌ Hardcoded secrets/API keys (sk-*, api_key=*, Bearer tokens)
  ❌ Code that crashes at runtime (syntax errors, undefined vars)
  ❌ Data loss bugs (DELETE without WHERE, DROP TABLE, rm -rf user input)
  ❌ Authentication/authorization bypasses
  ❌ Infinite loops or resource exhaustion

Veredictos:
  ✅ APPROVE - No issues o solo LOW/MEDIUM severity
  ⚠️ WARN - HIGH severity (recomienda fix pero permite merge)
  🚫 BLOCK - CRITICAL severity (merge DESHABILITADO físicamente)

Branch Protection:
  • "AI Gatekeeper" está en required_status_checks de main
  • enforce_admins: true (ni admins pueden bypass si bloquea)
  • Si BLOCK → botón de merge deshabilitado hasta fix

Fail-Open Safety:
  • Si Azure API falla (timeout, 500) → defaulta a APPROVE
  • Previene bloquear deploys legítimos por outages
  • Log: "Azure API returned XXX - defaulting to APPROVE"

Telemetría:
  • Cada review se guarda en GitHub Artifacts (90 días)
  • Path: ai-gatekeeper-telemetry-pr-{number}/
  • Includes: verdict, confidence, severity, issues[], timestamps

Ejemplos de BLOCKS reales:
  • PR #63: Path traversal en validate-release-artifacts.sh
    - rm -rf "/tmp/data-${VERSION}" sin validar VERSION
    - Attack: VERSION="../../../home/user" → borra /home/user
    - Fix: Validar con regex o usar mktemp -d
```

CD (deploy-production.yml) - Deploy automático a app.aurity.io

```
Trigger: Push a main (después de merge de PR)

Flujo automático:
  1. Integrity check (resetea cambios manuales en prod)
  2. Build frontend (Next.js static export)
  3. rsync frontend → Digital Ocean /opt/free-intelligence/apps/aurity/out/
  4. rsync backend → Digital Ocean /opt/free-intelligence/backend/
  5. pip install requirements-prod.txt
  6. Restart uvicorn (port 7001)
  7. Reload nginx
  8. Verify deployment (curl https://app.aurity.io)
  9. Create git tag (deploy-YYYYMMDD-HHMMSS)

Rollback manual:
  gh workflow run deploy-production.yml -f rollback_to=deploy-20251227-123456

Secrets requeridos (ya configurados):
  • DO_SSH_PRIVATE_KEY - SSH a Digital Ocean
  • AURITY_DEPLOY_KEY - Clonar submodule privado
  • AUTH0_DOMAIN, AUTH0_CLIENT_ID - Build frontend
  • SUPERADMIN_EMAILS - Build frontend
```

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

FI Coder (fi_coder)

⚠️ IMPORTANTE: Usar fi_coder en lugar de qwen-code directamente
	•	fi_coder = wrapper seguro sobre qwen-code con presets anti-fallo
	•	Procesa errores uno por uno en batches controlados
	•	Evita que qwen-code borre archivos o haga cambios destructivos

Ubicación: backend/src/fi_coder/

CLI:
```bash
# Ejecutar prompt con qwen-code (wrapper seguro)
PYTHONPATH=backend/src python3 -m fi_coder.cli.main execute "prompt aquí" --repo="."

# Fix lint errors (Ruff - Python)
PYTHONPATH=backend/src python3 -m fi_coder.cli.main lint-fix --file=backend/src/module.py
```

Workers (programático):
```python
# ESLint batch fix para Aurity (TypeScript/React)
from fi_workers.tasks.lint_fix_worker import lint_fix_aurity_batch
result = lint_fix_aurity_batch(batch_size=10)  # Procesa 10 errores a la vez

# Ruff batch fix para Backend (Python)
from fi_workers.tasks.lint_fix_worker import lint_fix_batch
result = lint_fix_batch(batch_size=5)
```

Funciones disponibles en lint_fix_worker.py:
	•	lint_fix_batch(batch_size) — Fix Ruff errors (Python backend)
	•	lint_fix_aurity_batch(batch_size) — Fix ESLint errors (TypeScript frontend)
	•	lint_fix_aurity_worker(batch_size) — Worker wrapper con métricas

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

---

## Desktop App CI/CD (Aurity Desktop)

### Overview

Aurity Desktop es una aplicación multiplataforma construida con:
- **Frontend**: Next.js (static export)
- **Desktop Framework**: Tauri (Rust)
- **Backend Sidecar**: FastAPI (PyInstaller bundle)
- **LLM**: Ollama local

### Platforms Soportadas

| Platform | Target Triple | Package Format | Status |
|----------|--------------|----------------|--------|
| macOS | `aarch64-apple-darwin` | DMG | ✅ Producción |
| Linux | `x86_64-unknown-linux-gnu` | AppImage | ✅ Producción |
| Windows | `x86_64-pc-windows-msvc` | NSIS | ✅ Producción |

### CI/CD Workflow

Archivo: `.github/workflows/build-desktop.yml`

**Trigger:**
```bash
# Build plataforma específica
gh workflow run build-desktop.yml -f platform=windows
gh workflow run build-desktop.yml -f platform=macos
gh workflow run build-desktop.yml -f platform=linux

# Build todas las plataformas
gh workflow run build-desktop.yml -f platform=all
```

**Jobs disponibles:**
- `build-linux` - Ubuntu 22.04 runner
- `build-macos` - macOS ARM64 runner
- `build-windows` - Windows Server 2022 runner

### Flujo de Build (Windows)

```yaml
1. Setup:
   - Node 20 + pnpm 9
   - Rust (target: x86_64-pc-windows-msvc)
   - Python 3.11

2. Build Backend:
   - PyInstaller con spec pre-configurado
   - Output: aurity-backend-x86_64-pc-windows-msvc.exe

3. Build Frontend:
   - Next.js static export con env vars de Auth0

4. Build Tauri:
   - Compila Rust app + bundle NSIS
   - Output: Aurity_1.0.0_x64-setup.nsis.zip

5. Signing (Ed25519):
   - pnpm tauri signer sign *.nsis.zip
   - Output: *.nsis.zip.sig

6. Distribución:
   - Upload a Azure Blob Storage
   - Upload a GitHub Artifacts
   - Create GitHub Release
   - Generate updater manifest (windows-x86_64)
```

### Code Signing

**Método**: Ed25519 (cross-platform, zero cost)

**Ventajas:**
- ✅ Mismo signing key para macOS/Linux/Windows
- ✅ Zero cost (vs $200-400/año certificado tradicional)
- ✅ CI/CD compatible (GitHub Secrets)

**Trade-offs:**
- ⚠️ SmartScreen warnings en Windows (primera instalación)
- ✅ Bypass simple: "More info" → "Run anyway"
- ✅ Auto-updater funciona sin warnings después de primera instalación

**Secretos requeridos:**
- `TAURI_SIGNING_PRIVATE_KEY` - Ed25519 key (ya existe, reutilizado)

### Auto-Updater

El updater manifest (`aurity-desktop-updater.json`) se genera automáticamente con 3 platforms:

```json
{
  "version": "1.0.0",
  "platforms": {
    "darwin-aarch64": { "signature": "...", "url": "..." },
    "linux-x86_64": { "signature": "...", "url": "..." },
    "windows-x86_64": { "signature": "...", "url": "..." }
  }
}
```

La app detecta updates en background y notifica al usuario.

### Local Development (Windows)

```powershell
# Build backend
cd apps/aurity-desktop/pyinstaller
python -m PyInstaller aurity-backend-x86_64-pc-windows-msvc.spec

# Build Tauri
cd ..
pnpm install
pnpm tauri build --target x86_64-pc-windows-msvc

# Verificar output
dir src-tauri\target\x86_64-pc-windows-msvc\release\bundle\nsis\
```

### Troubleshooting

**Windows Build Failures:**
- PyInstaller: Verificar que `backend/requirements-prod.txt` esté actualizado
- NSIS: Verificar que `tauri.conf.json` tenga config de Windows (líneas 88-101)
- Signing: Verificar que `TAURI_SIGNING_PRIVATE_KEY` esté en GitHub Secrets

**SmartScreen Bypass:**
- Normal con Ed25519 signing
- Documentado en README con screenshots
- Hash SHA256 incluido en release notes para verificación

### Archivos Críticos

| Archivo | Propósito |
|---------|-----------|
| `.github/workflows/build-desktop.yml` | CI/CD pipeline (3 platforms) |
| `apps/aurity-desktop/src-tauri/tauri.conf.json` | Tauri config (NSIS settings líneas 88-101) |
| `apps/aurity-desktop/pyinstaller/aurity-backend-x86_64-pc-windows-msvc.spec` | PyInstaller config Windows |
| `apps/aurity-desktop/README.md` | User-facing build instructions |

### Email Notifications (Windows Builds)

**Trigger:** Automático cuando build de Windows termina exitosamente

**Proveedor:** Azure Communication Services (ACS) - Servicio nativo de Azure

**Secrets requeridos:**
- `ACS_SMTP_USERNAME` - Format: `ResourceName|AppID|TenantID`
- `ACS_SMTP_PASSWORD` - Entra ID app secret
- `ACS_FROM_EMAIL` - DoNotReply@xxxxx.azurecomm.net
- `NOTIFY_EMAIL` - bernarduriza@gmail.com

**Email incluye:**
- Versión del build
- Commit SHA (short)
- Link directo a GitHub Release
- Link a workflow logs
- Timestamp del build

**Autenticación:** Entra ID (Azure AD) app credentials (más seguro que SMTP básico)

**Fail-safe:** Email failures NO bloquean builds (`continue-on-error: true`)

**Testing:**
```bash
gh workflow run build-desktop.yml --ref test-branch -f platform=windows
```

**Rate limits:** 100 emails/hora, 500/mes gratis (después $0.25/1000)

---

## 🐛 Windows Build Debugging Journey (2026-01-20)

### Context
Windows builds fallaban consistentemente. Proceso de debugging iterativo reveló 8 errores encadenados. Cada build fallaba "un paso más adelante" hasta completar.

### Errores Encontrados y Fixes Aplicados

#### Error #1: Missing requirements.txt (Build #21128337271)
**Síntoma:** PyInstaller no encontraba requirements.txt
**Root Cause:** Archivo faltante en `apps/aurity-desktop/pyinstaller/`
**Fix:** Crear requirements.txt con PyInstaller==6.11.1
**Commit:** (commit inicial del proceso)

#### Error #2: PyInstaller Version Incompatible
**Síntoma:** Conflicto de versiones de PyInstaller
**Root Cause:** Version mismatch entre requirements.txt y spec file
**Fix:** Pin PyInstaller==6.11.1 consistentemente

#### Error #3: Dependency Conflicts
**Síntoma:** pip resolver conflicts durante instalación
**Root Cause:** Dependencies con versiones incompatibles
**Fix:** Resolver conflicts en requirements-prod.txt

#### Error #4: Backend Dependencies No Instaladas (Build #21138010524)
**Síntoma:** Import errors durante PyInstaller build
**Root Cause:** Step "Install backend dependencies" faltante antes de PyInstaller
**Fix:** Agregar `pip install -r backend/requirements-prod.txt` antes de PyInstaller
**Commit:** 620ec78

#### Error #5: Rust 1.84 → 1.85 Required (Build #21159544629)
**Síntoma:**
```
Adding async-lock v3.4.2 (requires Rust 1.85)
Adding dlopen2 v0.8.2 (requires Rust 1.85)
Adding zbus v5.13.2 (requires Rust 1.85)
```
**Root Cause:** rust-toolchain.toml especificaba 1.84.0 pero dependencies requerían 1.85.0+
**Fix:** Upgrade `apps/*/rust-toolchain.toml` de 1.84.0 → 1.85.0
**Commit:** ef3b2da

#### Error #6: Pre-build Validation Runs Before Binary Exists (Build #21159966229)
**Síntoma:**
```
error: resource path `binaries\aurity-backend-x86_64-pc-windows-msvc.exe` doesn't exist
```
**Root Cause:** Pre-build Validation ejecuta `cargo check` que lee `tauri.conf.json`, el cual referencia el backend binary que aún no ha sido compilado por PyInstaller
**Fix:** Disabled Pre-build Validation con `if: false` (se movió después de PyInstaller en diseño posterior)
**User Commit:** 2b8b342

**Learning:**
- `cargo check` valida que tauri.conf.json sea válido, incluyendo que existan los binaries referenciados
- Pre-build Validation debe correr DESPUÉS de compilar el backend, no antes

#### Error #7: Sign NSIS Installer Hangs (Build #21160148835)
**Síntoma:** Step "Sign NSIS installer" colgado por 12+ minutos (debería tomar <10s)
**Root Cause:** PowerShell maneja stdin pipe diferente que bash - `echo "" |` causa hang
**Fix:** Remover pipe, pasar private-key directamente:
```powershell
# ANTES (hang):
echo "" | pnpm tauri signer sign "${{ steps.paths.outputs.path }}" --private-key "..."

# DESPUÉS (funciona):
pnpm tauri signer sign "${{ steps.paths.outputs.path }}" --private-key "..."
```
**Commit:** ac4143b

#### Error #8: wc/tr Not Available in Windows Git Bash (Build #21160148835)
**Síntoma:** `prepare-python-full.sh` exit code 127 "command not found"
**Root Cause:** Script usa `wc -c` y `tr` que no existen en Windows Git Bash
**Fix:** Cross-platform file size detection con `stat`:
```bash
# ANTES (falla en Windows):
FILE_SIZE=$(wc -c < "$FILE" | tr -d ' ')

# DESPUÉS (cross-platform):
if command -v stat &> /dev/null && stat --version &> /dev/null 2>&1; then
    FILE_SIZE=$(stat -c%s "$FILE")  # Linux (GNU stat)
elif command -v stat &> /dev/null; then
    FILE_SIZE=$(stat -f%z "$FILE")  # macOS (BSD stat)
else
    FILE_SIZE=$(powershell -Command "(Get-Item '$FILE').Length")  # Windows fallback
fi
```
**Commit:** ac4143b

### Build Progression

| Build | Errors Fixed | Farthest Step Reached | Outcome |
|-------|--------------|----------------------|---------|
| #21128337271 | None | Prepare Python Installer | Network timeout |
| #21138010524 | #1-3 | Pre-build Validation | Wrong directory |
| #21159406976 | #1-4 | Pre-build Validation | Rust formatting |
| #21159544629 | #1-5 | Pre-build Validation | Rust 1.84→1.85 |
| #21159741973 | #1-6 | Pre-build Validation | cargo clippy timeout |
| #21159966229 | #1-6 | Pre-build Validation | Disabled (fix #6) |
| #21160148835 | #1-6 | Sign NSIS installer | PowerShell hang (error #7) |
| #21160500828 | #1-8 | **In Progress** | **Testing final fixes** |

### Key Learnings

1. **Iterative Debugging is Normal in CI/CD**
   Cada build falla "un paso más adelante". No puedes ver errores posteriores hasta resolver los anteriores.

2. **Cross-Platform Shell Scripting is Hard**
   - PowerShell ≠ Bash (stdin pipes, command availability)
   - Git Bash on Windows no incluye todas las GNU tools (wc, tr)
   - Usar `stat` en vez de `wc` para file size (cross-platform)

3. **Rust Toolchain Version Matters**
   - Dependencies pueden requerir versiones específicas (edition2024 → Rust 1.85+)
   - rust-toolchain.toml debe coincidir con setup-tauri action

4. **Build Order Dependencies**
   - Tauri config validation requiere que backend binaries existan
   - Pre-build validation debe correr DESPUÉS de compilar sidecars

5. **cargo clippy vs cargo check for CI**
   - `cargo clippy` compila TODAS las dependencies (15-20 min con 587 packages)
   - `cargo check` solo valida sintaxis/tipos (2-3 min)
   - Para CI fail-fast, usar `cargo check` es suficiente

### Commands for Debugging

```bash
# Trigger Windows build
gh workflow run build-desktop.yml -f platform=windows --ref dev

# Monitor build progress
gh run watch

# View specific job logs
gh run view --job=<job-id> --log

# Cancel stuck build
gh run cancel <run-id>

# Check build artifacts
gh run view <run-id> --json artifacts
```

### Status: 🏃 In Progress
Build #21160500828 running with all 8 fixes applied. Expected to complete successfully.

---

## 🚨 Security Incidents & Response Process

### Incident Log

#### 2026-01-17: Path Traversal Vulnerability (PR #63)

**Timeline:**
- 17:04:27 - PR #63 merged to main (validation script with path traversal vuln)
- 17:04:34 - AI Gatekeeper flagged as CRITICAL (7 seconds AFTER merge)
- 17:05:00 - Hotfix PR #64 created with security fix
- 17:XX:XX - PR #64 merged, vulnerability patched

**Vulnerability:**
```bash
# VULNERABLE CODE (PR #63):
VERSION="${1:-}"
DOWNLOAD_DIR="/tmp/aurity-release-validation-${VERSION}"
rm -rf "$DOWNLOAD_DIR"  # Path traversal possible

# ATTACK VECTOR:
./validate-release-artifacts.sh "../../home/user"
# → rm -rf "/home/user"  # CATASTROPHIC
```

**Root Causes:**
1. **AI Gatekeeper fail-open behavior** - Ran AFTER merge instead of BEFORE
2. **No local security testing** - Malicious inputs not tested before commit
3. **Input validation missing** - User-controlled VERSION used directly in filesystem ops

**Fix Applied (PR #64):**
1. Strict semantic version regex: `^[0-9]+\.[0-9]+\.[0-9]+$`
2. `mktemp -d` for isolated temp dir (not user-controlled)
3. `trap EXIT` for automatic cleanup
4. Portable `${TMPDIR:-/tmp}/prefix.XXXXXX` form
5. 13/13 security tests passing

**Lessons Learned:**
1. ✅ **ALWAYS test with malicious inputs locally before commit**
   - Path traversal: `../../`, `../../../etc`
   - Command injection: `1.0.0; rm -rf /`, `$(whoami)`
   - Shell metacharacters: `|`, `&`, `;`, `$(...)`
2. ✅ **Never trust AI Gatekeeper timing** - It may run AFTER merge
3. ✅ **Validate ALL user inputs** with strict patterns before use in:
   - Filesystem operations (rm, mkdir, cd)
   - Command execution (system, exec, eval)
   - SQL queries, file paths, URLs
4. ✅ **Use mktemp for temp dirs** - Never derive paths from user input
5. ✅ **Portable shell scripting** - Test flag compatibility across GNU/BSD

**Response Process (Established):**
1. Immediate hotfix PR creation (< 1 min after detection)
2. Dual commit: security fix + regression tests
3. Fast-track review (no waiting for normal PR queue)
4. Document incident in CLAUDE.md
5. Update `.github/SECURITY.md` if pattern affects other code

**Prevention Checklist (Pre-Commit):**
- [ ] Input validation with strict regex/whitelist
- [ ] Security testing with malicious inputs
- [ ] No user input in filesystem ops without sanitization
- [ ] Portable shell syntax (POSIX-compatible where possible)
- [ ] Code review focused on OWASP Top 10

**Monitoring:**
- AI Gatekeeper verdicts logged to `/var/log/aurity-security.log`
- CRITICAL verdicts trigger Slack alert (even if merged)
- Weekly security audit of merged PRs (manual review)

---

## Browser MCPs (Automatización de Navegador)

### Chrome DevTools MCP (Interacción con el navegador)
Permite interactuar con Chrome: clicks, navegación, llenar formularios, tomar screenshots.

**Requisitos**: Chrome debe estar corriendo con remote debugging (gestionado por daemon automático)

**Herramientas disponibles**:
- `mcp__chrome-devtools__navigate_page` - Navegar a URLs
- `mcp__chrome-devtools__click` - Hacer click en elementos
- `mcp__chrome-devtools__fill` - Llenar campos de texto
- `mcp__chrome-devtools__take_screenshot` - Capturar pantalla
- `mcp__chrome-devtools__take_snapshot` - Obtener árbol de accesibilidad

**Nota**: Usa un perfil de Chrome separado (`~/.chrome-debug-profile`), no el perfil principal.

### Browser Tools MCP (Monitoreo)
Captura datos del navegador: console logs, network requests, auditorías.

**Requisitos**: DevTools debe estar abierto con el panel "BrowserToolsMCP" visible

**Herramientas disponibles**:
- `mcp__browser-tools__getConsoleLogs` - Ver logs de consola
- `mcp__browser-tools__getConsoleErrors` - Ver errores
- `mcp__browser-tools__getNetworkLogs` - Ver requests de red
- `mcp__browser-tools__takeScreenshot` - Capturar pantalla
- `mcp__browser-tools__runAccessibilityAudit` - Auditoría de accesibilidad
- `mcp__browser-tools__runPerformanceAudit` - Auditoría de performance

### Gestión de servicios
```bash
# Chrome Debug Daemon
launchctl start com.chrome-debug.daemon
launchctl stop com.chrome-debug.daemon
cat /tmp/chrome-debug-daemon.log

# Browser Tools Server
launchctl start com.browser-tools.server
launchctl stop com.browser-tools.server
cat /tmp/browser-tools-server.log
```
