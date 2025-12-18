# fi_common

Núcleo compartido para dominios, casos de uso e infraestructura de Free Intelligence.

## Capas
- **domain/**: Entidades, value objects, excepciones y contratos (interfaces).
- **application/**: Casos de uso, DTOs, validadores de negocio.
- **infrastructure/**: Adaptadores concretos (persistencia HDF5/SQL, clientes externos, configuración/DI).
- **shared/**: Utilidades transversales (logging, métricas, cache, tipos, constantes, helpers).

## Migración
Este paquete sirve como destino para el refactor de clean architecture:
1. Definir interfaces en `domain/interfaces`.
2. Reubicar lógica de negocio en `application/use_cases` consumiendo interfaces.
3. Implementar adaptadores en `infrastructure/*` y exponerlos vía DI.
4. Deprecate imports directos desde `backend.storage`/`backend.services` a favor de contratos.

## Notas
- Usa Python 3.14 y `from __future__ import annotations` en todos los módulos.
- No exponer PHI/PII en logs; usar `shared.logging` y métricas estructuradas.
- Mantener apéndice-only en HDF5 y escrituras atómicas para persistencia.
