# ARCHITECTURE: Redux-Claude Medical AI

**Source Repository**: https://github.com/BernardUriza/redux-claude.git
**Analysis Date**: 2025-10-28
**Analyzer**: Claude Code
**Purpose**: Technical specification for FI consultation module migration

---

## 1. REDUX STATE ARCHITECTURE

### Store Configuration

```typescript
// packages/cognitive-core/src/store/store.ts
configureStore({
  reducer: {
    medicalChat: persistedMedicalChatReducer
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['persist/PERSIST']
      }
    }).concat(medicalSyncMiddleware)
})
```

### State Shape

```typescript
interface RootState {
  medicalChat: MedicalChatState
}

interface MedicalChatState {
  // Dual-core architecture
  cores: {
    dashboard: ChatCore    // Main consultation flow
    assistant: ChatCore    // Autocompletion/suggestions
  }

  // Shared state across cores
  sharedState: {
    currentSession: SessionInfo
    patientData: PatientData
    appMode: 'chat' | 'autocompletion'
    systemHealth: 'optimal' | 'good' | 'warning' | 'critical'
  }

  // Medical extraction state
  medicalExtraction: {
    currentExtraction: MedicalExtractionOutput | null
    extractionProcess: ExtractionProcessState
    wipData: WIPData  // Work-in-progress data
  }
}

interface ChatCore {
  messages: MedicalMessage[]
  isLoading: boolean
  lastActivity: number
  sessionId: string
  completedTasks: number
}

interface ExtractionProcessState {
  isExtracting: boolean
  currentIteration: number      // 0-5
  maxIterations: 5
  lastExtractedAt: number | null
  error: string | null
}
```

---

## 2. REDUX ACTIONS CATALOG

### Medical Chat Actions

#### Message Management
```typescript
// Add new message to chat
{
  type: 'medicalChat/addMessage',
  payload: {
    coreId: 'dashboard' | 'assistant',
    content: string,
    type: 'user' | 'assistant',
    metadata?: {
      confidence?: number,
      sessionId?: string
    }
  }
}

// Update existing message
{
  type: 'medicalChat/updateMessage',
  payload: {
    coreId: string,
    messageId: string,
    content: string
  }
}

// Delete message
{
  type: 'medicalChat/deleteMessage',
  payload: {
    coreId: string,
    messageId: string
  }
}

// Clear all messages
{
  type: 'medicalChat/clearMessages',
  payload: {
    coreId: string
  }
}

// Mark message as processed
{
  type: 'medicalChat/markMessageAsProcessed',
  payload: {
    coreId: string,
    messageId: string
  }
}
```

#### Extraction Process Actions
```typescript
// Start extraction process (async thunk)
{
  type: 'medicalChat/extractMedicalData/pending',
  payload: undefined,
  meta: {
    arg: {
      messages: MedicalMessage[],
      currentExtraction: MedicalExtractionOutput | null
    }
  }
}

// Extraction succeeded
{
  type: 'medicalChat/extractMedicalData/fulfilled',
  payload: {
    extraction: MedicalExtractionOutput,
    completenessPercentage: number,
    missingFields: string[],
    nomCompliance: number
  }
}

// Extraction failed
{
  type: 'medicalChat/extractMedicalData/rejected',
  payload: {
    error: string
  }
}

// Increment iteration counter
{
  type: 'medicalChat/incrementIteration'
}

// Complete extraction process
{
  type: 'medicalChat/completeExtraction',
  payload: {
    finalExtraction: MedicalExtractionOutput
  }
}
```

#### WIP Data Management
```typescript
// Update demographics
{
  type: 'medicalChat/updateDemographics',
  payload: {
    age?: number,
    gender?: 'male' | 'female' | 'other',
    weight?: number,
    height?: number,
    occupation?: string
  }
}

// Update symptoms
{
  type: 'medicalChat/updateSymptoms',
  payload: {
    primarySymptoms?: string[],
    secondarySymptoms?: string[],
    duration?: string,
    severity?: 'mild' | 'moderate' | 'severe',
    location?: string,
    quality?: string,
    aggravatingFactors?: string[],
    relievingFactors?: string[]
  }
}

// Update medical context
{
  type: 'medicalChat/updateContext',
  payload: {
    pastMedicalHistory?: string[],
    familyHistory?: string[],
    medications?: string[],
    allergies?: string[],
    surgeries?: string[]
  }
}

// Update completeness
{
  type: 'medicalChat/updateCompleteness',
  payload: {
    percentage: number,
    missingCriticalFields: string[]
  }
}
```

#### Core Management
```typescript
// Set core loading state
{
  type: 'medicalChat/setCoreLoading',
  payload: {
    coreId: string,
    isLoading: boolean
  }
}

// Set core error
{
  type: 'medicalChat/setCoreError',
  payload: {
    coreId: string,
    error: string
  }
}

// Reset session
{
  type: 'medicalChat/resetSession',
  payload: {
    coreId?: string  // Optional: reset specific core or all
  }
}
```

### SOAP Analysis Actions

```typescript
// Start SOAP extraction
{
  type: 'soapAnalysisReal/startSOAPExtraction',
  payload: {
    extractionData: MedicalExtractionOutput
  }
}

// SOAP extraction succeeded
{
  type: 'soapAnalysisReal/extractionSuccess',
  payload: {
    analysis: SOAPAnalysis,
    quality: number  // 0-1
  }
}

// SOAP extraction failed
{
  type: 'soapAnalysisReal/extractionError',
  payload: {
    error: string
  }
}

// Update specific SOAP section
{
  type: 'soapAnalysisReal/updateSOAPSection',
  payload: {
    section: 'subjective' | 'objective' | 'assessment' | 'plan',
    content: SOAPSectionContent,
    confidence: number
  }
}

// Complete analysis
{
  type: 'soapAnalysisReal/completeAnalysis',
  payload: {
    finalAnalysis: SOAPAnalysis
  }
}
```

### Cognitive Actions

```typescript
// Update cognitive state
{
  type: 'cognitive/updateCognitiveState',
  payload: {
    confidence: number,
    activeGoals: Goal[],
    systemHealth: 'optimal' | 'good' | 'warning' | 'critical'
  }
}

// Add cognitive event
{
  type: 'cognitive/addCognitiveEvent',
  payload: {
    eventType: string,
    timestamp: number,
    data: Record<string, unknown>
  }
}

// Update system health
{
  type: 'cognitive/updateSystemHealth',
  payload: {
    health: 'optimal' | 'good' | 'warning' | 'critical',
    metrics: HealthMetrics
  }
}

// Emit processing step (for observability)
{
  type: 'cognitive/emitProcessingStep',
  payload: {
    step: string,
    agent: string,
    duration: number,
    result: any
  }
}
```

### Decision Actions

```typescript
// Start decision
{
  type: 'decisions/startDecision',
  payload: {
    id: string,
    provider: 'claude',
    query: string,
    timestamp: number
  }
}

// Complete decision
{
  type: 'decisions/completeDecision',
  payload: {
    id: string,
    decision: any,
    confidence: number,
    latency: number,
    provider: 'claude'
  }
}

// Fail decision
{
  type: 'decisions/failDecision',
  payload: {
    id: string,
    error: string,
    retryCount: number
  }
}

// Retry decision
{
  type: 'decisions/retryDecision',
  payload: {
    id: string,
    retryCount: number
  }
}

// Add audit entries
{
  type: 'decisions/addAuditEntries',
  payload: AuditEntry[]
}

interface AuditEntry {
  timestamp: number
  level: 'info' | 'warning' | 'critical'
  message: string
  context: Record<string, unknown>
}
```

---

## 3. SOAP DATA STRUCTURE (NOM-004-SSA3-2012)

### Complete SOAP Interface

```typescript
interface SOAPData {
  // S - SUBJETIVO (Subjective)
  subjetivo: {
    motivoConsulta: string              // Chief complaint
    historiaActual: string              // Present illness history

    antecedentes: {
      personales: string[]              // Personal medical history
      familiares: string[]              // Family history
      medicamentos: string[]            // Current medications
      alergias: string[]                // Allergies
      quirurgicos: string[]             // Surgical history
    }

    revisionSistemas: string            // Review of systems
    contextoPsicosocial: string         // Psychosocial context
    habitos: {
      tabaquismo?: string
      alcoholismo?: string
      drogas?: string
      ejercicio?: string
      dieta?: string
    }
  }

  // O - OBJETIVO (Objective)
  objetivo: {
    signosVitales: {
      presionArterial?: string          // Blood pressure
      frecuenciaCardiaca?: number       // Heart rate
      frecuenciaRespiratoria?: number   // Respiratory rate
      temperatura?: number              // Temperature (°C)
      saturacionOxigeno?: number        // O2 saturation (%)
      peso?: number                     // Weight (kg)
      talla?: number                    // Height (cm)
      imc?: number                      // BMI
      glucosa?: number                  // Glucose (mg/dL)
    }

    exploracionFisica: {
      aspecto: string                   // General appearance
      cabezaCuello: string              // Head & neck
      torax: string                     // Chest
      cardiovascular: string            // Cardiovascular
      pulmonar: string                  // Pulmonary
      abdomen: string                   // Abdomen
      extremidades: string              // Extremities
      neurologico: string               // Neurological
      piel: string                      // Skin
    }

    estudiosComplementarios: {
      laboratorio?: Record<string, any> // Lab results
      imagenologia?: Record<string, any> // Imaging
      otros?: Record<string, any>        // Other studies
    }
  }

  // A - ANALISIS (Assessment)
  analisis: {
    diagnosticoPrincipal: {
      condicion: string
      cie10: string                     // ICD-10 code
      evidencia: string[]               // Supporting evidence
      probabilidad: number              // 0-1
      confianza: number                 // Confidence 0-1
    }

    diagnosticosDiferenciales: Array<{
      condicion: string
      cie10: string
      probabilidad: number
      gravedad: 'baja' | 'moderada' | 'alta' | 'critica'
      urgencia: 'no_urgente' | 'semi_urgente' | 'urgente' | 'emergencia'
      defensiveScore: number            // gravity * 0.7 + probability * 0.3
      evidencia: string[]
      descartarMediante: string[]       // How to rule out
    }>

    factoresRiesgo: string[]            // Risk factors
    senosPeligro: string[]              // Red flags (widow makers)
    pronostico: {
      inmediato: string
      corto: string
      largo: string
    }

    razonamientoClinico: string         // Clinical reasoning narrative
  }

  // P - PLAN (Plan)
  plan: {
    tratamientoFarmacologico: Array<{
      medicamento: string
      dosis: string
      via: string
      frecuencia: string
      duracion: string
      indicacion: string
    }>

    tratamientoNoFarmacologico: Array<{
      intervencion: string
      frecuencia: string
      duracion: string
      objetivo: string
    }>

    estudiosAdicionales: Array<{
      estudio: string
      urgencia: 'stat' | 'urgente' | 'rutina'
      justificacion: string
      esperado: string
    }>

    interconsultas: Array<{
      especialidad: string
      urgencia: 'stat' | 'urgente' | 'rutina'
      motivo: string
    }>

    seguimiento: {
      proximaCita: string               // Next appointment
      vigilar: string[]                 // What to monitor
      criteriosEmergencia: string[]     // When to seek emergency care
      educacionPaciente: string[]       // Patient education
    }

    criteriosHospitalizacion?: string[] // Admission criteria (if applicable)
  }

  // Metadata
  metadata: {
    medico: string
    especialidad: string
    fecha: string                       // ISO 8601
    duracionConsulta: number            // Minutes
    consentimientoInformado: boolean
    versionNOM: 'NOM-004-SSA3-2012'
  }
}
```

### SOAP Completeness Calculation

```typescript
interface CompletenessMetrics {
  // Overall percentage
  percentage: number  // 0-100

  // Section completeness
  sections: {
    subjective: number    // 0-100
    objective: number
    assessment: number
    plan: number
  }

  // Critical fields
  criticalFieldsPresent: string[]
  criticalFieldsMissing: string[]

  // NOM-004 compliance
  nomCompliance: number  // 0-100
  nomViolations: string[]

  // Ready for finalization?
  readyForCommit: boolean
  blockingIssues: string[]
}
```

---

## 4. STATE TRANSITIONS

### Extraction State Machine

```
┌─────────┐
│  IDLE   │
└────┬────┘
     │ extractMedicalData/pending
     ↓
┌─────────────┐
│ EXTRACTING  │←──────┐
└────┬────┬───┘       │
     │    │           │
     │    └───────────┘ incrementIteration (if < maxIterations)
     │                │
     │ extractMedicalData/fulfilled
     ↓
┌─────────┐
│COMPLETE │
└─────────┘

Error path:
EXTRACTING → (extractMedicalData/rejected) → ERROR
ERROR → (user action) → RETRY → EXTRACTING
```

### SOAP Generation Flow

```
0% WIP Data Empty
    │
    ↓ Demographics captured
25% Subjective Section Complete
    │
    ↓ Vital signs inferred/captured
50% Objective Section Complete
    │
    ↓ Differential diagnoses generated
75% Assessment Section Complete
    │
    ↓ Treatment plan created
100% Plan Section Complete → READY FOR COMMIT
```

### Urgency Escalation

```
LOW (gravity 1-3)
    │
    ↓ Risk modifiers applied
MEDIUM (gravity 4-6)
    │
    ↓ Red flags detected
HIGH (gravity 7-8)
    │
    ↓ Widow maker pattern detected
CRITICAL (gravity 9-10) → IMMEDIATE ACTION
```

### Message Processing Pipeline

```
User Input
    │
    ↓ Sanitization
Validated Input
    │
    ↓ Medical Input Validator Agent
Category Assignment (symptom/question/emergency/general)
    │
    ├─→ Emergency → Triage Agent → URGENT PATH
    │
    ├─→ Symptom → Data Extractor Agent → WIP Update
    │
    └─→ Question → Chat Agent → Response

All paths converge:
    │
    ↓ Update Redux state
State Persisted (localStorage + session)
    │
    ↓ SOAP completeness check
If ready → Generate SOAP → Commit
```

---

## 5. MIDDLEWARE ARCHITECTURE

### Middleware Stack

```typescript
[
  // Redux Toolkit defaults
  thunk,
  immutableCheck,
  serializableCheck,

  // Custom medical middleware
  medicalSyncMiddleware,
  criticalPatternMiddleware (implicit in decisional layer),

  // Redux Persist
  persistMiddleware
]
```

### Medical Sync Middleware

**File**: `packages/cognitive-core/src/store/middleware/medicalSyncMiddleware.ts`

**Purpose**: Sync extracted medical data → patient data → SOAP state

**Triggers on**:
- `medicalChat/extractMedicalData/fulfilled`
- `medicalChat/updateDemographics`
- `medicalChat/updateSymptoms`
- `medicalChat/updateContext`

**Actions**:
```typescript
// Listens for extraction completion
if (action.type === 'medicalChat/extractMedicalData/fulfilled') {
  const { extraction } = action.payload

  // Update patient data
  dispatch(updatePatientData(extraction.demographics))

  // Trigger SOAP section updates
  dispatch(updateSOAPSection('subjective', extraction.symptoms))

  // Check completeness
  if (extraction.completeness.percentage >= 80) {
    dispatch(startSOAPExtraction(extraction))
  }
}
```

### Critical Pattern Middleware

**File**: `packages/cognitive-core/src/middleware/CriticalPatternMiddleware.ts`

**Purpose**: Detect life-threatening "widow maker" conditions

**Critical Patterns**:
```typescript
const WIDOW_MAKER_PATTERNS = [
  {
    name: 'Aortic Dissection',
    symptoms: ['chest pain', 'tearing pain', 'back pain', 'sudden onset'],
    gravity: 10,
    timeToAction: 'immediate',
    differentials: ['Acute MI', 'Pulmonary Embolism']
  },
  {
    name: 'Acute MI',
    symptoms: ['chest pain', 'dyspnea', 'diaphoresis', 'nausea'],
    gravity: 10,
    timeToAction: 'immediate'
  },
  {
    name: 'Pulmonary Embolism',
    symptoms: ['dyspnea', 'chest pain', 'hemoptysis'],
    gravity: 9,
    timeToAction: 'immediate'
  },
  {
    name: 'Meningitis',
    symptoms: ['headache', 'fever', 'neck stiffness'],
    gravity: 9,
    timeToAction: 'immediate'
  },
  {
    name: 'Sepsis',
    symptoms: ['fever', 'hypotension', 'tachycardia', 'confusion'],
    gravity: 9,
    timeToAction: 'immediate'
  }
]
```

**Override Logic**:
```typescript
const result = analyzeCriticalPatterns(input)
if (result.widowMakerAlert) {
  // Force urgency to CRITICAL
  urgencyLevel = 'CRITICAL'

  // Inject defensive prompt
  systemPrompt += generateDefensivePrompt(result.patterns)

  // Log audit event
  dispatch(addAuditEntry({
    level: 'critical',
    message: `Widow maker pattern detected: ${result.patterns[0].name}`
  }))
}
```

---

## 6. ASYNC THUNKS

### Extract Medical Data Thunk

**File**: `packages/cognitive-core/src/store/thunks/extractionThunks.ts`

```typescript
export const extractMedicalDataThunk = createAsyncThunk<
  ExtractionResult,
  ExtractThunkPayload,
  { rejectValue: string }
>(
  'medicalChat/extractMedicalData',
  async ({ messages, currentExtraction }, { rejectWithValue }) => {
    try {
      // Build context from messages
      const context = messages.map(m => ({
        role: m.role,
        content: m.content
      }))

      // Call medical data extractor agent
      const result = await callClaudeForDecision(
        'medical_data_extractor',
        context,
        { currentExtraction }
      )

      // Calculate completeness
      const completeness = calculateCompleteness(result.extraction)

      // Check NOM compliance
      const nomCompliance = checkNOMCompliance(result.extraction)

      return {
        extraction: result.extraction,
        completenessPercentage: completeness.percentage,
        missingFields: completeness.missingCriticalFields,
        nomCompliance: nomCompliance.score
      }
    } catch (error) {
      return rejectWithValue(error.message)
    }
  }
)
```

### Continue Extraction Thunk

```typescript
export const continueExtractionThunk = createAsyncThunk(
  'medicalChat/continueExtraction',
  async (_, { getState, dispatch }) => {
    const state = getState() as RootState
    const { currentExtraction, extractionProcess } = state.medicalChat.medicalExtraction

    if (extractionProcess.currentIteration >= extractionProcess.maxIterations) {
      throw new Error('Max iterations reached')
    }

    // Increment iteration
    dispatch(incrementIteration())

    // Re-extract with focus on missing fields
    const result = await dispatch(extractMedicalDataThunk({
      messages: state.medicalChat.cores.dashboard.messages,
      currentExtraction
    }))

    return result
  }
)
```

### Process Cognitively Thunk

**File**: `packages/cognitive-core/src/store/cognitiveSlice.ts`

```typescript
export const processCognitively = createAsyncThunk(
  'cognitive/process',
  async (input: string, { getState }) => {
    const state = getState() as RootState

    // Call intelligent medical chat agent
    const result = await callClaudeForDecision(
      'intelligent_medical_chat',
      input,
      {
        sessionHistory: state.medicalChat.cores.dashboard.messages,
        patientData: state.medicalChat.sharedState.patientData
      }
    )

    return {
      decision: result.decision,
      confidence: result.confidence,
      cognitiveState: result.cognitiveState,
      systemHealth: result.systemHealth
    }
  }
)
```

---

## 7. SELECTORS

### Extraction Selectors

**File**: `packages/cognitive-core/src/store/selectors/extractionSelectors.ts`

```typescript
// Get current extraction
export const selectExtractedData = (state: RootState) =>
  state.medicalChat.medicalExtraction.currentExtraction

// Get extraction process status
export const selectExtractionProcess = (state: RootState) =>
  state.medicalChat.medicalExtraction.extractionProcess

// Get WIP data
export const selectWipData = (state: RootState) =>
  state.medicalChat.medicalExtraction.wipData

// Calculate completeness percentage
export const selectCompletenessPercentage = createSelector(
  [selectExtractedData],
  (extraction) => {
    if (!extraction) return 0
    return extraction.completeness.percentage
  }
)

// Check NOM compliance
export const selectNOMCompliance = createSelector(
  [selectExtractedData],
  (extraction) => {
    if (!extraction) return 0
    return extraction.completeness.nomCompliance
  }
)

// Check if ready for SOAP generation
export const selectReadyForSOAP = createSelector(
  [selectCompletenessPercentage, selectNOMCompliance],
  (completeness, nomCompliance) => {
    return completeness >= 80 && nomCompliance >= 90
  }
)
```

### Medical Selectors

**File**: `packages/cognitive-core/src/store/selectors/medicalSelectors.ts`

```typescript
// Get all messages for a core
export const selectAllMessages = (coreId: string) =>
  (state: RootState) => state.medicalChat.cores[coreId].messages

// Get last message
export const selectLastMessage = (coreId: string) =>
  createSelector(
    [selectAllMessages(coreId)],
    (messages) => messages[messages.length - 1]
  )

// Get patient info
export const selectPatientInfo = (state: RootState) =>
  state.medicalChat.sharedState.patientData

// Get SOAP state (from separate slice)
export const selectSOAPState = (state: RootState) =>
  state.soapAnalysis?.currentAnalysis

// Get urgency assessment
export const selectUrgencyAssessment = createSelector(
  [selectExtractedData],
  (extraction) => {
    if (!extraction) return null
    // Calculate urgency based on symptoms
    return calculateUrgency(extraction.symptoms)
  }
)
```

---

## 8. PERSISTENCE STRATEGY

### Redux Persist Configuration

```typescript
import { persistReducer } from 'redux-persist'
import storage from 'redux-persist/lib/storage' // localStorage

const persistConfig = {
  key: 'medical-chat',
  version: 1,
  storage,
  whitelist: ['messages', 'diagnosticContext'], // Only persist these
  blacklist: ['isLoading', 'error'] // Don't persist these
}

const persistedMedicalChatReducer = persistReducer(
  persistConfig,
  medicalChatReducer
)
```

### Persisted Data

**Stored in**: `localStorage['persist:medical-chat']`

**Format**:
```json
{
  "messages": "[{...}]",
  "diagnosticContext": "{...}",
  "_persist": {
    "version": 1,
    "rehydrated": true
  }
}
```

### Rehydration

```typescript
// On app load
persistStore(store, null, () => {
  console.log('State rehydrated')

  // Resume session if exists
  const state = store.getState()
  if (state.medicalChat.sharedState.currentSession) {
    store.dispatch(resumeSession())
  }
})
```

---

## 9. ARCHITECTURAL PATTERNS

### 1. Dual-Core Pattern

**Purpose**: Separate concerns for main chat vs. autocompletion

**Benefit**:
- Concurrent workflows without state conflicts
- Independent loading states
- Separate error boundaries

### 2. WIP (Work-In-Progress) Pattern

**Purpose**: Accumulate partial data during extraction iterations

**Flow**:
```
Iteration 1: Extract demographics → WIP
Iteration 2: Extract symptoms → Merge to WIP
Iteration 3: Extract history → Merge to WIP
...
Iteration N: Complete → Finalize extraction
```

### 3. Defensive Medicine Pattern

**Formula**: `defensiveScore = gravity * 0.7 + probability * 0.3`

**Rationale**: Prioritize life-threatening conditions even if less probable

### 4. Event Sourcing (Target for FI)

**Redux as Event Log**:
- Each action = immutable event
- State = projection of event history
- Time-travel debugging
- Complete audit trail

**Migration to FI**:
- Redux actions → Domain events
- Redux reducer → Event store projection
- localStorage → HDF5 append-only corpus

---

## 10. CRITICAL FILE PATHS

### Redux Core
- Store: `/packages/cognitive-core/src/store/store.ts`
- Medical Chat Slice: `/packages/cognitive-core/src/store/medicalChatSlice.ts`
- SOAP Slice: `/packages/cognitive-core/src/store/slices/soapAnalysisSlice.ts`
- Cognitive Slice: `/packages/cognitive-core/src/store/cognitiveSlice.ts`
- Decisions Slice: `/packages/cognitive-core/src/store/decisionsSlice.ts`

### Thunks & Async
- Extraction Thunks: `/packages/cognitive-core/src/store/thunks/extractionThunks.ts`

### Middleware
- Medical Sync: `/packages/cognitive-core/src/store/middleware/medicalSyncMiddleware.ts`
- Critical Pattern: `/packages/cognitive-core/src/middleware/CriticalPatternMiddleware.ts`

### Selectors
- Extraction Selectors: `/packages/cognitive-core/src/store/selectors/extractionSelectors.ts`
- Medical Selectors: `/packages/cognitive-core/src/store/selectors/medicalSelectors.ts`

### Types
- Medical Types: `/packages/cognitive-core/src/types/medical.ts`
- Medical Interfaces: `/packages/cognitive-core/src/types/medicalInterfaces.ts`
- Medical Extraction: `/packages/cognitive-core/src/types/medicalExtraction.ts`

### SOAP Processing
- SOAP Processor: `/packages/cognitive-core/src/soap/SOAPProcessor.ts`
- SOAP Prompts: `/packages/cognitive-core/src/soap/SOAPPrompts.ts`

### Validators
- Defensive Medicine: `/packages/cognitive-core/src/validators/DefensiveMedicineValidator.ts`
- Diagnostic Decision Tree: `/packages/cognitive-core/src/validators/DiagnosticDecisionTree.ts`

### Classifiers
- Urgency Classifier: `/packages/cognitive-core/src/classifiers/UrgencyClassifier.ts`

### API
- Main Route: `/src/app/api/redux-brain/route.ts`

---

## 11. MIGRATION CONSIDERATIONS FOR FI

### Redux → Event Store Mapping

| Redux Concept | FI Equivalent |
|---------------|---------------|
| Action | Domain Event |
| Reducer | Event Handler / Projection |
| State | Read Model (reconstructed from events) |
| Thunk | Command Handler |
| Middleware | Event Interceptor |
| Selector | Query / View |

### Data Persistence

| Redux-Claude | Free Intelligence |
|--------------|-------------------|
| localStorage | HDF5 corpus (append-only) |
| Session Manager | Consultation event stream |
| Redux Persist | Event Store with snapshots |

### Event Schema

```python
# FI Domain Events (mapped from Redux actions)
class ConsultationEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    consultation_id: str
    timestamp: datetime
    event_type: str  # From MAPPING.json
    payload: dict
    metadata: EventMetadata

class EventMetadata(BaseModel):
    source: str = "fi_consultation_service"
    user_id: str
    session_id: str
    audit_hash: str  # SHA256
```

---

## SUMMARY

This architecture implements:
- ✅ Redux-based state management with dual-core pattern
- ✅ Async thunks for medical data extraction
- ✅ Middleware for critical pattern detection and sync
- ✅ Complete SOAP note structure (NOM-004-SSA3-2012)
- ✅ Defensive medicine with widow-maker detection
- ✅ Event-sourcing compatible design
- ✅ LocalStorage persistence with Redux Persist
- ✅ Comprehensive selectors for derived state

**Ready for migration to FI event-sourcing model.**
