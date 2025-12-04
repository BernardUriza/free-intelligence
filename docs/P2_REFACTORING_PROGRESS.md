# P2 Refactoring - Progreso

**Fecha:** 2025-01-XX  
**Estado:** 🟡 EN PROGRESO  
**Objetivo:** Reducir ConversationCapture de 1178 LOC a <400 LOC mediante extracción de hooks

---

## Problema Identificado

`ConversationCapture.tsx` es un **God Component** con:
- 1178 líneas de código
- 47+ variables de estado
- 16+ hooks React
- 12+ responsabilidades mezcladas
- 0% test coverage
- Imposible de mantener

---

## Estrategia de Refactoring

### Fase 1: Extracción de Hooks Especializados ✅
Crear hooks especializados siguiendo el principio Single Responsibility:

1. ✅ **useWorkflowSession** - Gestión de sesión y estado del workflow
2. ✅ **useWorkflowMetrics** - Métricas (WPM, chunk latency, backend health, logs)
3. ✅ **useAudioUpload** - Subida de chunks de audio con queue management
4. 🔄 **useWorkflowOrchestrator** - Orquestación del flujo completo (pending)
5. 🔄 **useCheckpointManager** - Gestión de checkpoints en pause/resume (pending)
6. 🔄 **useDemoMode** - Modo demo con datos simulados (pending)

### Fase 2: Refactoring del Componente Principal 🔄
- Migrar estado a hooks especializados
- Reducir props drilling usando composición
- Separar UI de lógica de negocio

### Fase 3: Splitting de Sub-componentes 🔜
- Extraer secciones grandes a componentes independientes
- Crear componentes "presentation-only"

---

## ✅ Hooks Creados - COMPLETADO (6/6)

### 1. `useWorkflowSession.ts` ✅
**Propósito:** Gestionar el estado completo de una sesión

**Responsabilidades:**
- Session ID generation
- Patient info management
- Workflow state (recording, paused, processing, finalized)
- Checkpoint state
- Diarization status
- Audio preview URLs
- Error handling

**Estado gestionado:**
- `sessionId`, `patientInfo`, `isPaused`, `isFinalized`
- `isWaitingForChunks`, `shouldFinalize`
- `checkpointState`, `diarizationJobId`, `showDiarizationModal`
- `pausedAudioUrl`, `error`
- `estimatedSecondsRemaining`

**Líneas:** ~260
**Variables de estado reducidas:** 15 (antes dispersas en ConversationCapture)

---

### 2. `useWorkflowMetrics.ts` ✅
**Propósito:** Gestionar métricas y estadísticas del workflow

**Responsabilidades:**
- Words Per Minute (WPM) calculation
- Chunk metrics tracking (latency, status, retries)
- Backend health monitoring
- Activity logs

**Estado gestionado:**
- `wpm`, `chunkMetrics`, `backendHealth`, `activityLogs`

**Helpers:**
- `calculateWPM()`, `getAverageLatency()`, `getSuccessRate()`
- `updateChunkMetric()`, `addLog()`, `clearLogs()`

**Líneas:** ~175
**Impacto:** Health monitoring automático basado en chunk failure rate

---

### 3. `useAudioUpload.ts` ✅
**Propósito:** Gestionar subida de chunks de audio al backend

**Responsabilidades:**
- Chunk numbering
- Inflight queue management
- Audio blob storage
- Upload retry logic

**Estado gestionado:**
- `chunkNumberRef`, `inflightRef`, `audioChunksRef`, `fullAudioBlobsRef`

**Helpers:**
- `uploadChunk()` - Subida con callbacks de success/error
- `getNextChunkNumber()`, `resetChunkCounter()`
- `getInflightCount()`, `clearInflight()`

**Líneas:** ~145
**Impacto:** Upload logic centralizado, tracking de inflight chunks

---

## Métricas de Progreso

| Métrica | Antes | Después (Estimado) | Mejora |
|---------|-------|---------------------|--------|
| **LOC ConversationCapture** | 1178 | ~350-400 | ✅ 66-70% |
| **Variables useState** | 47 | ~10-15 | ✅ 68-79% |
| **Hooks especializados** | 0 | 6 | ✅ Nuevo |
| **Líneas en hooks** | 0 | ~800 | ✅ Reusable |
| **Testabilidad** | 0% | 80%+ | ✅ Isolado |

---

## Próximos Pasos

### Hook #4: useWorkflowOrchestrator
**Propósito:** Coordinar el flujo completo del workflow

**Responsabilidades:**
- Inicializar sesión
- Coordinar start/pause/resume/stop
- Trigger diarization workflow
- Trigger SOAP generation
- Finalizar sesión

**Dependencias:** useWorkflowSession, useAudioUpload, useDiarizationPolling

---

### Hook #5: useCheckpointManager
**Propósito:** Gestionar checkpoints en pause/resume

**Responsabilidades:**
- Crear checkpoint (concatenar audio)
- Tracking de estado (isCreating, progress)
- Generar URL de preview
- Error handling

---

### Hook #6: useDemoMode
**Propósito:** Modo demo con datos simulados

**Responsabilidades:**
- Detectar modo demo
- Retornar datos mock
- Skip de llamadas API reales

---

## Impacto Esperado

### Mantenibilidad
- **Antes:** Cambiar lógica de checkpoint requería editar 1178 líneas
- **Después:** Editar solo `useCheckpointManager.ts` (~100 líneas)

### Testabilidad
- **Antes:** Imposible testear lógica aislada (todo junto)
- **Después:** Cada hook testeable independientemente

### Reusabilidad
- **Antes:** Lógica atada a ConversationCapture
- **Después:** Hooks reutilizables en otros componentes médicos

### Code Review
- **Antes:** 1178 líneas = 30-45 min review
- **Después:** 6 hooks × 100-200 líneas = 10-15 min cada uno

---

## Lecciones Aprendidas

1. **Single Responsibility Principle funciona**: Cada hook tiene un propósito claro
2. **Composition over Inheritance**: Componentes componen hooks en vez de heredar
3. **State Isolation**: Estado separado = menos bugs de acoplamiento
4. **Testing**: Hooks aislados = tests unitarios fáciles

---

---

### 4. `useWorkflowOrchestrator.ts` ✅
**Propósito:** Coordinar el flujo completo del workflow

**Responsabilidades:**
- Iniciar/detener/pausar/reanudar grabación
- Trigger diarization workflow
- Trigger SOAP generation
- Finalizar workflow
- State queries (canStart, canPause, etc.)

**Helpers principales:**
- `startRecording()`, `stopRecording()`, `pauseRecording()`, `resumeRecording()`
- `startDiarization()`, `startSOAPGeneration()`, `finalizeWorkflow()`
- `createCheckpoint()`
- `canStartRecording()`, `canPauseRecording()`, etc.

**Líneas:** ~250
**Impacto:** Orquestación centralizada, reduce complejidad en ConversationCapture

---

### 5. `useCheckpointManager.ts` ✅
**Propósito:** Gestionar checkpoints en pause/resume

**Responsabilidades:**
- Crear checkpoint (concatenar audio)
- Progress tracking (0-100%)
- Generar URL de preview
- Error handling específico

**Estado gestionado:**
- `isCreating`, `progress`, `lastCheckpoint`, `error`

**Helpers:**
- `createCheckpoint()` - Con simulación de progreso
- `getPreviewUrl()` - URL para audio preview
- `reset()` - Limpiar estado

**Líneas:** ~120
**Impacto:** Lógica de checkpoint aislada, fácil de testear

---

### 6. `useDemoMode.ts` ✅
**Propósito:** Modo demo con datos simulados

**Responsabilidades:**
- Gestionar estado de demo mode
- Proveer datos mock (transcripts, diarization, SOAP)
- Simulación de delays realistas
- Skip de llamadas API

**Demo consultations incluidas:**
- `pediatric_fever` - Consulta pediátrica
- `hypertension_control` - Control de hipertensión

**Helpers:**
- `enableDemoMode()`, `disableDemoMode()`
- `loadDemoConsultation()` - Carga demos predefinidos
- `getMockTranscript()`, `getMockDiarizationSegments()`, `getMockSOAPNote()`
- `simulateDelay()`, `shouldSkipAPI()`

**Líneas:** ~200
**Impacto:** Demos realistas sin backend, ideal para presentaciones

---

## ✅ FASE 1 COMPLETADA

**6/6 hooks especializados creados:**
1. ✅ useWorkflowSession (~260 LOC)
2. ✅ useWorkflowMetrics (~175 LOC)
3. ✅ useAudioUpload (~145 LOC)
4. ✅ useWorkflowOrchestrator (~250 LOC)
5. ✅ useCheckpointManager (~120 LOC)
6. ✅ useDemoMode (~200 LOC)

**Total:** ~1,150 LOC de lógica extraída y organizada

---

**Próximo paso:** Integrar hooks en ConversationCapture y reducir de 1178 LOC a <400 LOC.

