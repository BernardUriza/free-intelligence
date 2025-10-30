# 🎯 Timeline Operativo: Roadmap Completo (FI-UI-FEAT-100 a 119)

**Fecha**: 2025-10-29
**Objetivo**: Transformar timeline de listado simple a cockpit forense auditable production-grade
**Duración**: 120 horas (~7 semanas con 2 FE devs)
**Cards**: 19 (7 P0 Sprint A + 12 P1 Sprint B)

---

## 📊 Resumen Ejecutivo

### Visión
> De listado básico a **tablero forense auditable** con integridad verificable, búsqueda <300ms, export con procedencia, y accesibilidad AA.

### Métricas Objetivo
- **Performance**: Búsqueda ≤2s, detalle p95 <300ms, 1000 items sin jank
- **Integridad**: 100% sesiones con Hash/Policy/Redaction verificables
- **Accesibilidad**: WCAG 2.1 AA (axe + WAVE clean)
- **Usabilidad**: SUS ≥72, success rate ≥80%
- **Export**: 3+ formatos (MD, PDF, JSON) con procedencia

---

## 📋 BLOQUE P0: FUNDAMENTOS (Sprint A, 40 horas)

### Cards Sprint A (7 cards P0)

| # | Card | Descripción | Est | Status |
|---|------|-------------|-----|--------|
| **100** | Encabezado Contextual | Session ID, timespan, size, policy badges, sticky header | 6h | 📥 Backlog |
| **101** | Chips de Métrica | Tokens in/out, latency, provider, cache hit por interacción | 8h | 📥 Backlog |
| **103** | Búsqueda y Filtros | Full-text <300ms, filtros (date/tag/provider/tokens), URL persist | 8h | 📥 Backlog |
| **104** | Panel Metadatos | 11 campos procedencia (hashes, manifest, redaction, timestamps) | 6h | 📥 Backlog |
| **108** | Virtualización | react-window, 1000 items sin jank, 60fps, memory <100MB | 6h | 📥 Backlog |
| **111** | Accesibilidad AA | WCAG 2.1, keyboard nav (J/K/G/E/C/V), ARIA, screen reader | 8h | 📥 Backlog |
| **113** | Badges Integridad | 4 badges (Hash/Policy/Redaction/Signature) con estados OK/FAIL/PENDING | 6h | 📥 Backlog |

**Total Sprint A**: 48h estimadas (realista: ~40h con 2 devs)

### Hitos Sprint A
- **Día 7**: Demo P0 (listing + KPIs + export básico)
- **Criterios**: Búsqueda rápida, detalle <300ms, integridad 100%, a11y AA

---

## 🎯 BLOQUE P1: SUPERPOTENCIAS (Sprint B, 60 horas)

### Cards Sprint B (12 cards P1)

| # | Card | Descripción | Est | Status |
|---|------|-------------|-----|--------|
| **102** | Navegación Pro | Atajos teclado (9), mini-seekbar deslizable con microviz | 8h | 📥 Backlog |
| **105** | Copy/Export Procedencia | Copy w/ provenance (MD), Export session (MD/PDF/JSON) con pie | 6h | 📥 Backlog |
| **106** | Toggle Sin Spoilers | Oculta summaries/raw text, muestra metadata/badges/hashes parciales | 4h | 📥 Backlog |
| **107** | Diff Prompt/Respuesta | Modal comparador side-by-side, stats (add/remove/change), copy diff | 6h | 📥 Backlog |
| **110** | Acciones Rápidas | Context menu ⋯ con 5 acciones (Export/Verify/Hold/Pin/Delete) | 5h | 📥 Backlog |
| **112** | Permalink Interacción | Shortlink shareable, copy/markdown/QR, scroll to interaction | 4h | 📥 Backlog |
| **114** | Instrumentación UI | Métricas p95 render, error rate, eventos (export/copy/verify), dashboard 24h | 6h | 📥 Backlog |
| **115** | Tema y Tipografía | Inter + JetBrains Mono, light/dark theme, localStorage persist | 4h | 📥 Backlog |
| **116** | Bulk Export Rango | Selección rango (all/range/last30m), preview size, export con procedencia | 5h | 📥 Backlog |
| **117** | Marcar/Etiquetar | 3 tags predefinidos (pin/risk/follow_up), filtro por tags, audit log | 4h | 📥 Backlog |
| **118** | Toolbar Sesión | 6 botones globales (Export/Verify/Hold/Policy/Pin/Delete), status bar | 5h | 📥 Backlog |
| **119** | Pruebas Usabilidad | Script 5 tareas, 5 usuarios, SUS questionnaire, feedback doc | 8h | 📥 Backlog |

**Total Sprint B**: 65h estimadas (realista: ~60h)

### Hitos Sprint B
- **Día 21**: Demo P1 + usability testing
- **Criterios**: Navegación pro, export avanzado, UX testing SUS ≥72

---

## 🗓️ Roadmap Integrado (14 semanas)

| Fase | Sem | Cards | Horas | Hito | Entregable |
|------|-----|-------|-------|------|------------|
| **Sprint A** | 1-3 | 100,101,103,104,108,111,113 | 40h | MVP Operable | Listing + búsqueda + integridad |
| **Sprint B** | 4-6 | 102,105,106,107,110,112,114,115,116,117,118,119 | 60h | Tablero Forense | Navegación pro + export avanzado |
| **QA/Polish** | 7 | Perf, a11y, docs | 20h | Release | Production-ready |

**Capacidad Requerida**: 2 FE devs full-time × 7 semanas = 280 horas disponibles
**Horas Sprint**: 120h (43% utilization) → Buffer 160h para code review, testing, blockers

---

## ✅ Definition of Done (DoD Global)

### Performance
- ✅ Búsqueda: ≤2s para 50-100 items
- ✅ Detalle: p95 <300ms para ≤50 eventos
- ✅ Scroll: 60fps estable con 1000 items
- ✅ Memory: <100MB bundle, no leaks
- ✅ First Paint: <500ms

### Integridad
- ✅ 100% sesiones muestran Hash/Policy/Redaction correctos
- ✅ Verify detecta manifest válido/manipulado en <500ms
- ✅ Export incluye procedencia completa

### UX/Accesibilidad
- ✅ WCAG 2.1 AA (axe + WAVE clean)
- ✅ Keyboard nav completa (Tab, J/K, G, E, C, V, /, ?, Esc)
- ✅ Screen reader compatible (NVDA/JAWS)
- ✅ Tooltips contextuales, empty states, error feedback

### Observabilidad
- ✅ Métricas UI (p95 render, errors, eventos)
- ✅ Dashboard 24h con alertas
- ✅ Audit log de acciones críticas

### Usabilidad
- ✅ SUS score ≥72
- ✅ Task success rate ≥80% (5 tareas estándar)
- ✅ Average task time <45s

---

## 🎬 Próximos Pasos Inmediatos

### Hoy (2025-10-29)
- [x] Copiar 19 cards a Trello ✅ **COMPLETADO**
- [x] Aplicar labels P0/P1 + GTM ✅ **COMPLETADO**
- [ ] Backend prep: API routes `/api/sessions/{id}`, `/api/stats/realtime`

### Mañana
- [ ] Frontend dev: FI-UI-FEAT-100 (Encabezado Contextual)
- [ ] Mock data: 30 interacciones de prueba con metadata completa

### Día 2-3
- [ ] FI-UI-FEAT-101 (Chips Métrica) + 103 (Búsqueda/Filtros)
- [ ] Integration testing: búsqueda <300ms con 100 items

### Día 7 (Sprint A Demo)
- [ ] Demo interno: listing + búsqueda + export básico
- [ ] Checkpoint: Performance targets (p95, memory, FPS)

### Día 21 (Sprint B Demo)
- [ ] Usability testing con 5 usuarios (script card 119)
- [ ] SUS questionnaire + feedback doc
- [ ] Go/No-Go decision para release

---

## 📦 Tech Stack

### Frontend
- **Framework**: React 19 + Next.js 14 (App Router)
- **UI**: Tailwind CSS, @headlessui/react
- **Performance**: react-window (virtualization)
- **Diff**: react-diff-view
- **Types**: TypeScript (full coverage)

### Backend (APIs necesarias)
- **FastAPI**: `/api/sessions/{id}`, `/api/interactions`, `/api/verify-hash`, `/api/export`
- **HDF5**: corpus_ops integration
- **Observability**: Prometheus metrics, audit_logs

### Testing
- **E2E**: Playwright (usability script)
- **A11y**: axe DevTools, WAVE
- **Performance**: Lighthouse, DevTools Performance tab
- **Usability**: SUS questionnaire (System Usability Scale)

---

## 💡 Decisiones Técnicas Clave

### 1. Virtualización Obligatoria (card 108)
- **Why**: 1000+ items sin jank
- **How**: react-window FixedSizeList, overscan 5
- **Target**: Memory <100MB, FPS 60

### 2. Búsqueda Local (card 103)
- **Why**: <300ms p95
- **How**: Debounce 300ms, índice local (lunr.js si >500 items)
- **No backend roundtrip** para <500 items

### 3. Export con Procedencia (cards 105, 116)
- **Why**: Audit trail completo
- **How**: MD/PDF con pie (session ID, hashes, manifest ref, owner)
- **Backend**: FastAPI `/export` con reportlab (PDF)

### 4. Accesibilidad First (card 111)
- **Why**: WCAG 2.1 AA mandatory
- **How**: ARIA labels, keyboard nav, focus management, contrast 4.5:1
- **Testing**: axe, WAVE, screen reader

### 5. Observabilidad (card 114)
- **Why**: Product metrics + error monitoring
- **How**: recordMetric, recordEvent, Prometheus pushgateway
- **Dashboard**: p95 render, error_rate, export/copy/verify counts

---

## 🚨 Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| **Performance degradation >1000 items** | Media | Alto | Virtual scroll + lazy render, test con 2000 items |
| **A11y violations detectadas tarde** | Media | Alto | axe + WAVE desde día 1, cada PR |
| **Backend APIs no listas** | Media | Alto | Mock data completo, contract testing |
| **Usability testing falla SUS** | Baja | Medio | Pilot testing con 2 usuarios semana 3 |
| **Export PDF lento (>5s)** | Baja | Medio | Background job + progress modal, async download |

---

## 📊 Métricas de Éxito (KPIs)

### Performance KPIs
- **P95 render time**: ≤127ms (actual) vs <100ms (target)
- **Search response**: <300ms (target)
- **FPS stability**: 60fps (no drops <45fps)
- **Memory footprint**: <100MB (1000 items)

### Quality KPIs
- **axe violations**: 0 (WCAG 2.1 AA)
- **Test coverage**: ≥80% (unit + integration)
- **Error rate**: <0.5% (UI errors logged)

### Adoption KPIs (Post-release)
- **SUS score**: ≥72 (internal users)
- **Task success rate**: ≥80% (5 tareas estándar)
- **Average task time**: <45s (benchmark)
- **Weekly active sessions**: 50+ (clínicos + auditores)

---

## 📚 Recursos Adicionales

### Documentación
- **Spec completa**: Prompt original (este documento base)
- **API contracts**: `/docs/API_CONTRACTS.md` (pendiente)
- **Usability script**: Card 119 description
- **A11y checklist**: Card 111 AC

### Referencias
- WCAG 2.1: https://www.w3.org/WAI/WCAG21/quickref/
- react-window: https://react-window.vercel.app/
- SUS Calculator: https://www.usability.gov/how-to-and-tools/methods/system-usability-scale.html
- axe DevTools: https://www.deque.com/axe/devtools/

---

## ✨ Conclusión

Este roadmap transforma el timeline de AURITY de **listado simple** a **cockpit forense auditable production-grade** en 7 semanas con:

- **7 cards P0** (Sprint A): Fundamentos sólidos (búsqueda, integridad, a11y)
- **12 cards P1** (Sprint B): Superpotencias (navegación pro, export avanzado, UX testing)
- **120 horas** totales (~43% utilization con 2 FE devs)
- **DoD estricto**: Performance, integridad, a11y, usabilidad

**Estado actual**: 19 cards creadas en Trello, labels aplicados (P0/P1 + GTM), listas para Sprint Planning.

**Siguiente acción**: Backend dev prepara APIs → Frontend comienza FI-UI-FEAT-100 (Encabezado Contextual).

---

**¿Comenzamos con FI-UI-FEAT-100?** 🚀

---

*Generado: 2025-10-29*
*Board ID: 68fbfeeb7f8614df2eb61e42*
*Backlog List ID: 690100441851396c1cb143a6*
