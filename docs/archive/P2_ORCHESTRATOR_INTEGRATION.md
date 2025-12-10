# P2 Orchestrator Integration - ConversationCapture Simplification

**Fecha**: 2025-12-04
**Objetivo**: Simplificar handlers complejos en `ConversationCapture.tsx` usando la instancia existente de `useWorkflowOrchestrator`

---

## 🎯 Resumen Ejecutivo

Se ha completado la integración del hook `useWorkflowOrchestrator` en el componente `ConversationCapture`, simplificando significativamente los handlers y eliminando lógica duplicada. El orchestrator ahora centraliza el control del flujo de trabajo médico.

---

## 🔧 Cambios Realizados

### 1. **useWorkflowOrchestrator.ts - Mejoras al Hook**

#### Cambios:
- ✅ Agregado callback `onSessionCreated` al interface `WorkflowOrchestratorOptions`
- ✅ Integrado notificación de `onSessionCreated` en el método `startRecording`
- ✅ Agregada validación y logging de sesión finalizada en `startRecording`
- ✅ Eliminado `metrics.clearLogs()` para preservar historial de logs

#### Código Actualizado:

```typescript
export interface WorkflowOrchestratorOptions {
  session: WorkflowSessionState;
  audioUpload: AudioUploadState;
  metrics: WorkflowMetricsState;
  onRecordingStart?: () => void;
  onRecordingStop?: () => void;
  onPause?: () => void;
  onResume?: () => void;
  onDiarizationStart?: (jobId: string) => void;
  onSOAPStart?: (jobId: string) => void;
  onWorkflowComplete?: () => void;
  onSessionCreated?: (sessionId: string) => void; // NUEVO
}
```

**startRecording mejorado:**
```typescript
const startRecording = useCallback(
  async (patientInfo?: any) => {
    if (session.isFinalized) {
      session.setError('La sesión ya ha sido finalizada. No se puede grabar.');
      metrics.addLog('⚠️ Sesión completada - recarga la página para nueva consulta');
      return;
    }

    // Initialize session
    const sessionId = session.initializeSession(patientInfo);
    metrics.addLog(`🎙️ Grabación iniciada - Sesión: ${sessionId}`);

    // Reset counters
    audioUpload.resetChunkCounter();
    audioUpload.clearInflight();

    // Notify parent component (for DialogueFlow to load later)
    if (onSessionCreated) {
      onSessionCreated(sessionId);
    }

    if (onRecordingStart) {
      onRecordingStart();
    }
  },
  [session, audioUpload, metrics, onRecordingStart, onSessionCreated]
);
```

---

### 2. **ConversationCapture.tsx - Simplificación de Handlers**

#### Cambios:
1. ✅ **handleStartRecording**: Simplificado usando `orchestrator.startRecording()`
2. ✅ **Diarization Callback**: Migrado a usar `orchestrator.startSOAPGeneration()` y `orchestrator.finalizeWorkflow()`
3. ✅ **performFinalization**: Migrado a usar `orchestrator.startDiarization()`
4. ✅ **Instancia del Orchestrator**: Agregado `onSessionCreated` callback
5. ✅ **Correcciones**: Eliminadas referencias duplicadas `session.session.xxx`

#### handleStartRecording - Antes (70 líneas):

```typescript
const handleStartRecording = useCallback(async () => {
  if (session.isFinalized) {
    console.warn('[Recording] ❌ Cannot start new recording - session is finalized. Reload page for new session.');
    metrics.addLog('⚠️ Sesión completada - recarga la página para nueva consulta');
    return;
  }

  if (!session.patientInfo) {
    console.log('[Recording] Patient info required - showing modal');
    session.setShowPatientInfoModal(true);
    return;
  }

  try {
    session.setError(null);
    session.setIsPaused(false);
    audioUpload.audioChunksRef.current = [];
    audioUpload.fullAudioBlobsRef.current = [];
    audioUpload.chunkNumberRef.current = 0;
    audioUpload.inflightRef.current.clear();

    // Reset diarization state from previous session
    session.setShowDiarizationModal(false);
    session.setDiarizationJobId(null);

    // Reset transcription (Phase 6 - uses hook)
    resetTranscription();
    setWebSpeechTranscripts([]);
    setLoadedChunkMetrics([]);

    // Reset monitoring metrics
    resetMetrics();
    setWpm(0);
    startTimeRef.current = Date.now();
    metrics.addLog('🎙️ Grabación iniciada');

    // Generate NEW session ID (clean slate)
    const newSessionId = getSessionId();
    session.sessionIdRef.current = newSessionId;
    session.setSessionId(newSessionId);

    // Notify parent component (for DialogueFlow to load later)
    onSessionCreated?.(newSessionId);

    // Start recording with hook (handles dual recorders, timer, stream)
    await hookStartRecording();

    // Start WebSpeech for instant preview (if supported)
    if (isWebSpeechSupported) {
      startWebSpeech();
      console.log('[WebSpeech] Started instant preview');
    }

    if (setExternalIsRecording) {
      setExternalIsRecording(true);
    }
  } catch (err) {
    console.error('Error starting recording:', err);
    session.setError('No se pudo acceder al micrófono. Por favor, verifica los permisos.');
  }
}, [/* 12 dependencies */]);
```

#### handleStartRecording - Después (38 líneas):

```typescript
const handleStartRecording = useCallback(async () => {
  if (!session.patientInfo) {
    console.log('[Recording] Patient info required - showing modal');
    session.setShowPatientInfoModal(true);
    return;
  }

  try {
    // P2F3: Use orchestrator for state management
    await orchestrator.startRecording(session.patientInfo);

    // Reset transcription (Phase 6 - uses hook)
    resetTranscription();
    setWebSpeechTranscripts([]);
    setLoadedChunkMetrics([]);

    // Reset monitoring metrics
    resetMetrics();
    setWpm(0);
    startTimeRef.current = Date.now();

    // Start recording with hook (handles dual recorders, timer, stream)
    await hookStartRecording();

    // Start WebSpeech for instant preview (if supported)
    if (isWebSpeechSupported) {
      startWebSpeech();
      console.log('[WebSpeech] Started instant preview');
    }
  } catch (err) {
    console.error('Error starting recording:', err);
    session.setError('No se pudo acceder al micrófono. Por favor, verifica los permisos.');
  }
}, [session.patientInfo, orchestrator, resetTranscription, resetMetrics, hookStartRecording, isWebSpeechSupported, startWebSpeech]);
```

**Reducción**: 46% menos código (70 → 38 líneas)
**Beneficios**:
- ✅ Validación de sesión finalizada movida al orchestrator
- ✅ Inicialización de sesión centralizada
- ✅ Notificación de `onSessionCreated` manejada por orchestrator
- ✅ Reset de estado manejado por orchestrator
- ✅ Menos dependencias en el callback

---

#### Diarization Callback - Antes:

```typescript
onComplete: async () => {
  console.log('[Diarization] ✅ Completed with triple vision');
  metrics.addLog('✅ Diarización completada');
  session.setIsFinalized(true);

  setTimeout(async () => {
    session.session.setShowDiarizationModal(false); // ❌ Referencia duplicada
    session.session.setDiarizationJobId(null);      // ❌ Referencia duplicada

    const currentSessionId = session.session.sessionIdRef.current;
    if (currentSessionId) {
      try {
        console.log('[SOAP] 🚀 Starting SOAP generation...', currentSessionId);
        metrics.metrics.addLog('📋 Generando notas SOAP...'); // ❌ Referencia duplicada

        const soapResponse = await medicalWorkflowApi.startSOAPGeneration(currentSessionId);
        console.log('[SOAP] ✅ SOAP generation started:', soapResponse);
        metrics.metrics.addLog('✅ Generación SOAP iniciada'); // ❌ Referencia duplicada
      } catch (session.error) { // ❌ Nombre de variable incorrecto
        console.error('[SOAP] ❌ Failed to start SOAP generation:', session.error);
        metrics.metrics.addLog('⚠️ Error al generar SOAP (continuando...)');
      }
    }

    metrics.metrics.addLog('✅ Sesión completada - avanzando a revisión del diálogo');
    onNext?.();
  }, 2000);
},
```

#### Diarization Callback - Después:

```typescript
onComplete: async () => {
  console.log('[Diarization] ✅ Completed with triple vision');
  metrics.addLog('✅ Diarización completada');
  session.setIsFinalized(true);

  setTimeout(async () => {
    session.setShowDiarizationModal(false);
    session.setDiarizationJobId(null);

    console.log('[Workflow] 🎯 Phase 3 complete. Auto-advancing to Phase 4 (SOAP).');

    // Phase 4: Use orchestrator to start SOAP generation
    const currentSessionId = session.sessionIdRef.current;
    if (currentSessionId) {
      try {
        console.log('[SOAP] 🚀 Starting SOAP generation...', currentSessionId);
        metrics.addLog('📋 Generando notas SOAP...');

        await orchestrator.startSOAPGeneration();
        console.log('[SOAP] ✅ SOAP generation started');
        metrics.addLog('✅ Generación SOAP iniciada');
      } catch (error) {
        console.error('[SOAP] ❌ Failed to start SOAP generation:', error);
        metrics.addLog('⚠️ Error al generar SOAP (continuando...)');
      }
    }

    metrics.addLog('✅ Sesión completada - avanzando a revisión del diálogo');
    orchestrator.finalizeWorkflow();
  }, 2000);
},
```

**Mejoras**:
- ✅ Eliminadas referencias duplicadas `session.session.xxx` → `session.xxx`
- ✅ Eliminadas referencias duplicadas `metrics.metrics.xxx` → `metrics.xxx`
- ✅ Corregido nombre de variable `session.error` → `error`
- ✅ Uso de `orchestrator.startSOAPGeneration()` en lugar de llamada directa
- ✅ Uso de `orchestrator.finalizeWorkflow()` en lugar de `onNext?.()`

---

#### performFinalization - Diarization Start:

**Antes:**
```typescript
const diarizationResult = await medicalWorkflowApi.startDiarization(session.sessionIdRef.current);

if (diarizationResult.job_id) {
  console.log('[DIARIZATION] 🎙️ Starting diarization job:', diarizationResult.job_id);
  session.setDiarizationJobId(diarizationResult.job_id);
  session.setIsWaitingForChunks(false);
  session.setShowDiarizationModal(true);
  metrics.addLog(`🎙️ Iniciando diarización (Job: ${diarizationResult.job_id.slice(0, 8)}...)`);
}
```

**Después:**
```typescript
// P2F3: Use orchestrator for diarization
const diarizationJobId = await orchestrator.startDiarization();

if (diarizationJobId) {
  console.log('[DIARIZATION] 🎙️ Starting diarization job:', diarizationJobId);
  session.setIsWaitingForChunks(false);
  session.setShowDiarizationModal(true);
  metrics.addLog(`🎙️ Iniciando diarización (Job: ${diarizationJobId.slice(0, 8)}...)`);
}
```

**Mejoras**:
- ✅ Llamada directa a API reemplazada por `orchestrator.startDiarization()`
- ✅ `session.setDiarizationJobId()` ahora manejado por el orchestrator
- ✅ Menos lógica en el componente

---

### 3. **Correcciones de Sintaxis**

#### Interface Props:
```typescript
// ❌ ANTES
interface ConversationCaptureProps {
  session.sessionId?: string;
}

// ✅ DESPUÉS
interface ConversationCaptureProps {
  sessionId?: string;
}
```

#### SessionBadges Prop:
```typescript
// ❌ ANTES
<SessionBadges session.sessionId={session.sessionIdRef.current} />

// ✅ DESPUÉS
<SessionBadges sessionId={session.sessionIdRef.current} />
```

---

## 📊 Métricas de Impacto

### Reducción de Código:
- **handleStartRecording**: 70 → 38 líneas (-46%)
- **Diarization callbacks**: Eliminadas 5 referencias duplicadas
- **API calls directas**: 3 → 1 (eliminadas `startDiarization` y `startSOAPGeneration`)

### Mejoras de Mantenibilidad:
- ✅ Lógica de workflow centralizada en orchestrator
- ✅ Menos dependencias en callbacks (12 → 7 en `handleStartRecording`)
- ✅ Separación de responsabilidades: componente UI vs. lógica de negocio
- ✅ Facilita testing: orchestrator puede ser mockeado fácilmente

### Calidad de Código:
- ✅ **0 errores de lint** después de los cambios
- ✅ Eliminadas referencias duplicadas y sintaxis incorrecta
- ✅ Código más legible y predecible

---

## 🎯 Handlers Simplificados

### Handlers que ahora usan orchestrator:

| Handler | Métodos del Orchestrator Usados |
|---------|----------------------------------|
| `handleStartRecording` | `orchestrator.startRecording()` |
| `handlePauseRecording` | `orchestrator.pauseRecording()` |
| `handleResumeRecording` | `orchestrator.resumeRecording()` |
| `performFinalization` | `orchestrator.startDiarization()` |
| `useDiarizationPolling.onComplete` | `orchestrator.startSOAPGeneration()`, `orchestrator.finalizeWorkflow()` |

### Callbacks configurados en orchestrator:

```typescript
const orchestrator = useWorkflowOrchestrator({
  session,
  audioUpload,
  metrics,
  onRecordingStart: () => {
    if (setExternalIsRecording) setExternalIsRecording(true);
  },
  onRecordingStop: () => {
    if (setExternalIsRecording) setExternalIsRecording(false);
  },
  onSessionCreated: (sessionId) => {
    onSessionCreated?.(sessionId);
  },
  onDiarizationStart: (jobId) => {
    console.log('[Orchestrator] Diarization started:', jobId);
  },
  onSOAPStart: (jobId) => {
    console.log('[Orchestrator] SOAP generation started:', jobId);
  },
  onWorkflowComplete: () => {
    console.log('[Orchestrator] Workflow complete');
    onNext?.();
  },
});
```

---

## ✅ Estado Final

### Archivos Modificados:
1. `/apps/aurity/hooks/useWorkflowOrchestrator.ts` - Hook mejorado
2. `/apps/aurity/components/medical/ConversationCapture.tsx` - Handlers simplificados

### Verificación:
- ✅ **0 errores de lint**
- ✅ **0 errores de TypeScript**
- ✅ **Sintaxis corregida** en interfaces y props
- ✅ **Referencias duplicadas eliminadas**
- ✅ **Lógica centralizada** en orchestrator

---

## 🚀 Próximos Pasos Sugeridos

### P2F4 - Integración Completa (Opcional):
1. Migrar `handleChunk` para usar orchestrator (si aplica)
2. Extraer lógica de `performFinalization` a un método del orchestrator
3. Crear estado de máquina explícito para workflow phases

### P3 - Testing y Validación:
1. Tests unitarios para `useWorkflowOrchestrator`
2. Tests de integración para flujo completo
3. Validación de cobertura de código

---

## 📝 Notas Técnicas

### Patrón Aplicado: **Facade Pattern + Orchestrator**

El `useWorkflowOrchestrator` actúa como una fachada que:
- Encapsula la complejidad de coordinación entre múltiples hooks
- Proporciona una interfaz simple para el componente
- Centraliza el manejo de estado del workflow
- Facilita el testing mediante dependency injection

### Principios SOLID Aplicados:

1. **Single Responsibility**: Cada hook tiene una responsabilidad única
2. **Open/Closed**: Orchestrator puede extenderse sin modificar componente
3. **Dependency Inversion**: Componente depende de abstracciones (orchestrator) no de implementaciones

---

**Autor**: Claude AI (P2 Architectural Refactoring)
**Estado**: ✅ Completado
**Fecha**: 2025-12-04
