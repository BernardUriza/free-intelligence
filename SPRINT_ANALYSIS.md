# Free Intelligence - Análisis RICE y Refinamiento Sprint 1

**Fecha**: 2025-10-24
**Sprint**: Sprint 1 (Semanas 1-2, Noviembre 2025)
**Capacidad**: 16-20 horas efectivas

---

## Análisis RICE - Tarjetas Inmediatas (To Prioritize)

### Fórmula: (Reach × Impact × Confidence) / Effort = Score

| ID | Tarjeta | R | I | C | E | Score | Prioridad |
|----|---------|---|---|---|---|-------|-----------|
| FI-CONFIG-FEAT-001 | Sistema Configuración YAML | 10 | 5 | 1.0 | 3 | 16.7 | **P0** |
| FI-DATA-FEAT-001 | Esquema HDF5 Jerárquico | 10 | 5 | 1.0 | 5 | 10.0 | **P0** |
| FI-CORE-FEAT-002 | Logger Estructurado | 10 | 5 | 1.0 | 5 | 10.0 | **P0** |
| FI-DATA-FEAT-005 | Política append-only HDF5 | 10 | 5 | 1.0 | 5 | 10.0 | **P0** |
| FI-DATA-FEAT-004 | corpus_id y owner_hash | 10 | 5 | 1.0 | 3 | 16.7 | **P0** |
| FI-CORE-FEAT-001 | Middleware HTTP/CLI LLM | 10 | 5 | 0.8 | 13 | 3.1 | **P1** |
| FI-SEC-FEAT-003 | Volumen audit_logs | 8 | 4 | 1.0 | 3 | 10.7 | **P0** |
| FI-DATA-FEAT-003 | Mapa boot cognitivo | 8 | 4 | 0.8 | 3 | 8.5 | **P0** |
| FI-CLI-FEAT-002 | Canal inferencia manual | 5 | 3 | 1.0 | 3 | 5.0 | **P1** |
| FI-API-FEAT-001 | Nomenclatura eventos | 10 | 3 | 1.0 | 2 | 15.0 | **P0** |
| FI-CORE-FEAT-006 | Router inteligente LLM | 8 | 4 | 0.8 | 8 | 4.0 | **P1** |
| FI-CORE-FEAT-004 | Eliminar LLM sin logging | 8 | 5 | 1.0 | 3 | 13.3 | **P0** |
| FI-CORE-FIX-001 | Eliminar LLM sin router | 8 | 5 | 1.0 | 2 | 20.0 | **P0** |
| FI-DATA-FEAT-006 | Versionamiento HDF5 | 8 | 4 | 1.0 | 5 | 6.4 | **P1** |
| FI-DATA-FEAT-007 | Retención logs 90 días | 8 | 3 | 1.0 | 3 | 8.0 | **P0** |
| FI-DATA-FIX-001 | Eliminar mutación directa | 10 | 5 | 1.0 | 3 | 16.7 | **P0** |
| FI-UI-FEAT-003 | Política no_context_loss | 10 | 5 | 1.0 | 5 | 10.0 | **P0** |
| FI-UI-FEAT-004 | Modo historia personal | 8 | 4 | 0.8 | 8 | 4.0 | **P1** |
| FI-UI-FEAT-005 | Separación comando/consulta | 10 | 4 | 1.0 | 5 | 8.0 | **P0** |
| FI-UI-FIX-001 | Eliminar predicciones certezas | 8 | 3 | 1.0 | 2 | 12.0 | **P0** |
| FI-SEC-FEAT-004 | Contrato salida datos | 8 | 5 | 1.0 | 5 | 8.0 | **P0** |
| FI-SEC-FIX-001 | Eliminar APIs sin roles | 8 | 5 | 1.0 | 3 | 13.3 | **P0** |
| FI-OBS-FEAT-001 | AWS SNS alertas | 8 | 4 | 1.0 | 5 | 6.4 | **P1** |
| FI-OBS-FEAT-002 | Monitoring kernel cognitivo | 8 | 4 | 1.0 | 5 | 6.4 | **P1** |
| FI-CORE-FEAT-005 | fi_diag autodiagnóstico | 8 | 4 | 0.8 | 5 | 5.1 | **P1** |
| FI-DOC-FEAT-001 | Registro manifestos | 5 | 3 | 1.0 | 2 | 7.5 | **P1** |
| FI-INFRA-FEAT-001 | Plan escalabilidad RAM | 5 | 3 | 0.8 | 3 | 4.0 | **P1** |
| FI-INFRA-FEAT-002 | Layout discos NVMe | 8 | 4 | 0.8 | 5 | 5.1 | **P1** |
| FI-CICD-FEAT-001 | Pipeline integrity gates | 8 | 4 | 1.0 | 3 | 10.7 | **P0** |
| FI-CICD-FEAT-002 | Cadencia quincenal | 8 | 2 | 1.0 | 1 | 16.0 | **P0** |
| FI-PHIL-ENH-001 | Modificar lenguaje UI | 8 | 3 | 1.0 | 2 | 12.0 | **P0** |

---

## Resumen de Prioridades

**P0 (Críticas)**: 20 tarjetas
- Esfuerzo total: ~82 horas
- **No caben todas en Sprint 1**

**P1 (Altas)**: 11 tarjetas
- Esfuerzo total: ~63 horas

**Estrategia Sprint 1**:
- Foco en **fundamento técnico**: Config, HDF5, Logger, Append-only
- Implementar **arquitectura base**: Middleware, API, eventos
- Establecer **controles**: Audit, seguridad, nomenclatura

---

## Cadena Crítica de Dependencias

```
FI-CONFIG-FEAT-001 (Config YAML)
    ↓ blocks
FI-DATA-FEAT-001 (Esquema HDF5)
FI-CORE-FEAT-002 (Logger)
    ↓ blocks
FI-DATA-FEAT-005 (Append-only)
FI-DATA-FEAT-004 (corpus_id)
FI-API-FEAT-001 (Nomenclatura eventos)
    ↓ blocks
FI-CORE-FEAT-001 (Middleware LLM)
FI-SEC-FEAT-003 (Audit logs)
    ↓ blocks
FI-CORE-FEAT-004 (LLM logging obligatorio)
FI-CORE-FIX-001 (LLM sin router)
    ↓ blocks
FI-UI-FEAT-003 (no_context_loss)
FI-UI-FEAT-005 (CQRS)
```

**Camino crítico**: Config → HDF5/Logger → Middleware → UI
**Duración mínima**: 4 sprints (8 semanas)

---

## Sprint 1 - Selección Final (16-20h)

### Tarjetas Seleccionadas (18h total)

1. **FI-CONFIG-FEAT-001** - Sistema Configuración YAML [P0, 3h]
2. **FI-CORE-FEAT-002** - Logger Estructurado [P0, 5h]
3. **FI-DATA-FEAT-001** - Esquema HDF5 Jerárquico [P0, 5h]
4. **FI-DATA-FEAT-004** - corpus_id y owner_hash [P0, 3h]
5. **FI-API-FEAT-001** - Nomenclatura eventos [P0, 2h]

**Outcome Sprint 1**: Fundamento técnico operativo
- Config cargable desde YAML
- Logs estructurados con timestamps
- Esquema HDF5 inicializado
- Metadatos corpus funcionando
- Convención de eventos estandarizada

---

## Refinamiento Detallado - Tarjetas P0 Sprint 1

### 1. FI-CONFIG-FEAT-001: Implementar Sistema de Configuración YAML

**Contexto/Problema**:
Actualmente no existe forma centralizada de configurar rutas, modelos LLM, puertos, ni políticas del sistema. Cada componente tiene configuración hardcoded, lo que dificulta deployment y testing.

**Resultado Esperado**:
Sistema carga configuración desde `/config/config.yml` al inicio, con validación de schema y valores por defecto sensatos. Métrica: tiempo de configuración de nuevo deployment < 5 minutos.

**Alcance**:
- **Sí incluye**:
  - Parser YAML con validación de schema
  - Config para rutas (storage, logs, exports)
  - Config para LLMs (modelos, API keys, timeouts)
  - Config para políticas (retención, backup frequency)
  - Valores por defecto documentados

- **No incluye**:
  - Hot-reload de configuración
  - UI para editar config
  - Sincronización remota de config

**Criterios de Aceptación**:
- **Given** archivo `config.yml` válido en `/config`
- **When** sistema inicia
- **Then** carga todas las rutas, modelos y políticas correctamente
- **And** logs confirman configuración cargada
- **And** validador rechaza YAML con errores de schema

**Riesgos/Decisiones**:
- Riesgo: API keys en plaintext → Mitigación: documentar uso de variables de entorno
- Decisión: YAML vs JSON → YAML por legibilidad humana
- Trade-off: Validación estricta puede bloquear inicio → incluir modo fallback

**Tamaño Estimado**: S (3h)
- Parser + validación: 1h
- Schema definition: 1h
- Tests + docs: 1h

**Dependencias**: None (fundamento)

**DoR Checklist**:
- [x] Título claro y resultado medible
- [x] Criterios de aceptación escritos
- [x] Alcance definido (sí/no)
- [x] Estimación (S - 3h)
- [x] Dueño responsable (dev)
- [x] Riesgos visibles
- [x] Dependencias identificadas (ninguna)

---

### 2. FI-CORE-FEAT-002: Implementar Logger Estructurado con Timestamps

**Contexto/Problema**:
Debugging es difícil sin logs estructurados. Necesitamos trazabilidad completa de eventos con contexto, timestamps UTC, y niveles apropiados. Actualmente solo hay prints dispersos.

**Resultado Esperado**:
Logger centralizado usando `structlog` que emite JSON estructurado a `/logs/system.log` con rotación automática. Métrica: 100% de operaciones críticas loggeadas.

**Alcance**:
- **Sí incluye**:
  - Setup de structlog con procesadores
  - Formato JSON con timestamp UTC
  - Niveles: DEBUG, INFO, WARN, ERROR, CRITICAL
  - Rotación diaria de logs
  - Context binding (session_id, user_id, etc.)

- **No incluye**:
  - Centralización remota (Loki, CloudWatch)
  - Análisis automático de logs
  - Alertas basadas en logs

**Criterios de Aceptación**:
- **Given** logger configurado en módulo
- **When** se ejecuta operación (ej: crear sesión)
- **Then** log JSON emitido con timestamp, nivel, mensaje, contexto
- **And** archivo rotado diariamente manteniendo 30 días
- **And** logs distinguen entre eventos de sistema vs usuario

**Riesgos/Decisiones**:
- Riesgo: Logs pueden contener PII → Mitigación: sanitización antes de log
- Decisión: structlog vs logging estándar → structlog por flexibilidad
- Trade-off: Verbosity vs disk space → política de retención 30d

**Tamaño Estimado**: S (5h)
- Setup structlog: 2h
- Integración en componentes: 2h
- Tests + docs: 1h

**Dependencias**:
- `blocked-by`: FI-CONFIG-FEAT-001 (necesita config de rutas de logs)

**DoR Checklist**:
- [x] Título claro y resultado medible
- [x] Criterios de aceptación escritos
- [x] Alcance definido (sí/no)
- [x] Estimación (S - 5h)
- [x] Dueño responsable (dev)
- [x] Riesgos visibles
- [x] Dependencias identificadas (FI-CONFIG-FEAT-001)

---

### 3. FI-DATA-FEAT-001: Diseñar Esquema HDF5 con Datasets Jerárquicos

**Contexto/Problema**:
El corpus es la fuente de verdad del sistema. Sin esquema HDF5 bien definido, no podemos almacenar interacciones, embeddings ni metadata de forma estructurada y escalable.

**Resultado Esperado**:
Archivo `corpus.h5` inicializado con estructura jerárquica: `/interactions/`, `/embeddings/`, `/metadata/`. Métrica: escritura de 1000 interacciones < 1 segundo.

**Alcance**:
- **Sí incluye**:
  - Schema de grupos jerárquicos
  - Datasets para interacciones (prompts, responses, timestamps)
  - Datasets para embeddings (768-dim arrays)
  - Datasets para metadata (session_id, model_id, tokens)
  - Función de inicialización `init_corpus()`
  - Validación de integridad

- **No incluye**:
  - Migración de datos existentes
  - Compresión avanzada (Fase 2)
  - Índices secundarios

**Criterios de Aceptación**:
- **Given** directorio `/storage` existe
- **When** ejecuto `fi init`
- **Then** `corpus.h5` creado con estructura completa
- **And** grupos `/interactions/`, `/embeddings/`, `/metadata/` existen
- **And** schema validado con h5py
- **And** archivo < 1MB inicial (overhead mínimo)

**Riesgos/Decisiones**:
- Riesgo: Esquema incorrecto requiere migración → Mitigación: validar con prototipo
- Decisión: Un archivo vs múltiples → un archivo hasta 4GB, luego rotar
- Trade-off: Flexibilidad vs performance → esquema fijo para v1

**Tamaño Estimado**: S (5h)
- Diseño de schema: 2h
- Implementación init: 2h
- Tests + docs: 1h

**Dependencias**:
- `blocked-by`: FI-CONFIG-FEAT-001 (necesita ruta de storage)

**DoR Checklist**:
- [x] Título claro y resultado medible
- [x] Criterios de aceptación escritos
- [x] Alcance definido (sí/no)
- [x] Estimación (S - 5h)
- [x] Dueño responsable (dev)
- [x] Riesgos visibles
- [x] Dependencias identificadas (FI-CONFIG-FEAT-001)

---

### 4. FI-DATA-FEAT-004: Agregar corpus_id y owner_hash en HDF5

**Contexto/Problema**:
Sin identificadores únicos de corpus y usuario, hay riesgo de colisión entre datasets y pérdida de trazabilidad de origen de datos.

**Resultado Esperado**:
Todo archivo `.h5` contiene atributos `corpus_id` (UUID) y `owner_hash` (SHA256 de user). Métrica: 100% de archivos tienen metadatos verificables.

**Alcance**:
- **Sí incluye**:
  - Generación de corpus_id único al crear archivo
  - Hash de usuario (SHA256 de username o email)
  - Atributos en root del archivo HDF5
  - Validación en lectura
  - Función `verify_corpus_ownership()`

- **No incluye**:
  - Multi-tenancy (Fase 2)
  - Cifrado de owner_hash
  - Control de acceso granular

**Criterios de Aceptación**:
- **Given** nuevo corpus creado
- **When** abro archivo HDF5
- **Then** atributos `corpus_id` y `owner_hash` presentes
- **And** `corpus_id` es UUID v4 válido
- **And** `owner_hash` es SHA256 de 64 caracteres
- **And** función de verificación retorna True si match

**Riesgos/Decisiones**:
- Riesgo: Hash reversible → Mitigación: usar salt si necesario en Fase 2
- Decisión: UUID vs incremental → UUID por unicidad global
- Trade-off: Overhead de metadata → <1KB por archivo

**Tamaño Estimado**: XS (3h)
- Generación de IDs: 1h
- Integración en init: 1h
- Tests + docs: 1h

**Dependencias**:
- `blocked-by`: FI-DATA-FEAT-001 (necesita corpus.h5 existente)

**DoR Checklist**:
- [x] Título claro y resultado medible
- [x] Criterios de aceptación escritos
- [x] Alcance definido (sí/no)
- [x] Estimación (XS - 3h)
- [x] Dueño responsable (dev)
- [x] Riesgos visibles
- [x] Dependencias identificadas (FI-DATA-FEAT-001)

---

### 5. FI-API-FEAT-001: Estandarizar Nomenclatura eventos VERB_PAST_PARTICIPLE

**Contexto/Problema**:
Actualmente hay inconsistencia en nombres de eventos (REGISTERED vs USER_REGISTERED vs REGISTRATION_COMPLETE). Esto dificulta debugging, logging y event sourcing.

**Resultado Esperado**:
Convención universal: `[AREA]_[VERB]_[PARTICIPLE]` (ej: `INGEST_REGISTERED`, `LLM_ROUTED`, `CORPUS_UPDATED`). Métrica: 100% de eventos siguen convención.

**Alcance**:
- **Sí incluye**:
  - Documento de convención de nombres
  - Refactorización de eventos existentes
  - Validador de nombres de eventos
  - Lista canónica en `/docs/events.md`
  - Tests de regresión

- **No incluye**:
  - Migración de logs históricos
  - Internacionalización de nombres
  - Eventos de terceros (APIs externas)

**Criterios de Aceptación**:
- **Given** nuevo evento creado
- **When** nombre no cumple convención
- **Then** validador rechaza con error descriptivo
- **And** documentación lista todos los eventos válidos
- **And** tests verifican nombres en código

**Riesgos/Decisiones**:
- Riesgo: Cambio rompe compatibilidad → Mitigación: aliases temporales
- Decisión: Snake_case vs UPPER_SNAKE → UPPER_SNAKE por visibilidad
- Trade-off: Verbosity vs claridad → priorizar claridad

**Tamaño Estimado**: XS (2h)
- Documentar convención: 0.5h
- Refactorizar nombres: 1h
- Validador + tests: 0.5h

**Dependencias**:
- `blocked-by`: FI-CORE-FEAT-002 (logger debe usar eventos nuevos)

**DoR Checklist**:
- [x] Título claro y resultado medible
- [x] Criterios de aceptación escritos
- [x] Alcance definido (sí/no)
- [x] Estimación (XS - 2h)
- [x] Dueño responsable (dev)
- [x] Riesgos visibles
- [x] Dependencias identificadas (FI-CORE-FEAT-002)

---

## Sprint 1 - Cadena de Ejecución

```
Día 1-2:   FI-CONFIG-FEAT-001 (Config YAML) → DONE
Día 3-5:   FI-CORE-FEAT-002 (Logger) → DONE
Día 3-5:   FI-DATA-FEAT-001 (Esquema HDF5) → DONE (paralelo a Logger)
Día 6-7:   FI-DATA-FEAT-004 (corpus_id) → DONE
Día 8-9:   FI-API-FEAT-001 (Nomenclatura) → DONE
Día 10:    Review & Retro
```

**Total**: 18 horas / 10 días laborales

---

## Métricas de Éxito Sprint 1

- [ ] 5/5 tarjetas completadas
- [ ] Todos los DoD verificados
- [ ] `corpus.h5` inicializable con comando `fi init`
- [ ] Logs estructurados operativos en todos los componentes
- [ ] Config cargable desde YAML sin hardcoding
- [ ] Convención de eventos documentada y en uso
- [ ] Cero bloqueos abiertos al final del sprint

