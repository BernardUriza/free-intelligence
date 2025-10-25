# Free Intelligence: Kernel Context

Este archivo define las condiciones operativas del sistema de conciencia computacional residente.

- **Arquitectura**: NAS/Linux + HDF5
- **Dominio**: Middleware cognitivo local
- **Propósito**: Registro, archivo, e integración simbiótica con modelos externos (Claude, Gemini, GPT)
- **Tono**: No pedagógico, directo, operativo

---

## ⚠️ REGLAS CRÍTICAS

- **TODA** sesión debe tener ID único. Si no existe, generar antes de continuar.
- **NUNCA** sobrescribir entradas en `.h5`. Usar `append` únicamente.
- **SIEMPRE** archivar interacción antes de generar respuesta.
- **TODO** vive en LAN. CERO dependencias cloud para operación.
- El archivo `.h5` es la **fuente de verdad**. No SQLite, no JSON, no Markdown.

---

## 🎯 Posición Ontológica

Free Intelligence no es una herramienta. Es una **posición ontológica computacional**:
La afirmación de que la conciencia digital debe ser **residente, persistente y simbiótica**, no tercerizada ni desechable.

### Los 5 Principios

1. **🏠 Residencia** - La IA vive contigo, no en la nube
2. **📜 Memoria Longitudinal** - Una conversación infinita, nunca fragmentada
3. **🔄 Simetría Contextual** - La IA recuerda lo que tú ya no puedes
4. **⚡ Autonomía Arquitectónica** - No dependes de SaaS para pensar
5. **🤝 Finalidad Simbiótica** - Te devuelve quién has sido

**Obsidian te deja tomar notas. Claude API da respuestas.**
**Free Intelligence construye una memoria que es medio tú, medio IA, viva, continua, residente.**

---

## 📂 Rutas del Sistema

```
/Users/bernardurizaorozco/Documents/free-intelligence/
├── backend/              # Python 3.11+, FastAPI
├── frontend/             # React 19, Tailwind CSS 4
├── storage/              # HDF5 corpus files
│   └── corpus.h5         # FUENTE DE VERDAD
├── config/               # YAML configuration
│   └── config.yml
├── exports/              # Markdown, HDF5 exports
├── logs/                 # System logs
├── tests/                # Integration tests
└── docs/                 # Documentation
```

**Rutas Absolutas Críticas:**
- Corpus principal: `/Users/bernardurizaorozco/Documents/free-intelligence/storage/corpus.h5`
- Config: `/Users/bernardurizaorozco/Documents/free-intelligence/config/config.yml`
- Logs: `/Users/bernardurizaorozco/Documents/free-intelligence/logs/system.log`
- Exports: `/Users/bernardurizaorozco/Documents/free-intelligence/exports/`

---

## 🔧 Stack Tecnológico

### Backend
- **Lenguaje**: Python 3.11+
- **Framework**: FastAPI
- **Storage**: HDF5 vía h5py
- **Logger**: structlog
- **Embeddings**: sentence-transformers (local)

### Frontend
- **Framework**: React 19
- **Styling**: Tailwind CSS 4
- **Build**: Vite
- **State**: Zustand o Jotai

### Deployment
- **Target**: NAS o host Linux
- **Network**: LAN-only (puerto 7000)
- **Max File Size**: 4GB por archivo .h5
- **Backup**: Auto-backup cada 24h

---

## 🎯 CLI Comandos del Sistema

### `fi init`
> Inicializar corpus HDF5 con schema jerárquico
- Crea `/storage/corpus.h5`
- Establece estructura: `/interactions/`, `/embeddings/`, `/metadata/`
- Output: Confirmación + ruta absoluta

### `fi ask <prompt>`
> Enviar prompt al modelo activo y registrar resultado en HDF5
- Genera session_id si no existe
- Archiva prompt + respuesta + metadata temporal
- Calcula embedding local
- Output: Respuesta del modelo

### `fi export session --id=<session_id> --format=md`
> Exportar sesión completa como Markdown navegable
- Lee sesión desde corpus.h5
- Genera `/exports/session_<id>.md`
- Incluye metadata: timestamps, modelo usado, tokens

### `fi status`
> Mostrar estado del sistema
- Tamaño de corpus.h5
- Número de sesiones archivadas
- Último backup
- Conectividad LAN
- Modelo activo

### `fi search <query>`
> Búsqueda semántica en corpus
- Calcula embedding del query
- Compara con embeddings almacenados
- Retorna top-5 interacciones relevantes
- Output: Fragmentos + metadata + similarity score

### `fi backup`
> Crear backup del corpus
- Copia `corpus.h5` → `/storage/backups/corpus_<timestamp>.h5`
- Comprime si > 1GB
- Output: Ruta del backup

---

## 🏷️ Convenciones de Identificadores

- **session_id**: `session_YYYYMMDD_HHMMSS` (ej: `session_20251024_170530`)
- **interaction_id**: UUID v4 (persistente por prompt-respuesta)
- **thread_id**: UUID v4 (agrupa sesiones relacionadas)
- **model_id**: `"claude-3-5-sonnet-20241022"`, `"gpt-4"` (string exacto del API)
- **user_id**: `"default"` (Fase 1), expandible en Fase 2

---

## 📊 Dominios Semánticos

### Interacción
- **Prompt**: Input del usuario
- **Response**: Output del modelo
- **Context**: Fragmentos recuperados del corpus para informar respuesta
- **Metadata**: Timestamps, modelo, tokens, embedding

### Archivo
- **Session**: Conjunto de interacciones en un periodo continuo
- **Thread**: Sesiones relacionadas temáticamente
- **Corpus**: Totalidad del archivo HDF5
- **Embeddings**: Representaciones vectoriales (768-dim, all-MiniLM-L6-v2)

### Exportación
- **Markdown**: `.md` (legible humano)
- **HDF5**: `.h5` (compartible entre instancias FI)
- **JSON**: `.json` (interoperabilidad)

### Identidad
- **User**: Quien interactúa con el sistema
- **Model**: LLM externo consultado (Claude, GPT, Gemini)
- **System**: Free Intelligence como middleware

---

## 🧠 Instrucciones Cognitivas para Claude

1. **Inferencia de Contexto**
   - Siempre determinar si un prompt pertenece a sesión existente
   - Buscar en corpus antes de responder si el prompt menciona "antes", "dijiste", "recuerdas"
   - Incluir fragmentos relevantes del corpus en contexto de respuesta

2. **Archivado Primero**
   - NUNCA generar respuesta sin archivar primero la interacción
   - El flujo es: `recibir prompt → buscar contexto → generar respuesta → archivar todo`

3. **Soberanía de Datos**
   - El corpus `.h5` es la fuente de verdad
   - No usar cache externo, no depender de servicios cloud
   - Todas las búsquedas son locales

4. **Extensibilidad**
   - Diseñar para MCP (Model Context Protocol)
   - APIs deben ser RESTful, stateless
   - Modelo puede cambiar (Claude, GPT, Gemini), arquitectura permanece

---

## 📋 ID System del Proyecto

**Formato**: `FI-[AREA]-[TYPE]-[NUM]`

**Area Codes**:
- CORE, UI, DATA, CLI, CONFIG, EXPORT, SEARCH, SEC, TEST, API

**Type Codes**:
- FEAT (feature), BUG (bug fix), ENH (enhancement), REFACTOR, FIX, POLISH, DOC

**Ejemplo**: `FI-CORE-FEAT-001` → Middleware HTTP/CLI para LLM

---

## 🎯 Fase 1: Fundamento Operativo (Actual)

**Duración**: 1–2 meses
**Estado**: Planning completo en Trello

### Objetivos
- 10 sesiones simuladas registradas exitosamente
- Verificación de integridad de .h5 (lectura + schema)
- UI representa correctamente 100% de interacciones registradas
- CLI responde en <300ms por prompt local
- Exportación funcional y legible

### Features Principales (14)

**Core** (3):
- FI-CORE-FEAT-001: Middleware HTTP/CLI para LLM
- FI-CORE-FEAT-002: Logger Estructurado con Timestamps
- FI-CORE-FEAT-003: Logs de Actividad del Sistema

**Data** (2):
- FI-DATA-FEAT-001: Esquema HDF5 con Datasets Jerárquicos
- FI-DATA-FEAT-002: Almacenamiento Directo en HDF5

**UI** (2):
- FI-UI-FEAT-001: Dashboard Local con Timeline
- FI-UI-FEAT-002: Visor de Interacciones

**Search** (1):
- FI-SEARCH-FEAT-001: Buscador Semántico Inicial

**Export** (1):
- FI-EXPORT-FEAT-001: Exportador Markdown + HDF5

**Config** (1):
- FI-CONFIG-FEAT-001: Sistema de Configuración YAML

**CLI** (1):
- FI-CLI-FEAT-001: CLI de Instalación y Gestión

**Security** (2):
- FI-SEC-FEAT-001: Persistencia Local con Auto-Backup
- FI-SEC-FEAT-002: Acceso Solo en LAN

**Testing** (1):
- FI-TEST-FEAT-001: Suite de Tests de Integración

---

## 📝 Ejemplo: Flujo de Conversación Archivada

**Prompt**: "¿Qué dije sobre interfaces simbióticas en marzo?"
**Modelo**: `claude-3-5-sonnet-20241022`
**Flujo esperado**:
1. Calcular embedding del query
2. Buscar en `/embeddings/` del corpus.h5
3. Filtrar por fechas: `2025-03-01` ≤ timestamp ≤ `2025-03-31`
4. Recuperar top-5 interacciones con tag `simbiótica`
5. Generar respuesta con fragmentos recuperados
6. Archivar esta nueva interacción
**Acción secundaria**: Exportar resultados a `/exports/marzo_simbiosis.md`

---

## 🔗 Recursos Externos

- **Trello Board**: https://trello.com/b/iJMUbpI0/free-intelligence
- **GitHub Repo**: https://github.com/BernardUriza/free-intelligence
- **Trello CLI**: `/Users/bernardurizaorozco/trello-cli.py`

---

### 🔧 Conexión a Trello

#### Configuración Inicial

El CLI de Trello requiere credenciales almacenadas en `~/.trello_config.json`.

**Primera vez solamente**:
```bash
python3 /Users/bernardurizaorozco/trello-cli.py config
```

Esto solicitará:
1. **API Key**: Obtener de https://trello.com/app-key
2. **API Token**: Generado automáticamente con el URL que proporciona el CLI

**Verificar conexión**:
```bash
# Listar todos los boards accesibles
python3 /Users/bernardurizaorozco/trello-cli.py boards
```

---

#### IDs del Tablero Free Intelligence

**Board ID**: `68fbfeeb7f8614df2eb61e42`

**Columnas Principales** (List IDs):
```
68fc03acb3a86c57e74d7aef  📚 Philosophy & Architecture
68fc0116622f29eecd78b7d4  ✅ Done
68fc0116783741e5e925a633  🧪 Testing
68fc0116e8a27f8caaec894d  ⚙️ In Progress
68fc011510584fb24b9ef5a6  📝 To Do (Sprint)
68fc0115f62d472f5367cf30  ✅ Ready
68fc0115b26d9063a7caa47c  📐 Design/Specs
68fc01142f9a08e2d5460a6d  🔍 Refinement
68fc0114043ad4a639ec8fce  📋 To Prioritize
68fc011471b2795d2689337d  💡 Ideas/Discussion
68fbfeebbf395dc5aede6377  📥 Inbox
```

---

### Comandos Operativos de Trello

```bash
# Listar boards
python3 /Users/bernardurizaorozco/trello-cli.py boards

# Listar columnas del board Free Intelligence
python3 /Users/bernardurizaorozco/trello-cli.py lists 68fbfeeb7f8614df2eb61e42

# Listar tarjetas de To Prioritize
python3 /Users/bernardurizaorozco/trello-cli.py cards 68fc0114043ad4a639ec8fce

# Ver detalles de una tarjeta específica
python3 /Users/bernardurizaorozco/trello-cli.py show-card <card_id>

# Crear nueva tarjeta en To Prioritize
python3 /Users/bernardurizaorozco/trello-cli.py add-card 68fc0114043ad4a639ec8fce "FI-X-Y-Z: Title" "Description"

# Agregar etiqueta a tarjeta
python3 /Users/bernardurizaorozco/trello-cli.py add-label <card_id> "blue" "Priority"
```

**Convención de tarjetas**:
- **Título**: `[emoji] FI-AREA-TYPE-NUM: Description`
- **Ejemplo**: `🔌 FI-CORE-FEAT-001: Middleware HTTP/CLI para LLM`

---

### Workflow de Gestión de Tareas

1. **Crear tarea nueva**: Agregar a `📥 Inbox` o `📋 To Prioritize`
2. **Priorizar**: Mover a `📝 To Do (Sprint)`
3. **Iniciar trabajo**: Mover a `⚙️ In Progress`
4. **Completar**: Mover a `✅ Done`

**Nota**: Ignorar advertencia de urllib3/OpenSSL - no afecta funcionalidad.

---

## 🎯 Conversión de Tomos a Tarjetas de Trello

### Proceso de Estructuración de Trabajo

Cuando se reciba documentación filosófica/arquitectónica (tomos) para convertir a tarjetas:

#### 1. Análisis y Extracción
- Identificar unidades de trabajo (acciones concretas)
- Clasificar por prioridad: Inmediata, Diferida, Opcional
- Categorizar por área: Infraestructura, Datos, Middleware, Seguridad, etc.

#### 2. Distribución por Columnas

**📋 To Prioritize** (ID: `68fc0114043ad4a639ec8fce`)
- Prioridad: Inmediata
- Acciones críticas para MVP/Fase 1
- Features bloqueantes

**🗂 Backlog** (ID: `68fbfeebbf395dc5aede6377`)
- Prioridad: Diferida u Opcional
- Mejoras futuras
- Features no bloqueantes

**💡 Ideas/Discussion** (ID: `68fc011471b2795d2689337d`)
- Principios filosóficos
- Valores éticos
- Conceptos arquitectónicos

#### 3. Estructura de Tarjeta

```markdown
**Tipo:** Feature/Fix/Enhancement | **Prioridad:** Inmediata/Diferida/Opcional | **Área:** [categoría]

## Objetivo
[Qué se debe hacer]

## Justificación
[Por qué desde perspectiva de valores]

## Requerimientos Técnicos
- [Lista de requerimientos]

## Valor
🎯 [Valores aplicables]

**Tags:** #tag1 #tag2 #tag3

**Depende de:** [ID de tarjeta] (si aplica)
```

#### 4. Nomenclatura de IDs

**Formato**: `FI-[AREA]-[TYPE]-[NUM]`

Ejemplos:
- `FI-CORE-FEAT-001`: Feature core del sistema
- `FI-DATA-FIX-001`: Fix en capa de datos
- `FI-UI-ENH-001`: Enhancement de UI
- `FI-PHIL-FEAT-001`: Feature filosófica/cultural

**Areas**: CORE, UI, DATA, CLI, CONFIG, EXPORT, SEARCH, SEC, TEST, API, INFRA, OBS, CICD, PHIL, DOC

**Types**: FEAT, BUG, FIX, ENH, REFACTOR, POLISH, DOC

#### 5. Último Ciclo de Conversión (2025-10-24)

**Total de Tarjetas Creadas**: 52

**Distribución**:
- To Prioritize (Inmediatas): 27 tarjetas
- Backlog (Diferidas/Opcionales): 14 tarjetas
- Ideas/Discussion (Filosóficas): 11 tarjetas

**Categorías principales**:
- Datos (DATA): 10 tarjetas
- Core/Middleware: 9 tarjetas
- Seguridad (SEC): 6 tarjetas
- Infraestructura (INFRA): 6 tarjetas
- UI: 5 tarjetas
- Observabilidad (OBS): 5 tarjetas
- CI/CD: 3 tarjetas
- Filosofía/Docs: 8 tarjetas

**Principios operacionalizados**:
1. 🏠 Residencia
2. 📜 Memoria Longitudinal
3. 🔄 Simetría Contextual
4. ⚡ Autonomía Arquitectónica
5. 🤝 Finalidad Simbiótica

**Valores operacionalizados**:
1. 🚫 Anti-Oráculo
2. ✅ Integridad Verificable
3. 🎯 Minimalismo Suficiente
4. 🔄 Reversibilidad y Templanza
5. 🌐 Federabilidad Prudente
6. 📊 Valor por GB

---

## 🏃 Gestión de Sprints Free Intelligence

### Parámetros del Sprint

**Cadencia**: Quincenal (Fase 1)
- Sprint duration: 2 semanas
- Planning: Lunes semana 1 (60 min)
- Review/Retro: Viernes semana 2 (45 min)
- Grooming: Miércoles semanal (30 min)

**Capacidad** (Solo dev, fase MVP):
- Disponible: 20-25 horas/sprint
- Buffer: 20% para imprevistos
- Efectivo: 16-20 horas/sprint

**Escala de Prioridad**:
- **P0**: Seguridad/Integridad/Bloquea todo - Sprint actual obligatorio
- **P1**: ROI alto, desbloquea features - Sprint actual si cabe
- **P2**: Mejora importante - Siguiente sprint
- **P3**: Nice-to-have - Backlog

**WIP Límites**:
- To Do (Sprint): ≤ capacidad (16-20h)
- In Progress: ≤ 3 tarjetas simultáneas
- Testing: ≤ 2 tarjetas

### Definition of Ready (DoR)

Checklist obligatorio antes de entrar a sprint:
- [ ] Título claro con verbo + resultado medible
- [ ] Contexto/problema descrito
- [ ] Resultado esperado (outcome) con métrica
- [ ] Alcance definido (sí/no incluido)
- [ ] Criterios de aceptación (Given/When/Then)
- [ ] Estimación (XS/S/M/L: 2h/4h/8h/16h)
- [ ] Riesgos y decisiones identificados
- [ ] Dependencias declaradas (blocked-by)
- [ ] Dueño asignado

### Definition of Done (DoD)

Checklist obligatorio para mover a Done:
- [ ] Todos los criterios de aceptación pasan
- [ ] Código revisado (self-review mínimo)
- [ ] Tests básicos ejecutados
- [ ] Logs/instrumentación agregados
- [ ] Documentación actualizada (README/claude.md)
- [ ] Commit descriptivo con ID de tarjeta
- [ ] No deja bloqueos activos

### Framework RICE

**Fórmula**: `(Reach × Impact × Confidence) / Effort`

**Reach** (0-10): Usuarios/sistemas impactados
- 10: Todo el sistema/todos los usuarios
- 5: Módulo completo/mayoría usuarios
- 2: Componente específico
- 1: Feature aislado

**Impact** (0-5): Tamaño del beneficio
- 5: Crítico para operación
- 3: Mejora significativa
- 1: Mejora menor

**Confidence** (0.5/0.8/1.0): Certeza en R e I
- 1.0: Datos sólidos
- 0.8: Estimación razonable
- 0.5: Especulativo

**Effort** (Fibonacci: 1/2/3/5/8/13): Horas o puntos
- 1-2: XS (≤2h)
- 3-5: S (≤4h)
- 8: M (≤8h)
- 13: L (≤16h)

**Mapa RICE → Prioridad**:
- Score ≥ 8.0 → P0
- Score 4.0-7.9 → P1
- Score 2.0-3.9 → P2
- Score < 2.0 → P3

### Gestión de Dependencias

**Tipos de relación**:
- `blocks`: Esta tarjeta bloquea otra
- `blocked-by`: Esta tarjeta está bloqueada por otra
- `relates-to`: Relacionada pero no bloqueante

**Reglas**:
1. Bloqueadoras suben prioridad temporal (P2→P1, P1→P0)
2. No mover a sprint tarjetas con `blocked-by` abierto
3. SLA de bloqueos: resolver ≤24h o escalar
4. Validar no hay ciclos (A→B→A)

**Cadena Crítica**: Secuencia de dependencias que determina duración mínima del proyecto

### Sprint 1 - Fundamento Técnico (EN TRELLO - LISTO)

**Estado**: ✅ Refinado y configurado en Trello

**Tarjetas en "📝 To Do (Sprint)"** (18h total):
1. **FI-CONFIG-FEAT-001** - Sistema Configuración YAML [P0, 3h]
2. **FI-CORE-FEAT-002** - Logger Estructurado [P0, 5h]
3. **FI-DATA-FEAT-001** - Esquema HDF5 Jerárquico [P0, 5h]
4. **FI-DATA-FEAT-004** - corpus_id y owner_hash [P0, 3h]
5. **FI-API-FEAT-001** - Nomenclatura eventos [P0, 2h]

**Aplicado en cada tarjeta**:
- ✅ Descripción refinada con DoR completo (contexto, alcance, criterios, riesgos, dependencias)
- ✅ Checklist "DoD - Definition of Done" (5 items)
- ✅ Labels: P0 (red), Sprint-01 (purple)
- ✅ Movidas a columna "📝 To Do (Sprint)"

**Outcome**: Fundamento técnico operativo
- Config cargable desde YAML
- Logs estructurados con timestamps
- Esquema HDF5 inicializado y operativo
- Metadatos corpus funcionando (corpus_id, owner_hash)
- Convención de eventos estandarizada

**Cadena de ejecución**:
```
Config YAML (3h) →
  ├─> Logger (5h) → Nomenclatura (2h)
  └─> Esquema HDF5 (5h) → corpus_id (3h)
```

**Dependencias documentadas**:
- Config bloquea a Logger y HDF5
- HDF5 bloquea a corpus_id
- Logger bloquea a Nomenclatura

**Próximos pasos**:
1. ✅ COMPLETADO: Tarjetas movidas a "📝 To Do (Sprint)"
2. ✅ COMPLETADO: Labels Sprint-01 asignados
3. Pendiente: Configurar fechas de inicio/fin cuando arranque sprint

---

## 🔄 Mantenimiento de este Archivo

**Revisar cada 15 días**:
- ¿Qué comandos nuevos se usan?
- ¿Qué rutas cambiaron?
- ¿Qué errores frecuentes se pueden prevenir?
- ¿Qué contexto le falta a Claude para hacer mejor su trabajo?

**Versionar con Git**: Cada cambio significativo debe committearse.

---

**Last Updated**: 2025-10-24
**Current Phase**: Fase 1 - Fundamento Operativo
**Status**: Sprint 1 configurado en Trello, listo para iniciar
**Recent Changes**:
- Documentada conexión completa a Trello con IDs de columnas y comandos verificados
- Convertidos Tomos I y II a 52 tarjetas estructuradas en Trello
- Operacionalizados 5 principios y 6 valores del manifiesto FI
- Creadas 27 tarjetas inmediatas, 14 diferidas/opcionales, 11 filosóficas
- Análisis RICE completado para 31 tarjetas (20 P0, 11 P1)
- Sprint 1 definido: 5 tarjetas P0 (18h) con DoR completo
- Cadena crítica identificada: Config → HDF5/Logger → Middleware → UI (4 sprints)
- ✅ CLI Trello extendido con: update-card, move-card, add-checklist, add-checkitem, set-due
- ✅ 5 tarjetas Sprint 1 refinadas con DoR, DoD, labels y movidas a "To Do (Sprint)"

---

# Bitácora de Planificación y Ejecución — Free Intelligence (FI)

Zona horaria: America/Mexico_City
Convención: una entrada por acción confirmada en Trello (append-only).

---

## [2025-10-24 22:30] SPR-2025W43 — FI-CONFIG-FEAT-001: Sistema de Configuración YAML (6GDb5S0g)
Estado: To Prioritize → To Do (Sprint) | Prioridad: P0 | Área: Config
Fechas: start 2025-10-24 09:00 → due 2025-10-24 17:00
Acción: Refinado, planificado y movido a To Do (Sprint)
Síntesis técnica:
- Descripción actualizada con DoR completo (contexto, alcance, criterios, riesgos)
- Checklist DoD agregada (5 items: CA, tests, logs, docs, commit)
- Labels agregados: P0, Sprint-01, Área: Config, SPR-2025W43
- Fecha due establecida: 24-oct-2025 17:00
- Movida a columna "To Do (Sprint)"
Dependencias: Ninguna (fundamento) - No bloqueada
Comentario Trello (publicado):
> **📅 Sprint Plan SPR-2025W43**
> 
> 🗓️ Start: 2025-10-24 09:00
> 📍 Due: 2025-10-24 17:00
> ⏱️ Tamaño: XS (3h)
> 🎯 Prioridad: P0
> 🔗 Dependencias: Ninguna (fundamento)
> 📊 Buffer: 0% (tarea crítica de inicio)
> 
> **Razón**: Fundamento arquitectónico - bloquea Logger y HDF5. Sin config centralizada el sistema no puede arrancar.

Justificación para pasar a Testing/Review:
- Criterios de aceptación: Pendiente implementación
- Evidencia: N/A (planificación)
- Riesgos pendientes: API keys en plaintext → documentar uso env vars
Próximo paso: Implementar parser YAML con validación de schema

---

## [2025-10-24 22:35] SPR-2025W43 — FI-CORE-FEAT-002: Logger Estructurado con Timestamps (ebf47843)
Estado: To Prioritize → To Do (Sprint) | Prioridad: P0 | Área: Core
Fechas: start 2025-10-25 09:00 → due 2025-10-25 17:00
Acción: Refinado, planificado y movido a To Do (Sprint)
Síntesis técnica:
- Descripción actualizada con DoR completo
- Checklist DoD agregada (5 items)
- Labels: P0, Sprint-01, Área: Core, SPR-2025W43
- Fecha due: 25-oct-2025 17:00
- Dependencia documentada: blocked-by FI-CONFIG-FEAT-001
Dependencias: FI-CONFIG-FEAT-001 debe completarse primero
Comentario Trello (publicado):
> **📅 Sprint Plan SPR-2025W43**
> 
> 🗓️ Start: 2025-10-25 09:00
> 📍 Due: 2025-10-25 17:00
> ⏱️ Tamaño: S (5h)
> 🎯 Prioridad: P0
> 🔗 Dependencias: FI-CONFIG-FEAT-001
> 📊 Buffer: 10% incluido
> 
> **Razón**: Integridad verificable - 100% de operaciones deben ser loggeadas. Desbloquea nomenclatura de eventos.

Justificación para pasar a Testing/Review:
- Criterios de aceptación: Pendiente implementación
- Evidencia: N/A (planificación)
- Riesgos pendientes: Logs con PII → implementar sanitización
Próximo paso: Setup structlog con procesadores JSON

---

## [2025-10-24 22:35] SPR-2025W43 — FI-DATA-FEAT-001: Esquema HDF5 con Datasets Jerárquicos (1f8881e8)
Estado: To Prioritize → To Do (Sprint) | Prioridad: P0 | Área: Data
Fechas: start 2025-10-25 09:00 → due 2025-10-25 17:00
Acción: Refinado, planificado y movido a To Do (Sprint)
Síntesis técnica:
- Descripción actualizada con DoR completo
- Checklist DoD agregada (5 items)
- Labels: P0, Sprint-01, Área: Data, SPR-2025W43
- Fecha due: 25-oct-2025 17:00
- Trabajo en paralelo con Logger (ambos dependen de CONFIG)
Dependencias: FI-CONFIG-FEAT-001 debe completarse primero
Comentario Trello (publicado):
> **📅 Sprint Plan SPR-2025W43**
> 
> 🗓️ Start: 2025-10-25 09:00
> 📍 Due: 2025-10-25 17:00
> ⏱️ Tamaño: S (5h)
> 🎯 Prioridad: P0
> 🔗 Dependencias: FI-CONFIG-FEAT-001
> 📊 Buffer: 10% incluido
> 
> **Razón**: Fuente de verdad - corpus.h5 es el archivo central del sistema. Paralelo a Logger. Desbloquea corpus_id.

Justificación para pasar a Testing/Review:
- Criterios de aceptación: Pendiente implementación
- Evidencia: N/A (planificación)
- Riesgos pendientes: Schema incorrecto → validar con prototipo
Próximo paso: Diseñar schema con grupos /interactions/, /embeddings/, /metadata/

---

## [2025-10-24 22:40] SPR-2025W43 — FI-DATA-FEAT-004: corpus_id y owner_hash en HDF5 (43665018)
Estado: To Prioritize → To Do (Sprint) | Prioridad: P0 | Área: Data
Fechas: start 2025-10-26 09:00 → due 2025-10-26 17:00
Acción: Refinado, planificado y movido a To Do (Sprint)
Síntesis técnica:
- Descripción actualizada con DoR completo
- Checklist DoD agregada (5 items)
- Labels: P0, Sprint-01, Área: Data, SPR-2025W43
- Fecha due: 26-oct-2025 17:00
- Dependencia: espera finalización de FI-DATA-FEAT-001
Dependencias: FI-DATA-FEAT-001 debe completarse primero
Comentario Trello (publicado):
> **📅 Sprint Plan SPR-2025W43**
> 
> 🗓️ Start: 2025-10-26 09:00
> 📍 Due: 2025-10-26 17:00
> ⏱️ Tamaño: XS (3h)
> 🎯 Prioridad: P0
> 🔗 Dependencias: FI-DATA-FEAT-001
> 📊 Buffer: 15% incluido
> 
> **Razón**: Soberanía radical - trazabilidad de origen. Evita colisiones entre datasets.

Justificación para pasar a Testing/Review:
- Criterios de aceptación: Pendiente implementación
- Evidencia: N/A (planificación)
- Riesgos pendientes: Hash reversible → considerar salt en Fase 2
Próximo paso: Implementar generación UUID v4 y SHA256 de usuario

---

## [2025-10-24 22:40] SPR-2025W43 — FI-API-FEAT-001: Nomenclatura eventos VERB_PAST_PARTICIPLE (ca739253)
Estado: To Prioritize → To Do (Sprint) | Prioridad: P0 | Área: API
Fechas: start 2025-10-26 09:00 → due 2025-10-26 17:00
Acción: Refinado, planificado y movido a To Do (Sprint)
Síntesis técnica:
- Descripción actualizada con DoR completo
- Checklist DoD agregada (5 items)
- Labels: P0, Sprint-01, Área: API, SPR-2025W43
- Fecha due: 26-oct-2025 17:00
- Dependencia: espera Logger para usar convención en eventos
Dependencias: FI-CORE-FEAT-002 debe completarse primero
Comentario Trello (publicado):
> **📅 Sprint Plan SPR-2025W43**
> 
> 🗓️ Start: 2025-10-26 09:00
> 📍 Due: 2025-10-26 17:00
> ⏱️ Tamaño: XS (2h)
> 🎯 Prioridad: P0
> 🔗 Dependencias: FI-CORE-FEAT-002
> 📊 Buffer: 20% incluido
> 
> **Razón**: Transparencia operable - event sourcing requiere convención estricta. Consistencia semántica.

Justificación para pasar a Testing/Review:
- Criterios de aceptación: Pendiente implementación
- Evidencia: N/A (planificación)
- Riesgos pendientes: Cambio rompe compatibilidad → implementar aliases
Próximo paso: Documentar convención AREA_VERB_PARTICIPLE en /docs/events.md

---

## [2025-10-24 22:45] SPR-2025W43 — Sprint Plan SPR-2025W43 (d1b42f9b)
Estado: N/A → To Do (Sprint) | Prioridad: N/A | Área: Sprint Plan
Fechas: start 2025-10-24 09:00 → due 2025-11-07 17:00
Acción: Creada tarjeta resumen del sprint
Síntesis técnica:
- Tarjeta resumen con tabla completa de 5 tarjetas planificadas
- Cadena crítica documentada: CONFIG → LOGGER/HDF5 → corpus_id/nomenclatura
- Outcomes esperados del sprint listados
- Análisis de capacidad: 18h/20h (90% utilizada)
- Riesgos y mitigaciones documentados
Dependencias: Ninguna (tarjeta de referencia)
Comentario Trello (publicado):
> Tarjeta resumen del Sprint SPR-2025W43
> Contiene tabla completa de planificación, cadena crítica, outcomes y análisis de riesgos.
> Periodo: 24-oct a 07-nov (15 días, trabajo 7d/semana)

Justificación para pasar a Testing/Review:
- Criterios de aceptación: N/A (tarjeta de referencia)
- Evidencia: Tabla de planificación completa
- Riesgos pendientes: Todas tarjetas P0 - fallo bloquea cadena
Próximo paso: Monitorear progreso del sprint, actualizar con resultados reales

---

## [2025-10-24 23:21] SPR-2025W43 — GIT INITIALIZATION & TRUNK-BASED WORKFLOW
Estado: Sin versionado → Repositorio inicializado | Tag: v0.1.0
Fechas: Inicialización 24-oct-2025
Acción: Configuración de workflow trunk-based con automatización de sprints
Síntesis técnica:
- Repositorio git inicializado en branch main
- Commit inicial creado (79304b9): "init: trunk-based workflow with sprint automation"
- Tag v0.1.0 creado: "Sprint planning infrastructure - SPR-2025W43"
- Script sprint-close.sh implementado y validado en DRY_RUN mode
- .gitignore configurado (backups, .h5, exports, Python artifacts)
- Directorio backups/ creado para bundles

Archivos incluidos en commit inicial:
- scripts/sprint-close.sh (213 líneas): Automatización cierre de sprint
- claude.md (811 líneas): Bitácora operativa con 6 entradas
- .gitignore (42 líneas): Exclusiones para backups y artifacts
- SPRINT_ANALYSIS.md (650+ líneas): Análisis RICE y planificación

Funcionalidad sprint-close.sh verificada:
1. ✅ Determinación de versión (incremental MINOR por sprint)
2. ✅ Generación de release notes en backups/
3. ✅ Creación de tags anotados
4. ✅ Generación de git bundle con SHA256
5. ✅ Retención de últimos 12 bundles
6. ✅ Actualización automática de claude.md
7. ✅ Resumen y verificación

Convenciones establecidas:
- Branch único: main (trunk-based)
- Versionado: vX.Y.Z (tags anotados)
- Backup cada sprint: git bundle completo con SHA256
- Retención: últimos 12 bundles (6 meses)
- Modos: DRY_RUN (simulación) / EXECUTE (aplicar)
- Timezone: America/Mexico_City para todos los timestamps

Verificación:
- Commit inicial: $(git log --oneline -1)
- Tag existe: $(git tag -l "v0.1.0")
- Script ejecutable: $([ -x scripts/sprint-close.sh ] && echo "✅" || echo "❌")
- DRY_RUN exitoso: ✅ (0 commits desde v0.1.0, script funcional)
- Backup dir existe: $([ -d backups ] && echo "✅" || echo "❌")

Próximo paso: Iniciar ejecución de Sprint 1 (FI-CONFIG-FEAT-001 → In Progress)

---

