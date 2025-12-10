# P2 Fase 2 - Estrategia de Integración

**Fecha:** 2025-01-XX  
**Estado:** 🟡 EN PROGRESO  
**Objetivo:** Integrar hooks especializados en ConversationCapture

---

## Desafío

`ConversationCapture.tsx` tiene **1,178 líneas** con lógica altamente entrelazada. No es posible refactorizar todo de una vez sin romper funcionalidad.

---

## Estrategia: Integración Incremental

### Fase 2.1: Preparación (✅ COMPLETADO)
1. ✅ Importar hooks especializados
2. ✅ Inicializar hooks en lugar de useState
3. ✅ Mantener compatibilidad con código existente

**Cambios realizados:**
```typescript
// ANTES: 15+ useState dispersos
const [sessionId, setSessionId] = useState('');
const [isPaused, setIsPaused] = useState(false);
const [error, setError] = useState(null);
// ... +12 más

// DESPUÉS: 1 hook consolidado
const session = useWorkflowSession(externalSessionId, readOnly, patient, onSessionCreated);
// session.sessionId, session.isPaused, session.error, etc.
```

---

### Fase 2.2: Migración Gradual de Referencias 🔄
**Objetivo:** Reemplazar referencias a useState por hooks sin romper lógica

#### 2.2.1. SessionId Referencias
**Buscar y reemplazar:**
- `sessionId` → `session.sessionId`
- `setSessionId` → `session.setSessionId`
- `sessionIdRef.current` → `session.sessionIdRef.current`

**Impacto:** ~50 referencias en el archivo

#### 2.2.2. Pause/Resume Referencias
**Buscar y reemplazar:**
- `isPaused` → `session.isPaused`
- `setIsPaused` → `session.setIsPaused`
- `pausedAudioUrl` → `session.pausedAudioUrl`
- `setPausedAudioUrl` → `session.setPausedAudioUrl`

**Impacto:** ~20 referencias

#### 2.2.3. Patient Info Referencias
**Buscar y reemplazar:**
- `patientInfo` → `session.patientInfo`
- `setPatientInfo` → `session.setPatientInfo`
- `showPatientInfoModal` → `session.showPatientInfoModal`
- `setShowPatientInfoModal` → `session.setShowPatientInfoModal`

**Impacto:** ~15 referencias

#### 2.2.4. Diarization Referencias
**Buscar y reemplazar:**
- `diarizationJobId` → `session.diarizationJobId`
- `setDiarizationJobId` → `session.setDiarizationJobId`
- `showDiarizationModal` → `session.showDiarizationModal`
- `setShowDiarizationModal` → `session.setShowDiarizationModal`

**Impacto:** ~25 referencias

#### 2.2.5. Error & State Referencias
**Buscar y reemplazar:**
- `error` → `session.error`
- `setError` → `session.setError`
- `isFinalized` → `session.isFinalized`
- `setIsFinalized` → `session.setIsFinalized`

**Impacto:** ~10 referencias

---

### Fase 2.3: Migración de Métricas 📊
**Objetivo:** Reemplazar useChunkProcessor con useWorkflowMetrics

```typescript
// ANTES
const { chunkStatuses, avgLatency, backendHealth, activityLogs, addLog } = useChunkProcessor();

// DESPUÉS
// useChunkProcessor YA existe, integrar con useWorkflowMetrics
const metrics = useWorkflowMetrics();
// Usar metrics.addLog(), metrics.chunkMetrics, etc.
```

**Decisión:** Mantener useChunkProcessor temporalmente, migrar gradualmente su lógica a useWorkflowMetrics.

---

### Fase 2.4: Migración de Audio Upload 🎙️
**Objetivo:** Reemplazar refs y lógica de upload con useAudioUpload

```typescript
// ANTES
const chunkNumberRef = useRef(0);
const audioChunksRef = useRef([]);
const inflightRef = useRef(new Set());

// DESPUÉS
const audioUpload = useAudioUpload();
// audioUpload.chunkNumberRef, audioUpload.audioChunksRef, etc.
```

**Referencias a migrar:**
- `chunkNumberRef` → `audioUpload.chunkNumberRef`
- `audioChunksRef` → `audioUpload.audioChunksRef`
- `inflightRef` → `audioUpload.inflightRef`
- Upload logic → `audioUpload.uploadChunk()`

**Impacto:** ~30 referencias

---

### Fase 2.5: Event Handlers Simplificación 🔨
**Objetivo:** Usar useWorkflowOrchestrator para simplificar handlers

```typescript
// ANTES: handlePause tiene 50+ líneas
const handlePause = useCallback(async () => {
  // 1. Pausar recording
  // 2. Detener WebSpeech
  // 3. Crear checkpoint
  // 4. Generar preview
  // 5. Update UI state
  // ... 40+ líneas más
}, [deps...]);

// DESPUÉS: 5 líneas
const handlePause = useCallback(async () => {
  await orchestrator.pauseRecording();
  await orchestrator.createCheckpoint();
}, [orchestrator]);
```

**Handlers a simplificar:**
- `handleStart` (40 líneas → 5 líneas)
- `handlePause` (50 líneas → 5 líneas)
- `handleResume` (30 líneas → 3 líneas)
- `handleStop` (60 líneas → 10 líneas)

---

### Fase 2.6: Cleanup Final 🧹
**Objetivo:** Eliminar código duplicado y variables obsoletas

1. Eliminar useState migrados a hooks
2. Eliminar refs migrados a audioUpload
3. Simplificar props drilling
4. Reducir dependencias en useCallback/useEffect

---

## Riesgos y Mitigaciones

### Riesgo 1: Referencias Circulares
**Problema:** sessionId usado en múltiples useEffect con diferentes dependencies  
**Mitigación:** Usar session.sessionIdRef.current en lugar de session.sessionId cuando sea necesario

### Riesgo 2: Breaking Changes
**Problema:** Cambiar todas las referencias de una vez puede romper funcionalidad  
**Mitigación:** Migración incremental con testing manual en cada paso

### Riesgo 3: Props Drilling
**Problema:** Componentes hijos esperan props específicos  
**Mitigación:** Mantener props actuales, migrar componentes hijos después

---

## Progreso Actual

### ✅ Completado
- [x] Importar hooks especializados
- [x] Inicializar useWorkflowSession
- [x] Inicializar useWorkflowMetrics
- [x] Inicializar useAudioUpload
- [x] Eliminar useState duplicados (sessionId, isPaused, etc.)
- [x] Eliminar refs duplicados (audioChunksRef, chunkNumberRef, etc.)

### 🔄 En Progreso
- [ ] Migrar referencias sessionId
- [ ] Migrar referencias pause/resume
- [ ] Migrar referencias patient info

### 📋 Pendiente
- [ ] Migrar referencias diarization
- [ ] Migrar referencias error handling
- [ ] Simplificar event handlers
- [ ] Cleanup final

---

## Métricas Objetivo

| Métrica | Antes | Objetivo | Estado |
|---------|-------|----------|--------|
| **LOC Total** | 1,178 | 350-400 | 🟡 1,170 |
| **useState Count** | 47 | 10-15 | 🟡 35 |
| **Refs Count** | 10 | 2-3 | ✅ 1 |
| **Event Handler LOC** | 200+ | 50 | 📋 200+ |

---

## Siguiente Sesión

**Plan para completar Fase 2:**
1. Buscar/reemplazar sistemático de referencias
2. Testing manual después de cada grupo de cambios
3. Simplificar event handlers con orchestrator
4. Cleanup y validación final

**Tiempo estimado:** 2-3 horas de trabajo focused

---

## Lecciones Aprendidas

1. **God Components son difíciles de refactorizar:** Requieren estrategia incremental
2. **Hooks ayudan pero no son mágicos:** Migración manual sigue siendo necesaria
3. **Testing es crítico:** Cada cambio debe probarse antes de continuar
4. **Documentar estrategia ahorra tiempo:** Permite retomar trabajo fácilmente

---

**Conclusión:** Fase 2.1 completada. Fundamentos de integración establecidos. Listo para migración de referencias en próxima sesión.

