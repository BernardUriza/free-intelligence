# Python 3.14 (Obligatorio)

**Versión requerida:** Python 3.14.0+ (lanzado octubre 2025)

## Por qué 3.14

AURITY requiere Python 3.14 para aprovechar:
- **JIT compiler experimental** - 3-5% más rápido (crítico para pipelines RealtimeTalk)
- **t-strings** - Interpolación eficiente para prompts LLM
- **Lazy annotations** - Mejor rendimiento con Pydantic v2
- **InterpreterPoolExecutor** - Paralelismo en workers sin GIL bottleneck
- **compression.zstd** - Compresión superior para HDF5 chunks

## Setup Local

```bash
# Verificar versión
python --version  # Debe mostrar 3.14.x

# Instalar con pyenv (recomendado)
pyenv install 3.14.0
pyenv local 3.14.0

# Verificar configuración
python -c "import sys; assert sys.version_info >= (3, 14), 'Python 3.14+ requerido'"
```

## Features Relevantes

### 1. t-strings (Template Strings)
```python
# Antes (3.13)
prompt = f"Patient: {name}\nSymptoms: {symptoms}"

# Ahora (3.14) - con evaluación diferida
prompt = t"Patient: {name}\nSymptoms: {symptoms}"
```

### 2. Lazy Annotations
```python
# Mejora rendimiento de import en módulos con muchos type hints
from __future__ import annotations

def process_session(data: SessionData) -> SOAPNote:
    # Annotations no se evalúan hasta uso
    ...
```

### 3. InterpreterPoolExecutor
```python
# Útil para workers CPU-bound (transcription, diarization)
from concurrent.futures import InterpreterPoolExecutor

with InterpreterPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(transcribe_chunk, chunk) for chunk in chunks]
    results = [f.result() for f in futures]
```

## Compatibilidad CI/CD

⚠️ **CRÍTICO**: CI/CD debe usar Python 3.14, no 3.11.

Verificar en `.github/workflows/pr-gate.yml`:
```yaml
env:
  PYTHON_VERSION: "3.14"  # ✅ Debe coincidir con pyproject.toml
```

## Recursos

- **Docs oficiales:** https://docs.python.org/3/whatsnew/3.14.html
- **Tutorial:** https://docs.python.org/3/tutorial/index.html
- **Real Python 2025:** https://realpython.com/popular-python-tutorials-2025/
- **PEP 745 (Release Schedule):** https://peps.python.org/pep-0745/
