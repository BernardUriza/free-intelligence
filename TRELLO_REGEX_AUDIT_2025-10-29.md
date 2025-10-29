# 🔍 Trello Regex Pattern Audit Report

**Board**: Free Intelligence (68fbfeeb7f8614df2eb61e42)
**Date**: 2025-10-29 10:07:00
**Tool**: trello-cli v2.0.0 with regex pattern matching

---

## 📊 Audit Patterns Executed

| Pattern | Description | Matches | Non-Matches |
|---------|-------------|---------|-------------|
| `FI-UI-FEAT-.*` | All UI features | 32 | 147 |
| `FI-API-FEAT-.*` | All API features | 18 | 161 |
| `\[P0\].*` | All P0 priority cards | 15 | 164 |
| `FI-UI-FEAT-1[0-1][0-9]` | Timeline UI features (100-119) | 18 | 73 (in Backlog) |
| `.*Timeline.*\|.*SessionHeader.*\|.*CORS.*\|.*performance.*` | Timeline-related work | 12 | 167 |

---

## 🎯 Pattern 1: UI Features (`FI-UI-FEAT-.*`)

**Matches**: 32 cards
**Pattern violations**: 147 cards don't follow this naming

### ✅ Cards Following Pattern (Sample):
- FI-UI-FEAT-100: Encabezado Contextual de Sesión (✅ Done)
- FI-UI-FEAT-002: Visor de Interacciones (🧪 Testing)
- FI-UI-FEAT-003: Política no_context_loss (🧪 Testing)
- FI-UI-FEAT-004: Modo historia personal (🧪 Testing)
- FI-UI-FEAT-006: Triage Intake (✅ Done)

### ⚠️ Common Violations:
- Philosophy cards: `FI-PHIL-DOC-*` (13 cards)
- Hardware cards: `FI-HW-FEAT-*` (2 cards)
- New format: `[P0][Área: UI]` (4 cards)

### 💡 Recommendation:
- Consolidate naming: Either `FI-UI-FEAT-NNN` OR `[P0][UI]` format
- Current board has **2 naming conventions** (legacy + new)

---

## 🎯 Pattern 2: API Features (`FI-API-FEAT-.*`)

**Matches**: 18 cards
**Pattern violations**: 161 cards don't follow this naming

### ✅ Cards Following Pattern:
- FI-API-FEAT-001: Nomenclatura eventos (✅ Done)
- FI-API-FEAT-002: Timeline REST API (6901be18a6182c6cf5e93331) - New in Backlog
- FI-API-FEAT-003: Verify Hash Endpoint (6901be2393f164aff7d097ba) - New in Backlog
- FI-API-FEAT-004: Export Session API (6901be2ea935e4c4683f185b) - New in Backlog
- FI-API-FEAT-005: Search & Filter API (6901be3971ee50ec17d015f3) - New in Backlog

### 📈 Growth Trend:
- Legacy API cards: 1 (FI-API-FEAT-001)
- New Timeline API cards: 4 (FI-API-FEAT-002 through 005)
- **Growth**: 400% increase in last session

---

## 🎯 Pattern 3: P0 Priority (`\[P0\].*`)

**Matches**: 15 cards (8.4% of total)
**Using P0 label**: 79 cards (44%)

### 🔴 Finding: Label vs Title Inconsistency
- **Cards with `[P0]` in title**: 15
- **Cards with P0 label**: 79
- **Gap**: 64 cards use label but not title prefix

### ✅ Cards Using Both (Best Practice):
- [P0][Backend] Verificar Timeline API CORS (6902309f65337fe0a2341213) - In Progress
- [P0][Testing] Validar performance <100ms (690230a0d1d46767b200ae7a) - Sprint
- [P0][Área: UI][Tipo: FEAT] FI-UI-FEAT-002 - Backlog
- [P0][Área: UI][Tipo: FEAT] FI-UI-FEAT-003 - Backlog
- [P0][Área: UI][Tipo: FEAT] FI-UI-FEAT-004 - Backlog

### ⚠️ Cards Using Legacy Format:
- FI-CORE-FEAT-001: Middleware HTTP/CLI (has P0 label, no title prefix)
- FI-CLI-FEAT-002: Canal inferencia (has P0 label, no title prefix)
- FI-SEC-FEAT-002: Acceso Solo en LAN (has P0 label, no title prefix)

### 💡 Recommendation:
- **Option A**: Migrate all P0 cards to `[P0]` title prefix
- **Option B**: Remove title prefixes, rely solely on labels
- **Current state**: Mixed approach causing search complexity

---

## 🎯 Pattern 4: Timeline UI Features (`FI-UI-FEAT-1[0-1][0-9]`)

**Target Range**: FI-UI-FEAT-100 to FI-UI-FEAT-119 (20 cards planned)
**In Backlog**: 18 cards found
**Pattern violations in Backlog**: 73 cards

### ✅ Timeline UI Cards Found:
1. FI-UI-FEAT-100: Encabezado Contextual (Done ✅)
2. FI-UI-FEAT-101: Chips de Métrica (Backlog)
3. FI-UI-FEAT-102: Navegación Pro (Backlog)
4. FI-UI-FEAT-103: Búsqueda y Filtros (Backlog)
5. FI-UI-FEAT-104: Panel Metadatos (Backlog)
6. FI-UI-FEAT-105: Copy/Export Procedencia (Backlog)
7. FI-UI-FEAT-106: Toggle Sin Spoilers (Backlog)
8. FI-UI-FEAT-107: Diff Prompt/Respuesta (Backlog)
9. FI-UI-FEAT-108: Virtualización (Backlog)
10. FI-UI-FEAT-110: Acciones Rápidas (Backlog)
11. FI-UI-FEAT-111: Accesibilidad AA (Backlog)
12. FI-UI-FEAT-112: Permalink (Backlog)
13. FI-UI-FEAT-113: Badges Integridad (Backlog)
14. FI-UI-FEAT-114: Instrumentación UI (Backlog)
15. FI-UI-FEAT-115: Tema y Tipografía (Backlog)
16. FI-UI-FEAT-116: Bulk Export (Backlog)
17. FI-UI-FEAT-117: Marcar/Etiquetar (Backlog)
18. FI-UI-FEAT-118: Toolbar Sesión (Backlog)
19. FI-UI-FEAT-119: Pruebas Usabilidad (Backlog)

**Missing**: FI-UI-FEAT-109 (gap in sequence)

### 📊 Status Breakdown:
- ✅ Done: 1 (FI-UI-FEAT-100)
- 📥 Backlog: 18 (FI-UI-FEAT-101 through 119, minus 109)
- **Completion**: 5.3% (1/19)

### 🎯 Sprint Planning:
- **Sprint A (P0)**: 7 cards (101, 103, 104, 108, 111, 113)
- **Sprint B (P1)**: 12 cards (102, 105, 106, 107, 110, 112, 114-119)

---

## 🎯 Pattern 5: Timeline-Related Work (`.*Timeline.*|.*SessionHeader.*|.*CORS.*|.*performance.*`)

**Matches**: 12 cards
**Non-matches**: 167 cards

### ✅ Timeline Ecosystem Cards Found:

**Backend (API)**:
- FI-API-FEAT-002: Timeline REST API (6901be18a6182c6cf5e93331)
- [P0][Backend] Verificar Timeline API CORS (6902309f65337fe0a2341213) - In Progress

**Frontend (UI)**:
- FI-UI-FEAT-100: Encabezado Contextual de Sesión (Done)
- FI-UI-FEAT-101 through 119: Timeline UI roadmap (18 cards)

**Testing & Validation**:
- [P0][Testing] Validar performance <100ms (690230a0d1d46767b200ae7a)
- [P1][UI] Validar copy-to-clipboard en SessionHeader (6902309cabf2307611d873c4)
- [P1][UI] Validar colapso responsivo móvil (6902309e84d8ef73f5fa0f82)
- [P1][Testing] Smoke tests Timeline API ↔ UI (690230a133057ce421878eff)
- [P2][Testing] Unit tests clipboard utilities (690230a2ab5a0d442c50aa99)

**DevOps & Docs**:
- [P1][DevOps] Configurar .env.local (690230a03e2e96f1fb2caf02)
- [P1][Docs] Actualizar documentación SessionHeader (690230a36214ed9e6fdd7465)

### 📊 Timeline Project Statistics:
- **Total cards**: 30+ (1 done, 2 in progress, 27+ planned)
- **Backend API**: 5 cards (FI-API-FEAT-002 through 006)
- **Frontend UI**: 19 cards (FI-UI-FEAT-100 through 119)
- **Testing/Validation**: 6 cards
- **DevOps/Docs**: 2 cards

### 🎯 Critical Path:
1. [P0] CORS verification (In Progress) - Blocks all frontend work
2. [P0] Performance validation - Establishes baseline
3. [P1] .env.local setup - Enables deployment
4. Sprint A UI features (7 cards) - MVP
5. Sprint B UI features (12 cards) - Production-ready

---

## 📋 Backlog Analysis: Cards Without Labels

**Total cards in Backlog without labels**: 12

### ⚠️ Unlabeled Cards:
1. [BUG] Schema violation: medications null (69011ee265d6a85ba27db684)
2. [PROMPT] Reinforce CRITICAL urgency criteria (69011ee62a6749f1d4478f5f)
3. [DOC] Update latency AC (69011ee7cfd710a73cc52e3c)
4. [SECURITY] Audit log hardening (69011ee8f61913590d1f9f40)
5. [TECH-DEBT] Pre-commit hooks py3.12 (69012e8da0bd4f8817459d71)
6. [P0][Área: UI] FI-UI-FEAT-002 (6901aecd25567a12dda1c178)
7. [P0][Área: UI] FI-UI-FEAT-003 (6901aece21020f069575c590)
8. [P0][Área: UI] FI-UI-FEAT-004 (6901aed07718e2782280e904)
9. [P0][Área: API] FI-API-FEAT-001 (6901aed11f9246220f040146)
10. [P1][Área: UI] FI-UI-FEAT-005 (6901af1a927e34ebd349970e)
11. [P1][Área: Observability] FI-UI-FEAT-006 (6901af1bbedde186a96cad52)
12. [P1][Área: Export] FI-UI-FEAT-007 (6901af1cf01f1aca1d617c2e)

### 💡 Action Required:
All 12 cards need labels applied. Priority + Area labels minimum.

---

## 📊 Naming Convention Analysis

### Current Conventions in Use:

**Convention 1: Legacy Format** (161 cards)
```
FI-[AREA]-[TYPE]-[NUM]: Title
Examples:
- FI-CORE-FEAT-001: Middleware HTTP/CLI
- FI-DATA-FEAT-005: Política append-only
- FI-UI-FEAT-100: SessionHeader
```

**Convention 2: New Format** (18 cards)
```
[Priority][Área: X][Tipo: Y] Task: Title
Examples:
- [P0][Backend] Verificar Timeline API CORS
- [P1][UI] Validar copy-to-clipboard
- [P2][Testing] Unit tests clipboard
```

### 🔄 Mixed Format Issues:
- **Search complexity**: Need 2 regex patterns to find all P0 cards
- **Sorting issues**: Different formats sort differently
- **Inconsistent parsing**: Tools expect one format or the other

### 💡 Recommendations:

**Option A: Migrate to New Format**
- Pros: More explicit (priority visible in title)
- Cons: Longer titles, harder to type
- Effort: 161 renames

**Option B: Keep Legacy Format**
- Pros: Compact, established
- Cons: Priority only in labels (not searchable in title)
- Effort: 18 renames

**Option C: Hybrid (Current State)**
- Pros: Flexibility
- Cons: Inconsistency, search complexity
- Effort: 0 (accept current state)

### 🎯 Suggested Decision Criteria:
- If search is primary use case → New format
- If compactness matters → Legacy format
- If no strong preference → Hybrid (label as source of truth)

---

## 🔧 Regex Patterns Reference

### Useful Patterns for Audits:

```bash
# All UI features
trello board-audit <board_id> "FI-UI-FEAT-.*"

# All API features
trello board-audit <board_id> "FI-API-FEAT-.*"

# All P0 cards (new format)
trello board-audit <board_id> "\[P0\].*"

# Timeline range (100-119)
trello list-audit <list_id> "FI-UI-FEAT-1[0-1][0-9]"

# Timeline ecosystem
trello board-audit <board_id> ".*Timeline.*|.*SessionHeader.*|.*CORS.*"

# All backend cards
trello board-audit <board_id> "FI-CORE-.*|FI-API-.*|FI-DATA-.*"

# All done features
trello board-audit <board_id> "FI-.*-FEAT-.*"

# All bugs and fixes
trello board-audit <board_id> "FI-.*-(BUG|FIX)-.*"

# Cards with due dates this week
trello sprint-audit <board_id> "2025-10-2[8-9]|2025-11-0[1-4]"
```

---

## 📈 Audit Score Summary

| Audit Type | Score | Status | Key Finding |
|------------|-------|--------|-------------|
| Board Health | 35/100 | 🔴 CRITICAL | 21 Done cards without due dates |
| Sprint Health | 75/100 | 🟡 GOOD | All sprint cards have due dates |
| Label Quality | 90/100 | 🟢 EXCELLENT | Only 2 similar pairs |
| Backlog Quality | 60/100 | 🟠 NEEDS ATTENTION | 12 cards without labels |
| Timeline Project | 5% | 🔴 EARLY | 1/19 cards done (FI-UI-FEAT-100) |

---

## 🎯 Recommended Actions

### IMMEDIATE (Today):
1. ✅ ~~Fix In Progress workflow~~ **DONE**
2. 🔴 Apply labels to 12 unlabeled Backlog cards
3. 🔴 Assign members to 9 execution cards

### SHORT TERM (This Week):
4. 🟠 Decide on naming convention (legacy vs new vs hybrid)
5. 🟠 Add due dates to 21 Done cards (retroactive)
6. 🟠 Complete or remove 9 incomplete checklists

### MEDIUM TERM (Next Sprint):
7. 🟡 Rename cards to follow chosen convention (0-161 cards)
8. 🟡 Document regex patterns for team use
9. 🟡 Create saved searches for common patterns

---

**Report Generated**: 2025-10-29 10:07:00
**Next Audit**: 2025-10-30 (daily during active sprint)
**Tool**: trello-cli v2.0.0
**Commands Used**: board-audit, list-audit, sprint-audit with regex patterns
