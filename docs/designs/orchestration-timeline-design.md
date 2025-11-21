# Orchestration Timeline Design

Diseño de visualización mejorada del timeline para mostrar pasos de orquestación del DecisionalMiddleware.

## 📍 Ubicación

**Route:** `/timeline` (ya existe)
**Component:** `apps/aurity/app/timeline/page.tsx`
**Enhancement:** Agregar visualización de orchestration steps

---

## 🎯 Objetivo

Mostrar el "ciclo cognitivo del médico" visualmente:
- Cada paso de orchestration = un evento en el timeline
- Colores diferentes por tipo de persona (soap_editor = 🟢, clinical_advisor = 🔵)
- Feedback loops visibles (refinement arrows)

---

## 📊 Datos Disponibles

Del backend, cada SOAP generation ahora retorna:

```json
{
  "status": "COMPLETED",
  "orchestration_strategy": "COMPLEX",
  "personas_invoked": ["soap_editor", "clinical_advisor", "soap_editor"],
  "confidence_score": 0.95,
  "doctor_context_requested": false
}
```

**Nuevos datos del HDF5:**
```python
# En soap_worker.py guardamos intermediate_outputs
orchestration_result.intermediate_outputs = [
    {
        "step": 1,
        "persona": "soap_editor",
        "output": {...},  # SOAP draft v1
        "timestamp": "2025-11-20T15:30:01.234Z"
    },
    {
        "step": 2,
        "persona": "clinical_advisor",
        "output": {"feedback": "Consider adding HbA1c target..."},
        "timestamp": "2025-11-20T15:30:12.567Z"
    },
    {
        "step": 3,
        "persona": "soap_editor",
        "output": {...},  # SOAP draft v2 (refined)
        "timestamp": "2025-11-20T15:30:24.890Z"
    }
]
```

---

## 🎨 Diseño Visual

### 1. Nueva Sección: "Medical Reasoning Process"

Agregar ANTES del timeline actual (línea 298 de `timeline/page.tsx`):

```tsx
{/* Medical Reasoning Process - Orchestration Steps */}
{orchestrationSteps.length > 0 && (
  <div className="p-6 rounded-xl border-2 bg-gradient-to-br from-blue-900/20 to-purple-900/20 border-blue-700/30 shadow-lg">
    <div className="flex items-center justify-between mb-6">
      <div>
        <h2 className="text-xl font-bold text-blue-400 flex items-center gap-2">
          <Brain className="w-6 h-6" />
          Proceso de Razonamiento Clínico
        </h2>
        <p className="text-xs text-slate-500 mt-1">
          Estrategia: {strategy} · {personas.length} pasos · Confianza: {confidence}%
        </p>
      </div>
      <div className="flex gap-2">
        <Badge variant="blue">DecisionalMiddleware</Badge>
        <Badge variant="purple">Redux Médico</Badge>
      </div>
    </div>

    {/* Orchestration Flow Visualization */}
    <div className="relative">
      {/* Timeline axis */}
      <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-gradient-to-b from-blue-500 via-purple-500 to-emerald-500"></div>

      {/* Steps */}
      <div className="space-y-6 ml-16">
        {orchestrationSteps.map((step, idx) => (
          <OrchestrationStep
            key={step.id}
            step={step}
            index={idx}
            totalSteps={orchestrationSteps.length}
            isRefinement={step.persona === personas[idx - 1]}
          />
        ))}
      </div>
    </div>

    {/* Complexity Analysis Summary */}
    <div className="mt-6 p-4 bg-slate-900/50 rounded-lg border border-slate-700">
      <div className="grid grid-cols-4 gap-4 text-center">
        <div>
          <div className="text-2xl font-bold text-blue-400">{complexityScore}</div>
          <div className="text-xs text-slate-500">Complexity Score</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-purple-400">{diagnosisCount}</div>
          <div className="text-xs text-slate-500">Diagnoses</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-emerald-400">{confidence}%</div>
          <div className="text-xs text-slate-500">Confidence</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-amber-400">{duration}s</div>
          <div className="text-xs text-slate-500">Duration</div>
        </div>
      </div>
    </div>
  </div>
)}
```

### 2. Component: `OrchestrationStep`

```tsx
interface OrchestrationStepProps {
  step: {
    id: string;
    step_number: number;
    persona: string;
    timestamp: string;
    output: any;
    duration_ms?: number;
  };
  index: number;
  totalSteps: number;
  isRefinement: boolean;
}

function OrchestrationStep({ step, index, totalSteps, isRefinement }: OrchestrationStepProps) {
  const personaConfig = {
    soap_editor: {
      icon: <FileText className="w-5 h-5" />,
      color: "emerald",
      label: "SOAP Editor",
      description: "Síntesis de información clínica"
    },
    clinical_advisor: {
      icon: <Shield className="w-5 h-5" />,
      color: "blue",
      label: "Clinical Advisor",
      description: "Validación de precisión médica"
    },
    soap_generator: {
      icon: <Zap className="w-5 h-5" />,
      color: "purple",
      label: "SOAP Generator",
      description: "Generación directa"
    }
  }[step.persona];

  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="relative">
      {/* Step indicator (dot on timeline) */}
      <div className={`absolute -left-[70px] w-8 h-8 rounded-full bg-${personaConfig.color}-500 border-4 border-slate-900 flex items-center justify-center`}>
        {personaConfig.icon}
      </div>

      {/* Refinement arrow (if this is a refinement step) */}
      {isRefinement && (
        <div className="absolute -left-[60px] -top-4 text-amber-400">
          <CornerDownRight className="w-4 h-4" />
        </div>
      )}

      {/* Step card */}
      <div
        className={`p-4 rounded-xl border-2 bg-gradient-to-br from-slate-800/50 to-slate-900/50 border-${personaConfig.color}-700/30 cursor-pointer hover:border-${personaConfig.color}-600 transition-all`}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-3">
            <div className={`px-2 py-1 rounded text-xs font-bold text-${personaConfig.color}-400 bg-${personaConfig.color}-950 border border-${personaConfig.color}-800`}>
              Step {step.step_number}/{totalSteps}
            </div>
            <div>
              <div className="text-sm font-bold text-white">{personaConfig.label}</div>
              <div className="text-xs text-slate-400">{personaConfig.description}</div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Duration */}
            {step.duration_ms && (
              <div className="text-xs text-slate-500 flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {step.duration_ms}ms
              </div>
            )}

            {/* Expand indicator */}
            <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
          </div>
        </div>

        {/* Timestamp */}
        <div className="text-xs text-slate-500 mb-2">
          {new Date(step.timestamp).toLocaleTimeString('es-MX')}
        </div>

        {/* Collapsible output preview */}
        {isExpanded && (
          <div className="mt-4 pt-4 border-t border-slate-700 space-y-3">
            {/* Output preview based on persona type */}
            {step.persona === 'clinical_advisor' ? (
              // Show feedback
              <div className="p-3 bg-blue-950/30 rounded-lg border border-blue-900">
                <div className="text-xs text-blue-400 mb-2 font-semibold">Feedback Clínico:</div>
                <div className="text-sm text-slate-300 whitespace-pre-wrap">
                  {step.output.feedback || JSON.stringify(step.output, null, 2)}
                </div>
              </div>
            ) : (
              // Show SOAP draft summary
              <div className="grid grid-cols-2 gap-2">
                <div className="p-2 bg-emerald-950/20 rounded border border-emerald-900">
                  <div className="text-xs text-emerald-400">Subjetivo</div>
                  <div className="text-xs text-slate-400 line-clamp-2">
                    {step.output.subjective || '—'}
                  </div>
                </div>
                <div className="p-2 bg-blue-950/20 rounded border border-blue-900">
                  <div className="text-xs text-blue-400">Objetivo</div>
                  <div className="text-xs text-slate-400 line-clamp-2">
                    {step.output.objective || '—'}
                  </div>
                </div>
                <div className="p-2 bg-purple-950/20 rounded border border-purple-900">
                  <div className="text-xs text-purple-400">Assessment</div>
                  <div className="text-xs text-slate-400 line-clamp-2">
                    {step.output.assessment || '—'}
                  </div>
                </div>
                <div className="p-2 bg-amber-950/20 rounded border border-amber-900">
                  <div className="text-xs text-amber-400">Plan</div>
                  <div className="text-xs text-slate-400 line-clamp-2">
                    {step.output.plan || '—'}
                  </div>
                </div>
              </div>
            )}

            {/* Refinement indicator */}
            {isRefinement && (
              <div className="p-2 bg-amber-950/20 rounded border border-amber-900 text-xs text-amber-400 flex items-center gap-2">
                <CornerDownRight className="w-3 h-3" />
                Refinamiento basado en feedback del paso anterior
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
```

### 3. API Endpoint para Orchestration Steps

**Nuevo endpoint:** `GET /api/sessions/{session_id}/orchestration`

```python
# backend/api/public/workflows/sessions.py

@router.get("/sessions/{session_id}/orchestration")
async def get_orchestration_steps(session_id: str) -> dict:
    """Get orchestration steps from SOAP generation task.

    Returns:
        {
            "strategy": "COMPLEX",
            "personas_invoked": ["soap_editor", "clinical_advisor", "soap_editor"],
            "confidence_score": 0.95,
            "complexity_score": 62.0,
            "complexity_level": "COMPLEX",
            "steps": [
                {
                    "step": 1,
                    "persona": "soap_editor",
                    "timestamp": "...",
                    "output": {...},
                    "duration_ms": 8234
                },
                ...
            ]
        }
    """
    from backend.models.task_type import TaskType
    from backend.storage.task_repository import get_task_metadata

    try:
        # Get SOAP task metadata
        metadata = get_task_metadata(session_id, TaskType.SOAP_GENERATION)

        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No SOAP generation task found for {session_id}"
            )

        # Extract orchestration data
        return {
            "session_id": session_id,
            "strategy": metadata.get("orchestration_strategy", "UNKNOWN"),
            "personas_invoked": metadata.get("personas_invoked", []),
            "confidence_score": metadata.get("confidence_score", 0.0),
            "complexity_score": metadata.get("complexity_score", 0.0),
            "complexity_level": metadata.get("complexity_level", "UNKNOWN"),
            "doctor_context_requested": metadata.get("doctor_context_requested", False),
            "steps": metadata.get("intermediate_outputs", []),
        }

    except Exception as e:
        logger.error("ORCHESTRATION_GET_FAILED", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get orchestration data: {e!s}"
        ) from e
```

### 4. Frontend Integration

```tsx
// In timeline/page.tsx, add new state:
const [orchestrationData, setOrchestrationData] = useState<OrchestrationData | null>(null);

// Fetch orchestration steps when session loads:
useEffect(() => {
  async function fetchOrchestration() {
    if (!sessionData?.metadata.session_id) return;

    try {
      const response = await fetch(`/api/sessions/${sessionData.metadata.session_id}/orchestration`);
      const data = await response.json();
      setOrchestrationData(data);
    } catch (err) {
      console.error('[Timeline] Failed to load orchestration:', err);
    }
  }

  fetchOrchestration();
}, [sessionData?.metadata.session_id]);

// Then render the orchestration section:
{orchestrationData && (
  <MedicalReasoningProcess
    strategy={orchestrationData.strategy}
    personas={orchestrationData.personas_invoked}
    confidence={orchestrationData.confidence_score * 100}
    complexityScore={orchestrationData.complexity_score}
    steps={orchestrationData.steps}
  />
)}
```

---

## 🎯 Resultado Visual

### Timeline Mejorado:

```
┌─────────────────────────────────────────────┐
│ 🧠 Proceso de Razonamiento Clínico         │
│ Estrategia: COMPLEX · 3 pasos · 95%        │
├─────────────────────────────────────────────┤
│                                             │
│  ●──────────────────────────────────        │
│  │ Step 1/3  SOAP Editor                    │
│  │ Síntesis de información clínica          │
│  │ ⏱ 8234ms                                 │
│  │ [Collapsed: Click to expand]             │
│  │                                           │
│  ●──────────────────────────────────        │
│  │ Step 2/3  Clinical Advisor               │
│  │ Validación de precisión médica           │
│  │ ⏱ 4567ms                                 │
│  │ [Expanded:]                               │
│  │   Feedback Clínico:                      │
│  │   "Consider adding HbA1c target..."      │
│  │                                           │
│  ↘●─────────────────────────────────        │
│   │ Step 3/3  SOAP Editor                   │
│   │ Refinamiento basado en feedback         │
│   │ ⏱ 7890ms                                │
│   │ [Collapsed]                              │
│                                             │
├─────────────────────────────────────────────┤
│  Complexity: 62  Diagnoses: 2              │
│  Confidence: 95%  Duration: 25s            │
└─────────────────────────────────────────────┘
```

---

## 📝 Beneficios

1. **Visualización del "Redux Médico"**: Cada paso del ciclo cognitivo es visible
2. **Trazabilidad**: Auditable - cada decisión tiene timestamp y output
3. **Educativo**: El doctor ve cómo el AI razonó (no es caja negra)
4. **Debuggable**: Si el SOAP es incorrecto, sabes en qué paso falló
5. **Expandible**: Fácil agregar más tipos de personas (cardiologist, nephrologist, etc.)

---

## 🔮 Futuras Mejoras

- **Diff View**: Mostrar cambios entre draft v1 y v2
- **Confidence Evolution**: Gráfica de cómo evoluciona la confianza por paso
- **Alternative Paths**: Mostrar qué hubiera pasado con estrategia SIMPLE vs COMPLEX
- **Doctor Annotations**: Permitir al doctor agregar notas en cada paso

---

**Status:** Design Complete ✅
**Next Step:** Implement backend endpoint + frontend components
