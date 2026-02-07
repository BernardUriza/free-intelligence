# Developer Tooling Scripts

Herramientas para mantener la calidad y arquitectura del backend.

**Creado:** 2026-02-02 (P4-1 Holoceno Temprano - Developer Tooling)

---

## 📋 Herramientas Disponibles

### 1. check-imports.py - Validación de Arquitectura

Detecta violaciones de Clean Architecture verificando imports entre capas.

**Uso:**
```bash
# Verificación básica
python backend/scripts/check-imports.py

# Con sugerencias de corrección
python backend/scripts/check-imports.py --fix-suggestions
```

**Reglas validadas:**
- ❌ API no debe importar core/ (deprecado)
- ❌ Domain no debe importar API (inversión de dependencias)
- ❌ Services no debe importar API (independencia de HTTP)
- ❌ Repositories no deben importar services (DIP)
- ❌ Mappers no deben importar API (transformación pura)

**Exit codes:**
- 0: Sin violaciones
- 1: Violaciones detectadas

---

### 2. validate-di-usage.py - Detección de Service Locator

Detecta uso del anti-pattern service locator (get_container()).

**Uso:**
```bash
# Verificación normal (excluye tests, scripts)
python backend/scripts/validate-di-usage.py

# Modo estricto (valida todo)
python backend/scripts/validate-di-usage.py --strict
```

**Detecta:**
- `get_container()` calls
- `container.some_service` accesos directos
- Imports de container en API layer

**Patrón correcto:**
```python
# ❌ Service Locator (anti-pattern)
def create_session():
    container = get_container()
    session_service = container.session_service
    return session_service.create(...)

# ✅ Dependency Injection (correcto)
def create_session(
    session_service: SessionService = Depends(get_session_service)
):
    return session_service.create(...)
```

**Exit codes:**
- 0: No service locator usage
- 1: Service locator detectado

---

### 3. analyze-file-sizes.py - Análisis de Complejidad

Detecta archivos que exceden límites de tamaño recomendados.

**Uso:**
```bash
# Análisis básico
python backend/scripts/analyze-file-sizes.py

# Mostrar top 20 archivos más grandes
python backend/scripts/analyze-file-sizes.py --top 20

# Custom threshold
python backend/scripts/analyze-file-sizes.py --threshold 400
```

**Límites recomendados:**
- Infrastructure: 300 líneas
- Services: 400 líneas
- Repositories: 350 líneas
- API routers: 250 líneas
- Mappers: 200 líneas
- General: 500 líneas

**Output:**
```
⚠️  Found 61 file(s) exceeding size limits:

📄 providers/llm.py
   Lines: 1186 (limit: 500, +686 lines, +137%)
   Layer: other
   💡 Consider splitting into smaller modules (target: <500 lines)
```

**Exit codes:**
- 0: Todos los archivos OK
- 1: Archivos exceden límites (warning)

---

### 4. generate-dependency-graph.py - Visualización de Dependencias

Genera grafos de dependencias entre módulos.

**Uso:**
```bash
# Reporte textual
python backend/scripts/generate-dependency-graph.py

# JSON para análisis programático
python backend/scripts/generate-dependency-graph.py --format json

# Graphviz DOT format
python backend/scripts/generate-dependency-graph.py --format dot > deps.dot

# Visualizar con graphviz (requiere graphviz instalado)
python backend/scripts/generate-dependency-graph.py --format dot | dot -Tpng > deps.png

# Filtrar por capa
python backend/scripts/generate-dependency-graph.py --layer services
```

**Output formats:**
- `text`: Reporte textual legible
- `json`: JSON estructurado con estadísticas
- `dot`: Graphviz para visualización gráfica

**Detecta:**
- Dependencias circulares
- Módulos altamente acoplados
- Estructura de capas

**Exit codes:**
- 0: Siempre (informacional)

---

## 🔄 Integración con CI/CD

### GitHub Actions

Agregar a `.github/workflows/architecture-lint.yml`:

```yaml
name: Architecture Linting

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Check architecture boundaries
        run: python backend/scripts/check-imports.py --fix-suggestions

      - name: Validate DI usage
        run: python backend/scripts/validate-di-usage.py

      - name: Check file sizes
        run: python backend/scripts/analyze-file-sizes.py
        continue-on-error: true  # Warning only
```

### Pre-commit Hook

Agregar a `.git/hooks/pre-commit`:

```bash
#!/bin/bash
python backend/scripts/check-imports.py || exit 1
python backend/scripts/validate-di-usage.py || exit 1
```

---

## 📊 Métricas de Calidad

**Estado actual (2026-02-02):**

| Métrica | Valor | Target |
|---------|-------|--------|
| Violaciones de arquitectura | 7 | 0 |
| Uso de service locator (API) | 0 ✅ | 0 |
| Archivos >límite | 61 | <10 |
| Dependencias circulares | TBD | 0 |

**Progreso desde Plan Geológico inicio:**
- ✅ Service Locator eliminado (30 → 0 ocurrencias)
- ✅ Mappers extraídos (0 → 4)
- ⏳ File sizes (61 archivos grandes pendientes)
- ⏳ Architecture violations (7 pendientes de fix)

---

## 🛠️ Desarrollo

### Agregar nueva regla a check-imports.py

```python
ILLEGAL_PATTERNS = [
    # ... reglas existentes
    (
        "backend/nueva_capa",
        "backend/capa_prohibida",
        "Razón de la prohibición",
        "Sugerencia de corrección",
    ),
]
```

### Agregar nuevo límite a analyze-file-sizes.py

```python
LAYER_LIMITS = {
    # ... límites existentes
    "nueva_capa": 350,  # líneas
}
```

---

## 📝 Referencias

- **Plan Geológico:** `.claude/guides/backend-refactor-geological-plan.md`
- **Clean Architecture:** Martin, Robert C. (2017)
- **Dependency Injection:** Fowler, Martin. "Inversion of Control Containers"
