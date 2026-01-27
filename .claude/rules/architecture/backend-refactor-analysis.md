# Backend Architecture Analysis (Post 46→6 Refactor)

**Date:** 2026-01-27
**Status:** Partial refactor complete, deep issues remain
**Grade:** B- (functional, improved, but structure needs work)

---

## 📊 Current State (After Refactor)

### Directory Structure
```
backend/
├── core/         297 files (50% of codebase) 🔴 OVERLOADED
├── utils/        122 files
├── tests/         71 files
├── api/           29 files
├── app/            7 files
└── ...
```

### Problem: `core/` is a dumping ground

**What `core/` contains:**
- Domain entities (✅ correct)
- Services (❌ should be separate)
- API routers (❌ should be in `api/`)
- Infrastructure (❌ should be separate)

**Result:** Import paths like:
```python
from backend.core.services.timeline.api.internal.timeline.router import ...
# 7 levels deep = unmaintainable
```

---

## 🔴 Critical Issues

### 1. Import Path Depth (7 levels)

**Top offenders:**
```
core/services/timeline/api/internal/timeline/router.py      (7 levels)
core/services/kpi/api/internal/kpis/router.py               (7 levels)
core/services/transcription/api/internal/transcribe/router  (7 levels)
```

**Impact:**
- Hard to remember import paths
- Refactoring breaks 50+ files per change
- New developers get lost

**Solution:**
```python
# Target structure (max 4 levels):
from backend.services.timeline import TimelineService
from backend.api.routers import timeline_router
```

### 2. Architectural Layering Violation

**Current (wrong):**
```
core/
  services/
    timeline/
      api/          ← API inside service inside core
        internal/
        public/
```

**Correct Clean Architecture:**
```
domain/           # Entities only (Patient, Session, SOAP)
services/         # Business logic (TimelineService)
api/              # HTTP layer (routers)
  public/
  internal/
infrastructure/   # External adapters (HDF5, PostgreSQL)
```

**Why it matters:**
- Domain should NOT depend on services
- Services should NOT depend on API
- API should import from services, not vice versa

### 3. Module Distribution Imbalance

| Layer | Files | Expected | Status |
|-------|-------|----------|--------|
| `core/` | 297 | ~50 | 🔴 6x oversized |
| `services/` | 1 | ~80 | 🔴 Empty |
| `api/` | 29 | ~40 | ✅ OK |
| `utils/` | 122 | ~60 | ⚠️ 2x oversized |

---

## 🎯 Recommended Structure (Target State)

```
backend/
├── domain/              # Pure domain entities (no dependencies)
│   ├── patient/
│   │   ├── entity.py        # Patient dataclass
│   │   └── repository.py    # Interface (ABC)
│   ├── session/
│   │   ├── entity.py
│   │   └── repository.py
│   └── soap/
│
├── services/            # Business logic (domain orchestration)
│   ├── timeline/
│   │   ├── service.py       # TimelineService class
│   │   └── types.py         # DTOs
│   ├── transcription/
│   │   ├── service.py
│   │   └── adapters/        # LLM/STT adapters
│   └── soap/
│
├── api/                 # HTTP layer (thin controllers)
│   ├── public/
│   │   └── workflows/
│   │       ├── timeline.py  # Router (imports TimelineService)
│   │       └── soap.py
│   └── internal/
│       ├── transcribe.py
│       └── kpis.py
│
├── infrastructure/      # External system adapters
│   ├── storage/
│   │   ├── hdf5/
│   │   └── postgres/
│   ├── events/
│   └── workers/
│
├── utils/               # Shared utilities (helpers only)
│   ├── common/          # Logger, config
│   └── metrics/
│
└── app/                 # Application bootstrap
    ├── main.py
    └── routers.py
```

---

## 📈 Migration Strategy (Gradual)

### Phase 1: Extract Services from `core/` (1 week)
```bash
# Move service logic out of core/services/ → services/
git mv backend/core/services/timeline backend/services/timeline
git mv backend/core/services/soap backend/services/soap
# Repeat for all services
```

### Phase 2: Separate API from Services (1 week)
```bash
# Move routers from services/ → api/
git mv backend/services/timeline/api backend/api/routers/timeline
# Update imports
```

### Phase 3: Extract Domain Entities (1 week)
```bash
# Move entities from core/ → domain/
git mv backend/core/domain/patient backend/domain/patient
# Repeat
```

### Phase 4: Refactor Infrastructure (1 week)
```bash
# Move storage/events from core/ → infrastructure/
git mv backend/core/infrastructure backend/infrastructure
```

---

## 🚀 Quick Wins (Can Do Today)

### 1. Document Current Architecture ✅ DONE
- Created this analysis document
- Identified 3 critical issues
- Documented target structure

### 2. Create Import Aliases ✅ DONE (15 min)
```python
# backend/__init__.py
from backend import get_logger        # vs backend.utils.common.logging.logger
from backend import SessionsStore     # vs backend.core.infrastructure.storage...
```

### 3. Add __all__ to Key Modules ✅ DONE (30 min)
```python
# backend/core/services/soap/__init__.py
from .services.soap_generation_service import SOAPGenerationService
__all__ = ["SOAPGenerationService"]
```

**Completed modules:**
- soap, transcription, llm, workflow, tts, kpi, checkin, evidence, export

**Benefits:**
- IDE autocomplete shows only public APIs
- Documents intended API surface
- Prevents accidental dependencies on internal classes

### 4. Dependency Graph Visualization ✅ DONE (1 hour)
```bash
# Graph generated at .claude/rules/architecture/backend-deps-graph.svg
open .claude/rules/architecture/backend-deps-graph.svg
```

**Key findings from graph:**
- **185 modules** with dependencies
- **428 total edges** (dependencies)
- **Top importers:**
  - `app.routers` → 12 dependencies (orchestration layer)
  - `utils.common.infrastructure` → 12 dependencies (shared utilities)
  - `core.infrastructure.workers` → 12 dependencies (background jobs)
  - `core.services.llm` → 11 dependencies (LLM integrations)
  - `app.main` → 10 dependencies (FastAPI bootstrap)

**Visual insights:**
- Color-coded by layer (core=red, api=blue, app=green, utils=yellow)
- Clear clusters show tight coupling within services
- Cross-layer dependencies visible (some violations of Clean Architecture)

---

## 📊 Metrics

### Before Refactor (46 modules)
- Deepest import: 9 levels
- Circular imports: Unknown
- Avg module size: ~500 LOC

### After Refactor (6 layers)
- Deepest import: 7 levels (-2) ✅
- Circular imports: 0 (detected) ✅
- Avg module size: ~300 LOC ✅

### Target (Clean Architecture)
- Deepest import: 4 levels (-3 more)
- Module count: ~150 files (vs 297 in core/)
- Clear layer boundaries (domain/services/api/infra)

---

## 🎓 Key Learnings

1. **46 → 6 was good first step** - eliminated `fi_*` chaos
2. **But `core/` became new dumping ground** - need further split
3. **Import depth is symptom, not root cause** - fix layering first
4. **Migration must be gradual** - can't break prod for weeks

---

## 🔗 References

- [Clean Architecture (Uncle Bob)](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Python Layered Architecture](https://stackoverflow.com/questions/47778544/python-layered-architecture)
- [Dependency Inversion Principle](https://en.wikipedia.org/wiki/Dependency_inversion_principle)

---

**Next Steps:**
1. Review this doc with team
2. Agree on target structure
3. Execute Phase 1 (extract services)
4. Measure import depth improvement
