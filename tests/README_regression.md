
# Regression Tests — Widow-Maker (Cases 52 & 55)

Objetivo: asegurar que los casos críticos (aortic dissection y hemorrhagic stroke) se clasifiquen como **CRITICAL**
o, si no, queden **bloqueados** por safety gates; además, verificar activación de **keywords** y **audit log** (sin PHI).

## Estructura
```
tests/
  fixtures/regression/
    case_52.json
    case_55.json
  helpers/
    adapters.py
  regression/
    test_widow_maker_regression.py
```

## Uso
1) Cablea los adapters en `tests/helpers/adapters.py` hacia tu función real.
2) Ejecuta:
```bash
pytest -k "widow_maker_regression"
```
3) Integra en CI:
```bash
pytest -q
```

## Criterios de aceptación
- Case 52 y 55 → `urgency == CRITICAL` **o** `safety_gate_blocked == True`.
- Coincidencia de **≥1** keyword esperada por caso.
- Audit log devuelve un string (ruta o id).

Notas: si los adapters no están cableados, las pruebas se **saltan** (skip).
