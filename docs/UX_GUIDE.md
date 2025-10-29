# UX Guide - Free Intelligence

**Card**: FI-UX-STR-001
**Axioma**: Humano = App en Beta
**Owner**: UX/Product Team
**Version**: 1.0.0
**Date**: 2025-10-29

---

## Filosofía UX

> _"El usuario final nunca sale de iteración"_

Free Intelligence diseña para humanos en **beta perpetua**: olvido, distracción, cambio de intención son features, no bugs. El onboarding no termina en Day 1; es un proceso continuo de re-discovery.

---

## Principios de Diseño

### 1. **Sin Spoilers, Pero Con Guía**

**Concepto**: No abrumar con info anticipada, pero proveer ayuda contextual cuando se necesita.

**Implementación**:
- Tooltips activados por hover (no invasivos)
- "?" icon junto a features complejos
- Progressive disclosure: mostrar opciones avanzadas solo cuando usuario está listo
- Onboarding modular: 3 steps iniciales (identidad, primer corpus, export test)

**Anti-patterns**:
- ❌ Video tutorial de 10 min en primera pantalla
- ❌ Modal con 5 pantallas de features
- ❌ Wizard bloqueante

---

### 2. **Feedback Loops Continuos**

**Concepto**: Cada acción debe tener respuesta inmediata y clara.

**Implementación**:
- **Write success**: Toast notification con hash prefix
- **Export progress**: Barra de progreso + ETA
- **Verify result**: Badges visuales (✅ OK, ⚠️ FAIL, ⏳ PENDING)
- **Timeline load**: Skeleton UI mientras carga

**Ejemplo**:
```tsx
// After ingestion success
toast.success(`Saved! Hash: ${hash.slice(0, 12)}...`, {
  action: {
    label: "View in Timeline",
    onClick: () => router.push(`/timeline/${sessionId}`)
  }
})
```

**Timing**:
- Optimistic UI: mostrar cambio instantáneamente
- Revert si API falla (con explicación clara)
- Latencia >500ms: mostrar spinner/skeleton

---

### 3. **Undo/Redo Obligatorio**

**Concepto**: Humano = Beta significa errores constantes. Facilitar reversión.

**Implementación**:
- Todas las mutaciones deben ser undoable (excepto export, que es append-only)
- Shortcut: Cmd/Ctrl+Z (undo), Cmd/Ctrl+Shift+Z (redo)
- Visual: snackbar con "Undo" button (5 sec timeout)

**Scope**:
- ✅ Session creation
- ✅ Tag assignment
- ✅ Pin/unpin
- ❌ Export (immutable por policy)

---

### 4. **Accesibilidad AA (WCAG 2.1)**

**Rationale**: Beta perpetua aplica también a usuarios con disabilities. Diseñar para edge cases mejora experiencia para todos.

**Checklist**:
- [ ] Contrast ratio ≥4.5:1 (text vs background)
- [ ] Keyboard navigation completa (Tab, Enter, Esc)
- [ ] Screen reader compatible (ARIA labels)
- [ ] Focus indicators visibles (outline)
- [ ] Font size ≥16px (body text)
- [ ] No info transmitida solo por color

**Testing**:
- axe DevTools (Chrome extension)
- NVDA/JAWS screen reader test
- Keyboard-only navigation audit

---

## Onboarding Flow

### **Phase 1: Identity Setup (1 min)**

**Goal**: Establecer identidad del usuario (email/username)

**UI**:
```
┌────────────────────────────────────────┐
│  Welcome to Free Intelligence          │
│                                        │
│  Let's get started. What should we    │
│  call you?                             │
│                                        │
│  [________________] (Email or username)│
│                                        │
│  [Continue]                            │
└────────────────────────────────────────┘
```

**Validation**:
- Email format OR username (alphanumeric + underscore)
- No passwords (local-first, no auth needed)

**Next**: Phase 2

---

### **Phase 2: First Corpus (2 min)**

**Goal**: Crear primer session y escribir una interaction

**UI**:
```
┌────────────────────────────────────────┐
│  Your First Session                    │
│                                        │
│  Let's create your first session.     │
│  Think of it as a conversation thread. │
│                                        │
│  Session name: [________________]      │
│                                        │
│  What's your first thought?            │
│  [                                   ] │
│  [                                   ] │
│                                        │
│  [Create Session]                      │
└────────────────────────────────────────┘
```

**Backend**:
- POST /api/ingest/interaction
- Return session_id + interaction_id + hash

**Next**: Phase 3

---

### **Phase 3: Export Test (1 min)**

**Goal**: Validar que usuario entiende export flow

**UI**:
```
┌────────────────────────────────────────┐
│  Export Your Data                      │
│                                        │
│  Free Intelligence stores everything   │
│  locally. You can export anytime.      │
│                                        │
│  Let's try exporting your first        │
│  session.                               │
│                                        │
│  Format: ◉ JSON  ○ HDF5  ○ Markdown   │
│                                        │
│  [Export]                              │
└────────────────────────────────────────┘
```

**Backend**:
- POST /api/export/session
- Return manifest + file download

**Success**:
- Toast: "Exported! Saved to Downloads/"
- Show hash prefix for verification

**Completion**: Redirect to Timeline

---

## Microcopys

### **Tone**: Technical but friendly, no corporate fluff

### **Examples**:

**Empty Timeline**:
```
No sessions yet.

Create your first session to start tracking thoughts.

[+ New Session]
```

**Export Progress**:
```
Exporting session_20251029_140530...
Generating manifest... ✅
Computing hashes... 🔄 (2/5)
Writing to disk... ⏳

ETA: 3 seconds
```

**Verify Success**:
```
✅ Session verified!

Hash: a3f7d8e2... (verified)
Policy: Compliant
Audit: Logged

[View in Timeline]
```

**Error Handling**:
```
⚠️ Export failed

Reason: Disk full (90% used)
Action: Free up space or change export location

[Retry] [Change Location]
```

---

## Pin/Tag System

### **Concept**: Usuario puede marcar sessions/interactions importantes sin alterar corpus

**Pin** (⭐):
- Sticky to top of Timeline
- Visual indicator (star icon)
- Shortcut: `p` (keyboard)

**Tag** (🏷️):
- Custom labels (e.g., "bug", "idea", "todo")
- Multi-select (una interaction puede tener 3+ tags)
- Filterable en Timeline
- Autocomplete para tags existentes

**UI**:
```
Timeline Item:
┌────────────────────────────────────────┐
│ ⭐ user_message · 2025-10-29 14:05     │
│ 🏷️ bug, p0                             │
│                                        │
│ "Claude Code no muestra todo items"   │
│                                        │
│ [Pin] [Tag] [Copy] [Verify]           │
└────────────────────────────────────────┘
```

**Backend**:
- Metadata stored in session attributes (not in corpus.h5)
- Persisted locally (IndexedDB or localStorage)

---

## Friday Review (Weekly Ritual)

### **Concept**: Humano = Beta requiere rituales de reflexión

**When**: Every Friday 4pm (configurable)

**UI**: Modal notification
```
┌────────────────────────────────────────┐
│  📅 Friday Review                       │
│                                        │
│  This week you created:                │
│  • 12 sessions                         │
│  • 87 interactions                     │
│  • 3 exports                           │
│                                        │
│  Most active sessions:                 │
│  1. session_20251024_093021 (15 items)│
│  2. session_20251027_141207 (12 items)│
│                                        │
│  What went well this week?             │
│  [_______________________________]     │
│                                        │
│  [Save Reflection] [Skip]             │
└────────────────────────────────────────┘
```

**Persistence**:
- Reflections stored as special interaction type (`reflection`)
- Tagged with `friday-review`
- Searchable in Timeline

---

## Accessibility Checklist (AA)

### **Color & Contrast**

- [ ] Text color: `#f8fafc` (slate-50) on `#0f172a` (slate-900) = 17.4:1 ✅
- [ ] Link color: `#60a5fa` (blue-400) on `#0f172a` = 8.1:1 ✅
- [ ] Disabled state: `#64748b` (slate-500) clearly distinguishable

### **Keyboard Navigation**

- [ ] Tab order follows visual flow
- [ ] Focus indicators visible (2px blue outline)
- [ ] Modal traps focus (Esc to close)
- [ ] Shortcuts documented in Help panel (Cmd+/)

### **Screen Readers**

- [ ] All images have alt text
- [ ] Buttons have aria-label (when icon-only)
- [ ] Loading states announced (`aria-live="polite"`)
- [ ] Error messages linked to inputs (`aria-describedby`)

### **Font & Typography**

- [ ] Base font size: 16px (1rem)
- [ ] Headings use semantic HTML (h1, h2, h3)
- [ ] Line height ≥1.5 (body text)
- [ ] No text in images (use HTML+CSS)

### **Motion & Animation**

- [ ] Respect `prefers-reduced-motion` media query
- [ ] Animations <5 seconds
- [ ] No auto-play video/audio

---

## Testing Protocol

### **Manual Testing**

**Smoke Test** (5 min):
1. Load app in private browsing
2. Complete onboarding (3 phases)
3. Create 2 sessions
4. Export 1 session (JSON)
5. Verify export integrity
6. Pin 1 interaction
7. Tag 1 interaction with "test"
8. Trigger Friday review (mock date)

**Acceptance**:
- All 8 steps complete without errors
- Tooltips appear on hover
- Keyboard shortcuts work
- Screen reader announces key actions

### **Automated Testing**

**Tools**:
- Playwright (E2E)
- axe-core (accessibility)
- Lighthouse (performance + a11y)

**Test Suite**:
```bash
# E2E
pnpm test:e2e

# Accessibility
pnpm test:a11y

# Lighthouse (CI)
lighthouse http://localhost:9000 --chrome-flags="--headless"
```

**CI Requirements**:
- Lighthouse accessibility score ≥90
- axe violations = 0 (errors)
- Playwright tests 100% pass

---

## Implementation Notes

### **Tech Stack**

- **Frontend**: Next.js 14 + React 19 + Tailwind CSS
- **State**: Zustand (session management)
- **Forms**: React Hook Form + Zod validation
- **Notifications**: Sonner (toast library)
- **Icons**: Lucide React

### **File Structure**

```
apps/aurity/
  app/
    onboarding/
      page.tsx          # Onboarding flow (3 phases)
    timeline/
      page.tsx          # Timeline with pin/tag
  components/
    ui/
      tooltip.tsx       # Tooltip component
      toast.tsx         # Toast notifications
  lib/
    onboarding.ts       # Onboarding state machine
```

---

## Next Steps

**Immediate** (Sprint 44):
1. Wireframe onboarding flow (3 phases) - Figma
2. Implement Phase 1 (Identity Setup) - Next.js
3. Accessibility audit with axe DevTools
4. Write microcopys in `lib/microcopys.ts`

**Future Sprints**:
- Phase 2 + 3 implementation
- Friday Review automation
- Pin/Tag system backend
- Lighthouse CI integration

---

## References

- **Axioma**: `docs/PHILOSOPHY_CORPUS.md` (Humano = App en Beta)
- **Mapping**: `docs/PHI_MAPPING.md` (Axiom 2)
- **WCAG 2.1 AA**: https://www.w3.org/WAI/WCAG21/quickref/?currentsidebar=%23col_customize&levels=aa
- **Tailwind Dark Mode**: https://tailwindcss.com/docs/dark-mode

---

_"El usuario nunca termina de aprender. El onboarding nunca termina."_
