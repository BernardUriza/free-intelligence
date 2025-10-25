# Python Type Hints Best Practices (2025)

**Fecha**: 2025-10-25
**Fuente**: Web search + Python official docs
**Aplicable a**: Python 3.11+, Pylance/Pyright, mypy

---

## 🎯 Principios Generales

### 1. Adopción Gradual
- **NO reescribir todo de golpe**: Type checkers como mypy analizan solo las partes con type hints
- Agregar hints gradualmente, priorizando APIs públicas y funciones críticas
- Los tests pueden omitir hints (runtime > static analysis en tests)

### 2. Herramientas Modernas (2025)

| Herramienta | Propósito | Nivel de Strictness |
|-------------|-----------|---------------------|
| **Pylance/Pyright** | Static analysis en VS Code | Más estricto que mypy |
| **mypy** | Static analysis CLI | Configurable (basic/strict) |
| **Pydantic** | Runtime validation | Valida datos externos (APIs, DBs) |

**Regla de oro**: Pylance > mypy en detección de ambigüedad, pero ambos detectan los mismos issues fundamentales.

---

## 🆕 Sintaxis Moderna (Python 3.10+)

### Generics Nativos (Python 3.9+)
```python
# ❌ Antiguo (typing module)
from typing import List, Dict, Tuple
def process(items: List[str]) -> Dict[str, int]: ...

# ✅ Moderno (built-in generics)
def process(items: list[str]) -> dict[str, int]: ...
```

### Union Types con `|` (Python 3.10+)
```python
# ❌ Antiguo
from typing import Union, Optional
def read_file(path: Union[str, Path]) -> Optional[str]: ...

# ✅ Moderno
from pathlib import Path
def read_file(path: str | Path) -> str | None: ...
```

### Type Aliases con `type` (Python 3.12+)
```python
# ❌ Antiguo
from typing import TypeAlias
PathLike: TypeAlias = str | Path

# ✅ Moderno (PEP 695)
type PathLike = str | Path
```

---

## 📂 Paths: Best Practices Específicas

### Opción 1: `Path | str` (Recomendado para apps modernas)
```python
from pathlib import Path

def load_config(config_path: Path | str) -> dict:
    """Acepta tanto Path como str, convierte internamente."""
    path = Path(config_path).expanduser()
    return yaml.safe_load(path.read_text())
```

**Ventajas**:
- Más flexible para usuarios
- Convierte internamente sin afectar type hints

### Opción 2: `str | os.PathLike[str]` (Más inclusivo)
```python
import os

def read_file(path: str | os.PathLike[str]) -> str:
    """Acepta cualquier objeto path-like (PEP 519)."""
    return Path(path).read_text()
```

**Ventajas**:
- Soporta cualquier implementación de `os.PathLike`
- Incluye `bytes` paths si usas `os.PathLike[str | bytes]`

### Opción 3: Solo `str` (Más estricto)
```python
def validate_corpus(corpus_path: str) -> bool:
    """API estricta: solo acepta strings."""
    if not Path(corpus_path).exists():
        raise FileNotFoundError(corpus_path)
    return True
```

**Ventajas**:
- Fuerza conversión explícita por parte del caller
- Menos ambigüedad en la API

---

## 🔧 Configuración Recomendada

### `pyrightconfig.json` (para Pylance/VS Code)
```json
{
  "typeCheckingMode": "basic",
  "pythonVersion": "3.11",
  "reportMissingImports": true,
  "reportMissingTypeStubs": false,
  "reportUnusedImport": "warning",
  "reportUnusedVariable": "warning",
  "reportAttributeAccessIssue": "none",
  "reportIndexIssue": "none"
}
```

### `mypy.ini` (para CI/CD)
```ini
[mypy]
python_version = 3.11
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = False  # Gradual adoption
ignore_missing_imports = True

# Por módulo (strict en backend crítico)
[mypy-backend.corpus_ops]
disallow_untyped_defs = True
```

---

## 🚫 Suprimir Falsos Positivos

### Estrategia 1: Type Stubs (`.pyi` files)
Crear `typings/h5py/__init__.pyi`:
```python
class Dataset:
    def __getitem__(self, key: Any) -> Any: ...
    def resize(self, size: int | tuple[int, ...]) -> None: ...
    @property
    def shape(self) -> tuple[int, ...]: ...
```

### Estrategia 2: Inline `# type: ignore`
```python
dataset.resize(new_size)  # type: ignore[attr-defined]
```

### Estrategia 3: Configuración global
```json
{
  "reportAttributeAccessIssue": "none"
}
```

**Orden de preferencia**: Stubs > Configuración global > Inline ignores

---

## 📊 Cuándo Usar Qué

| Escenario | Herramienta | Nivel |
|-----------|-------------|-------|
| **Desarrollo local** | Pylance (VS Code) | `basic` |
| **CI/CD gates** | mypy | `strict` en módulos críticos |
| **APIs externas** | Pydantic | Runtime validation |
| **Tests** | Sin type hints | Runtime > static |

---

## 🎯 Aplicación a Free Intelligence

### Config Actual
- ✅ `pyrightconfig.json` creado con configuración moderna
- ✅ Type stubs para `h5py` en `typings/h5py/__init__.pyi`
- ✅ Warnings de h5py suprimidos globalmente
- ✅ Python 3.11 configurado como target

### Acciones Futuras (Post-Sprint 2)
1. **Agregar type hints a APIs públicas** (corpus_ops, corpus_schema)
2. **Pydantic para validación de eventos** (cuando implementemos API REST)
3. **mypy en CI/CD** (GitHub Actions) con modo `strict` solo en módulos críticos

---

## 📚 Referencias

- [PEP 484 - Type Hints](https://peps.python.org/pep-0484/)
- [PEP 519 - PathLike protocol](https://peps.python.org/pep-0519/)
- [PEP 695 - Type Parameter Syntax (Python 3.12)](https://peps.python.org/pep-0695/)
- [Python Typing in 2025 - Medium Guide](https://khaled-jallouli.medium.com/python-typing-in-2025-a-comprehensive-guide-d61b4f562b99)
- [Typing Best Practices - Official Docs](https://typing.readthedocs.io/en/latest/source/best_practices.html)
- [Pylance vs mypy strictness comparison](https://stackoverflow.com/questions/79580115/)

---

**END OF BEST PRACTICES**
