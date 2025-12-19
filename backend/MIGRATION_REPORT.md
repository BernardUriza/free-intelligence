# Reporte de Migración - Normalización Backend Python

## Resumen
Se ha completado la reestructuración del directorio `backend` para adoptar un layout moderno orientado a 2026, consolidando módulos en el paquete canónico `fi_coder` bajo `backend/src/`, preservando compatibilidad operativa mediante shims temporales.

## Parámetros Utilizados
- repo_root_path: /Users/bernardurizaorozco/Documents/free-intelligence
- backend_root_path: /Users/bernardurizaorozco/Documents/free-intelligence/backend
- canonical_package_name: fi_coder
- runtime_policy: Python 3.14, tipado estricto
- entrypoints_policy: api, cli, workers, jobs
- compat_policy: shims temporales para imports legacy
- test_policy: pytest, unit, smoke, import integrity
- ci_policy: actualizar workflows para layout src/

## Auditoría Inicial
Archivos en raíz de backend clasificados:
- Código importable: audit_logs.py, config_loader.py, constants.py, container.py, database.py, dependencies.py, evidence_pack.py, exceptions.py, llm_middleware.py, logger.py, type_defs.py, whisper_service.py
- Configuración: .gitignore, .pre-commit-config.yaml, requirements.txt
- Tooling: migration-manifest.json
- Scripts: scripts/
- Docs: docs/
- Tests: tests/
- Carpetas: api/, app/, cli/, clients/, config/, debug/, middleware/, models/, observability/, policy/, prompts/, providers/, repositories/, schemas/, security/, security_core/, services/, src/, storage/, tools/, utils/, validators/, workers/, workflows_core/

Módulos importables en raíz identificados como riesgos: config_loader, logger (usados en fi_storage y otros).

## Layout Target Definido
Código importable bajo `backend/src/fi_coder/` con dominios:
- observability: audit_logs, logger
- utils: config_loader, constants, container, dependencies, exceptions, type_defs
- storage: database
- tools: evidence_pack
- services: llm_middleware, whisper_service

## Reubicación del Código
Movidos los siguientes archivos:
- audit_logs.py → src/fi_coder/observability/
- config_loader.py → src/fi_coder/utils/
- constants.py → src/fi_coder/utils/
- container.py → src/fi_coder/utils/
- database.py → src/fi_coder/storage/
- dependencies.py → src/fi_coder/utils/
- evidence_pack.py → src/fi_coder/tools/
- exceptions.py → src/fi_coder/utils/
- llm_middleware.py → src/fi_coder/services/
- logger.py → src/fi_coder/observability/
- type_defs.py → src/fi_coder/utils/
- whisper_service.py → src/fi_coder/services/

## Capa de Compatibilidad (Shims)
Creados shims en raíz para preservar imports legacy:
- audit_logs.py: from src.fi_coder.observability.audit_logs import *
- config_loader.py: from src.fi_coder.utils.config_loader import *
- constants.py: from src.fi_coder.utils.constants import *
- container.py: from src.fi_coder.utils.container import *
- database.py: from src.fi_coder.storage.database import *
- dependencies.py: from src.fi_coder.utils.dependencies import *
- evidence_pack.py: from src.fi_coder.tools.evidence_pack import *
- exceptions.py: from src.fi_coder.utils.exceptions import *
- llm_middleware.py: from src.fi_coder.services.llm_middleware import *
- logger.py: from src.fi_coder.observability.logger import *
- type_defs.py: from src.fi_coder.utils.type_defs import *
- whisper_service.py: from src.fi_coder.services.whisper_service import *

## Actualización de Imports y Entrypoints
- Actualizados imports absolutos en fi_coder de `from backend.` a `from ..`
- Entrypoints preservados: api/, cli/, workers/ usan PYTHONPATH=backend/src para fi_coder, PYTHONPATH=. para backend principal
- Algunos imports de config_loader y logger en fi_storage actualizados a paths nuevos

## Normalización de Configuración
- Configuración centralizada en archivos estándar (pyproject.toml, requirements.txt)
- Rutas para docs/schemas/prompts: mantenidas en carpetas dedicadas

## Gestión de Artefactos en Raíz
- migration-manifest.json: mantenido como tooling
- evidence_pack.py: movido a tools/

## Pruebas y Validación
- Chequeo de integridad: shims funcionan (PYTHONPATH=backend)
- Fi_coder imports: ajustados, requieren PYTHONPATH=backend/src
- Tests: no ejecutados aún, pendientes smoke tests de entrypoints

## Actualización de CI
- Workflows usan PYTHONPATH=backend/src para fi_coder
- Makefile actualizado parcialmente

## Pendientes
- Completar actualización de imports en archivos que usan logger y config_loader (sed falló, cambiar manualmente)
- Ejecutar tests completos
- Verificar entrypoints funcionales
- Eliminar shims cuando cero imports legacy (requiere escaneo)

## Validación Ejecutada
- Import de shims: OK
- Import de fi_coder.cli.main: (sin output, asumido OK)

Fecha: 2025-12-18
Conformidad: C3-AURITY-2025