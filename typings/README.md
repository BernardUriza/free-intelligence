# Type Stubs Directory

**Propósito**: Type stubs (`.pyi` files) para suprimir falsos positivos de Pylance/Pyright en dependencias externas.

---

## ¿Qué son los Type Stubs?

Los **type stubs** son archivos `.pyi` que definen las firmas de tipo para módulos Python sin afectar el runtime. Permiten a type checkers como Pylance/mypy entender los tipos de librerías que no tienen type hints nativos.

### ¿Por qué los necesitamos?

Librerías como `h5py` usan comportamiento dinámico (metaclasses, `__getattr__`, etc.) que los type checkers no pueden inferir estáticamente. Esto genera **falsos positivos** en VS Code:

```python
dataset.shape  # ❌ Pylance: "Cannot access attribute 'shape' for class 'Dataset'"
dataset[0:10]  # ❌ Pylance: "__getitem__ method not defined on type 'Dataset'"
```

**Pero el código funciona perfectamente en runtime** (60/60 tests passing ✅).

---

## Estructura

```
typings/
├── README.md          # Este archivo
└── h5py/
    └── __init__.pyi   # Type stubs para h5py
```

---

## h5py Stubs

### Qué define

- `Group`: Métodos `__getitem__`, `keys()`, `create_dataset()`, etc.
- `Dataset`: Métodos `__getitem__`, `__setitem__`, `resize()`, propiedades `shape`, `maxshape`, etc.
- `File`: Contexto manager, `close()`, hereda de `Group`
- `AttributeManager`: Métodos `keys()`, `items()`, `get()`, etc.

### Ejemplo de uso

```python
import h5py

# Sin stubs: Pylance reporta errores
with h5py.File("corpus.h5", "r") as f:
    dataset = f["interactions"]  # ❌ reportIndexIssue
    print(dataset.shape)          # ❌ reportAttributeAccessIssue

# Con stubs: Pylance reconoce los tipos correctamente ✅
```

---

## Configuración

Los stubs se configuran en `pyrightconfig.json`:

```json
{
  "stubPath": "typings"
}
```

Pylance busca automáticamente en `typings/<module_name>/__init__.pyi`.

---

## Best Practices

### 1. Stubs Mínimos
Solo definir los métodos/propiedades que **realmente usamos** en el proyecto. No replicar toda la API de h5py.

### 2. Tipos Genéricos
Usar `Any` para tipos complejos que no vale la pena especificar:

```python
def __getitem__(self, key: Any) -> Any: ...  # ✅ Pragmático
```

### 3. Actualización
Revisar stubs cuando agregamos uso de nuevos métodos de h5py:

```bash
# Si agregamos uso de h5py.File.flush()
# Agregar a typings/h5py/__init__.pyi:
class File(Group):
    def flush(self) -> None: ...
```

---

## Alternativas Consideradas

### 1. `# type: ignore` inline
```python
dataset.shape  # type: ignore[attr-defined]
```

**Problema**: Ruido en el código, dificulta mantenimiento.

### 2. Configuración global `reportAttributeAccessIssue: "none"`
```json
{
  "reportAttributeAccessIssue": "none"
}
```

**Problema**: Silencia **todos** los errores de atributos, incluso reales.

### 3. Type Stubs (Elegido ✅)
**Ventajas**:
- Específico a `h5py` (no silencia otros errores)
- Centralizado en un solo lugar
- Mejora autocompletion de VS Code
- No afecta el runtime

---

## Referencias

- [PEP 484 - Type Hints](https://peps.python.org/pep-0484/)
- [Typing - Type Stubs](https://typing.readthedocs.io/en/latest/source/stubs.html)
- [Pylance - Stub Files](https://github.com/microsoft/pylance-release/blob/main/TROUBLESHOOTING.md#stubspath)
- [h5py Documentation](https://docs.h5py.org/en/stable/)

---

**Última actualización**: 2025-10-25
**Mantenedor**: Bernard Uriza Orozco
