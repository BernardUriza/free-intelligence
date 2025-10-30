# 📋 Timeline SessionHeader - Tarjetas Trello Creadas

**Fecha**: 2025-10-29
**Total**: 8 tarjetas (2 P0, 5 P1, 1 P2)
**Card Base**: FI-UI-FEAT-100 (SessionHeader Component)

## 🔴 P0 - Sprint (Due: 31-oct / 01-nov)

### 1. [P0][Backend] Verificar Timeline API CORS y conectividad
- **ID**: `6902309f65337fe0a2341213`
- **Lista**: 🚀 Sprint
- **Due**: 2025-10-31
- **Labels**: P0 (red), Core (blue)
- **Contexto**: API corriendo en port 9002, necesita CORS para localhost:3000/9000
- **AC**: Health check OK, policy_badges retornan desde backend
- **Código relacionado**:
  - `backend/timeline_api.py` (port 9002)
  - `lib/api/timeline.ts:10-11` (NEXT_PUBLIC_TIMELINE_API_URL)
  - `lib/api/timeline.ts:182-197` (healthCheck)

### 2. [P0][Testing] Validar performance <100ms metadata load
- **ID**: `690230a0d1d46767b200ae7a`
- **Lista**: 🚀 Sprint
- **Due**: 2025-11-01
- **Labels**: P0 (red), Observability (purple)
- **Contexto**: Performance.now() ya implementado en page.tsx:93-95
- **AC**: 10 requests, p95 <100ms confirmado, métricas documentadas
- **Código relacionado**:
  - `app/timeline/page.tsx:67` (loadTime state)
  - `app/timeline/page.tsx:93-95` (performance.now measurement)
  - `app/timeline/page.tsx:142-150` (UI display con threshold)

---

## 🟠 P1 - Backlog (Due: 01-nov / 02-nov)

### 3. [P1][UI] Validar copy-to-clipboard en SessionHeader
- **ID**: `6902309cabf2307611d873c4`
- **Lista**: 📥 Backlog
- **Due**: 2025-11-01
- **Labels**: P1 (orange), GTM (pink)
- **Contexto**: Ya implementado con handleCopy(), feedback ✓ por 2s
- **AC**: Copy session_id + owner_hash, console logs, fallback funciona
- **Código relacionado**:
  - `SessionHeader.tsx:31-37` (handleCopy function)
  - `SessionHeader.tsx:54` (copy session_id button)
  - `SessionHeader.tsx:77` (copy owner_hash button)
  - `lib/utils/clipboard.ts` (copyToClipboard utilities)

### 4. [P1][UI] Validar colapso responsivo móvil
- **ID**: `6902309e84d8ef73f5fa0f82`
- **Lista**: 📥 Backlog
- **Due**: 2025-11-01
- **Labels**: P1 (orange), GTM (pink)
- **Contexto**: isExpanded state ya implementado, botón ▼/▶ md:hidden
- **AC**: Collapse funciona en <768px, siempre visible en desktop
- **Código relacionado**:
  - `SessionHeader.tsx:29` (isExpanded useState)
  - `SessionHeader.tsx:91-97` (toggle button md:hidden)
  - `SessionHeader.tsx:122-124` (conditional grid rendering)

### 5. [P1][DevOps] Configurar .env.local con NEXT_PUBLIC_TIMELINE_API_URL
- **ID**: `690230a03e2e96f1fb2caf02`
- **Lista**: 📥 Backlog
- **Due**: 2025-10-31
- **Labels**: P1 (orange), Core (blue)
- **Contexto**: Variable leída en timeline.ts:10-11, default localhost:9002
- **AC**: .env.local creado, documentado en README, hot reload funciona
- **Archivos a crear/modificar**:
  - `apps/aurity/.env.local` (crear)
  - `aurity/modules/fi-timeline/README.md` (actualizar)
  - `apps/aurity/.gitignore` (verificar .env.local)

### 6. [P1][Testing] Smoke tests Timeline API ↔ UI integration
- **ID**: `690230a133057ce421878eff`
- **Lista**: 📥 Backlog
- **Due**: 2025-11-02
- **Labels**: P1 (orange), Observability (purple)
- **Contexto**: 5 casos: happy path, API down, 404, timeout, CORS
- **AC**: Todos los casos probados, fallback funciona, console logs claros
- **Código relacionado**:
  - `app/timeline/page.tsx:71-118` (useEffect con error handling)
  - `lib/api/timeline.ts` (5 API functions)

### 7. [P1][Docs] Actualizar documentación SessionHeader + API setup
- **ID**: `690230a36214ed9e6fdd7465`
- **Lista**: 📥 Backlog
- **Due**: 2025-11-02
- **Labels**: P1 (orange), GTM (pink)
- **Contexto**: README existe con 250 líneas, falta backend setup
- **AC**: Getting Started, env vars, troubleshooting section completa
- **Archivo a actualizar**:
  - `aurity/modules/fi-timeline/README.md`
  - Agregar secciones: Backend Setup, Environment Variables, Troubleshooting

---

## 🟡 P2 - Backlog (Due: 05-nov)

### 8. [P2][Testing] Unit tests clipboard utilities
- **ID**: `690230a2ab5a0d442c50aa99`
- **Lista**: 📥 Backlog
- **Due**: 2025-11-05
- **Labels**: P2 (yellow), Core (blue)
- **Contexto**: 4 funciones en clipboard.ts, fallback a execCommand
- **AC**: 5 tests mínimo, coverage >80%, mocks correctos
- **Archivos a crear**:
  - `lib/utils/__tests__/clipboard.test.ts`
- **Tests requeridos**:
  1. copyToClipboard con navigator.clipboard
  2. copyToClipboard con fallback execCommand
  3. copySessionId label formatting
  4. copyOwnerHash hash completo
  5. Error handling cuando todo falla

---

## 📊 Resumen

| Prioridad | Cantidad | Lista | Due Range |
|-----------|----------|-------|-----------|
| P0 | 2 | 🚀 Sprint | 31-oct → 01-nov |
| P1 | 5 | 📥 Backlog | 01-nov → 02-nov |
| P2 | 1 | 📥 Backlog | 05-nov |

**Total**: 8 tarjetas creadas con contexto del código actual

## 🎯 Próximos Pasos

1. **Hoy (29-oct)**: Trabajar en P0 #1 (CORS) y P0 #2 (Performance)
2. **Mañana (30-oct)**: P1 #5 (.env.local setup)
3. **01-nov**: Validación UI (P1 #3, #4)
4. **02-nov**: Testing & Docs (P1 #6, #7)
5. **05-nov**: Unit tests (P2 #8)

## 📝 Notas

### Estado Actual de FI-UI-FEAT-100
- ✅ **Completado** (moved to Done)
- SessionHeader implementado con todas las features base
- Copy-to-clipboard implementado
- Responsive collapse implementado
- Timeline API integration implementado
- Performance monitoring implementado

### Pendientes de Validación
Estas 8 tarjetas cubren:
- Validación manual de features implementadas
- Testing E2E y unitario
- Configuración de entorno
- Verificación de performance
- Documentación completa

### Workflow Cumplido
- ⚠️ REGLA CRÍTICA: In Progress NO quedó vacío
- FI-UI-FEAT-100 movido a Done
- Siguiente card (FI-DATA-FEAT-002) ya está en In Progress
- Sprint tiene 2 P0 nuevas priorizadas

---

**Generado**: 2025-10-29
**Card origen**: FI-UI-FEAT-100 (6901b1b1fdbfc65236b80c0f)
**Commits**:
- 255ee5e (submodule SessionHeader complete)
- 5d6bd2e (main repo submodule update)
- c214530 (pre-commit hook fix)
