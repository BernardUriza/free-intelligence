# Free Intelligence · Quick Reference (v0.7.3)

**AURITY — Advanced Universal Reliable Intelligence for Telemedicine Yield**

**Owner:** Bernard Uriza Orozco  
**Version:** 0.1.1 (Production)  
**Updated:** 2026-01-20  
**TZ:** America/Mexico_City

---

## 🚀 Quick Start

```bash
# Development
make dev-all              # Backend (7001) + Frontend (9000)
make test                 # pytest
pnpm dev                  # Next.js only

# Production Deploy
git push origin dev       # → PR to main → CI/CD auto-deploy

# Desktop Builds
gh workflow run build-desktop.yml -f platform=windows
```

## 📂 Project Structure

```
free-intelligence/
├── backend/              # FastAPI + HDF5 storage
│   ├── app/main.py      # CORS/entry
│   ├── api/
│   │   ├── public/workflows/     # PUBLIC API
│   │   └── internal/             # INTERNAL (blocked)
│   └── workers/         # ThreadPoolExecutor
├── apps/
│   ├── aurity/          # Next.js frontend (production)
│   ├── aurity-desktop/  # Tauri desktop app
│   └── fi-monitor/      # Windows monitor app
└── .claude/
    ├── CLAUDE.md        # This file (quick reference)
    └── rules/           # 📚 Detailed docs by topic
```

## 🔗 Quick Links

- **Production:** https://app.aurity.io
- **Backend:** https://app.aurity.io/api/
- **Detailed Docs:** `.claude/rules/` (organized by topic)
- **CI/CD:** `.github/workflows/`

## 📚 Documentation Organization

Detailed documentation is organized in `.claude/rules/`:

```
.claude/rules/
├── ci-cd/
│   ├── windows-builds.md     # Debugging journey (8 errors + fixes)
│   ├── github-actions.md     # Workflows, AI Gatekeeper
│   └── deployment.md         # Production deploy
├── development/
│   ├── bernard-workflow.md   # 🎯 How to work with Bernard
│   ├── git-workflow.md       # 2-branch model (dev/main)
│   ├── python-314.md         # Python 3.14 requirements
│   └── code-style.md         # Conventions, commits
├── security/
│   ├── credentials.md        # ZERO TOLERANCE secret policy
│   ├── ssh-policy.md         # Production access rules
│   └── incidents.md          # Security incident log
├── integrations/
│   ├── browser-mcps.md       # Chrome DevTools, Browser Tools
│   ├── ollama.md             # LLM setup, smoke tests
│   └── cloudflare.md         # Tunnel, observability
└── architecture/
    ├── aurity-cloud.md       # Production topology
    ├── desktop-app.md        # Tauri, PyInstaller
    └── layering.md           # PUBLIC → INTERNAL → WORKER
```

## ⚡ Executive Kernel

- **Single Entry:** PUBLIC → INTERNAL → WORKER (no excepciones)
- **Only PUBLIC routes** bajo `/api/workflows/aurity/*`
- **Append-only** en datos clínicos (HDF5); integridad por sha256
- **Zero trust** entre capas; RBAC Auth0 en ADMIN
- **SLOs explícitos;** observabilidad por defecto; kill-switch listo

## 🌐 Production Environment

- **Live:** https://app.aurity.io/
- **Backend:** https://app.aurity.io/api/
- **SSL:** Let's Encrypt (auto-renew)
- **DNS:** app.aurity.io → 104.131.175.65
- **Topology:** Nginx (SSL) → Next.js (static) + FastAPI (7001)

## 🔑 Core Principles

1. **Bernard Workflow:** Simplicidad, enfoque, no tangentes → Ver `.claude/rules/development/bernard-workflow.md`
2. **Git Flow:** Always work in `dev`, PR to `main` → Ver `.claude/rules/development/git-workflow.md`  
3. **Security:** ZERO TOLERANCE for hardcoded secrets → Ver `.claude/rules/security/credentials.md`
4. **Production:** NO manual edits, CI/CD only → Ver `.claude/rules/security/ssh-policy.md`

## 🐛 Troubleshooting

- **Windows Builds:** Ver `.claude/rules/ci-cd/windows-builds.md`
- **Git Issues:** Ver `.claude/rules/development/git-workflow.md`
- **Security:** Ver `.claude/rules/security/`

### Turbopack Cache (Windows)

**COMANDO SEGURO para limpiar cache:**
```powershell
# 1. Matar SOLO el proceso de Next.js en puerto 9000 (NO todo node.exe)
$pid = (Get-NetTCPConnection -LocalPort 9000 -ErrorAction SilentlyContinue).OwningProcess | Select-Object -First 1
if ($pid) { Stop-Process -Id $pid -Force }

# 2. Limpiar cache
Remove-Item -Recurse -Force .next, .turbo, .swc, node_modules/.cache -ErrorAction SilentlyContinue

# 3. Reiniciar
pnpm dev
```

## 🚫 COMANDOS PROHIBIDOS (Windows)

**NUNCA usar estos comandos - matan TODAS las instancias de Claude Code:**

```powershell
# ❌ PROHIBIDO - Mata TODO node.exe incluyendo Claude Code
taskkill /F /IM node.exe

# ❌ PROHIBIDO - Mismo efecto destructivo
Stop-Process -Name node -Force
Get-Process node | Stop-Process -Force
```

**Por qué es peligroso:** Claude Code corre sobre Node.js. Matar `node.exe` indiscriminadamente destruye:
- Todas las sesiones de Claude Code activas
- Todos los servidores de desarrollo (Next.js, Vite, etc.)
- Cualquier herramienta basada en Node.js

**Alternativa SEGURA - Matar proceso por puerto específico:**
```powershell
# Matar SOLO el proceso en puerto 9000
$pid = (Get-NetTCPConnection -LocalPort 9000 -ErrorAction SilentlyContinue).OwningProcess | Select-Object -First 1
if ($pid) { Stop-Process -Id $pid -Force; Write-Host "Killed PID $pid" } else { Write-Host "No process on port 9000" }
```

**Claude DEBE:**
- Matar procesos por PUERTO específico, no por nombre de proceso
- NUNCA usar `taskkill /F /IM node.exe` bajo ninguna circunstancia
- Preguntar al usuario antes de matar cualquier proceso si hay duda

## 🏷️ Conventions

- **Commits:** Conventional Commits (feat/fix/docs/chore)
- **Branches:** dev (work) + main (production only)
- **PRs:** Require AI Gatekeeper (GPT-5) approval
- **Docs:** Keep CLAUDE.md brief, details in `.claude/rules/`

## 🚫 EMOJIS PROHIBIDOS EN CÓDIGO

**REGLA:** NUNCA usar emojis en código TypeScript/JavaScript. SIEMPRE usar iconos de Lucide.

**Por qué:**
- Emojis se renderizan diferente en cada OS/navegador
- No son accesibles (screen readers)
- No son estilizables (color, tamaño, stroke)
- Lucide icons son consistentes y profesionales

**Librería:** `lucide-react` (ya instalada)

**Mapeos centralizados en `lib/icons/`:**
```typescript
// Importar desde mapeos centralizados
import { getMedicalServiceIcon, getCheckinActionIcon } from '@/lib/icons';

// O importar iconos directamente
import { Stethoscope, Brain, ClipboardList } from 'lucide-react';
```

**Archivos de iconos disponibles:**
- `lib/icons/medical-icons.ts` - Iconos médicos/clínicos
- `lib/icons/checkin-icons.ts` - Iconos de check-in
- `lib/icons/ui-icons.ts` - Iconos generales de UI
- `lib/icons/dynamic-icons.ts` - Mapeo dinámico por key

**Ejemplo INCORRECTO:**
```typescript
// ❌ PROHIBIDO
const services = [
  { icon: '🩺', name: 'Consulta' },
  { icon: '💉', name: 'Vacunación' },
];
```

**Ejemplo CORRECTO:**
```typescript
// ✅ CORRECTO
import { Stethoscope, Syringe } from 'lucide-react';

const services = [
  { icon: Stethoscope, name: 'Consulta' },
  { icon: Syringe, name: 'Vacunación' },
];

// Renderizar:
<service.icon className="w-6 h-6" strokeWidth={1.5} />
```

**Excepciones permitidas:**
- Archivos `.md` (documentación)
- Console.log para debugging (baja prioridad migrar)

**Claude DEBE:**
- Usar Lucide icons para TODA iconografía en UI
- Buscar en `lib/icons/` antes de importar directamente
- Agregar nuevos iconos al mapeo centralizado si no existen
- NUNCA escribir emojis en código de renderizado

## 📸 Verificación Visual Obligatoria

**REGLA:** Cuando Claude declare que algo "funciona" o "está arreglado", DEBE:

1. Tomar screenshot usando CDP:
   ```bash
   node scripts/screenshot-cdp.mjs <URL> <output.png>
   ```

2. **ABRIR el screenshot para que el USUARIO lo vea** (no solo leerlo con Read):
   ```powershell
   Start-Process <output.png>
   ```

**IMPORTANTE:**
- `Read(archivo.png)` → Solo Claude ve la imagen (el usuario NO la ve)
- `Start-Process archivo.png` → Abre el visor de Windows (el usuario SÍ la ve)

**Claude DEBE usar Start-Process para que Bernard vea los screenshots.**

**NO celebrar fixes sin evidencia visual.** Screenshots > palabras.

## 🚨 Cuadro Rojo de Next.js = ALARMA

**DESPUÉS de cada cambio de código, Claude DEBE verificar errores automáticamente:**

```bash
# 1. Verificar errores de consola (OBLIGATORIO)
node scripts/check-console-errors.mjs http://localhost:9000/<ruta>

# 2. Si hay errores críticos → ARREGLAR antes de continuar
# 3. Si no hay errores → Tomar screenshot y abrirlo para el usuario
node scripts/screenshot-cdp.mjs <URL> <output.png>
powershell -Command "Start-Process '<output.png>'"
```

**Errores críticos (DEBEN arreglarse):**
- `Maximum update depth exceeded` → Loop infinito en useEffect
- `Hydration mismatch` → Server/client rendering diferente
- `Cannot read property` → Null reference
- `TypeError` / `ReferenceError` → Bug de código

**Errores ignorables:**
- `ERR_CONNECTION_REFUSED` → Backend no corriendo (normal en dev frontend-only)

**Claude NO debe:**
- Preguntarle al usuario si hay errores (Claude debe verificar solo)
- Ignorar el cuadro rojo
- Commitear código con errores
- Declarar "funciona" sin verificar consola

**Claude DEBE:** Verificar errores automáticamente, arreglarlos, y solo entonces mostrar screenshot.

---

**Este kernel context existe para que cualquier persona (humana o máquina) entienda cómo se mueve el sistema en 2 minutos: entradas, límites, garantías y rutas de escape.**

**Para detalles específicos, ver `.claude/rules/` organizado por tema.**
