# Patient Manager Feedback UI Design

Diseño de interfaz de auditoría médica para `medical-ai` - permite al doctor revisar, aprobar y corregir sesiones procesadas por el sistema.

## 📍 Ubicación

**Route:** `/medical-ai/patients` (ya existe)
**Enhancement:** Agregar sección de auditoría de sesiones
**New Component:** `SessionAuditPanel.tsx`

---

## 🎯 Objetivo

Permitir al doctor:
1. **Revisar** el procesamiento automático (SOAP, diarización, emociones)
2. **Aprobar/Rechazar** sesiones con feedback estructurado
3. **Corregir** errores de transcripción, identificación de speakers, o notas SOAP
4. **Auditar** el razonamiento del sistema (ver orchestration steps)

---

## 📊 Datos Disponibles

### API Endpoint (nuevo):
`GET /api/sessions/{session_id}/audit`

```json
{
  "session_id": "session_20251120_143000",
  "patient": {
    "id": "PAT-001",
    "name": "María González",
    "age": 45,
    "comorbidities": ["Diabetes Tipo 2", "Hipertensión"]
  },
  "session_metadata": {
    "date": "2025-11-20T14:30:00Z",
    "duration_seconds": 420,
    "doctor": "Dr. Uriza",
    "status": "pending_review"  // pending_review | approved | rejected
  },
  "orchestration": {
    "strategy": "COMPLEX",
    "personas_invoked": ["soap_editor", "clinical_advisor", "soap_editor"],
    "confidence_score": 0.92,
    "complexity_score": 68.5,
    "steps": [...]  // Full orchestration steps
  },
  "soap_note": {
    "subjective": "...",
    "objective": "...",
    "assessment": "...",
    "plan": {...}
  },
  "diarization": {
    "segments": [...]  // Speaker segments
  },
  "flags": [
    {
      "type": "low_confidence",
      "severity": "warning",
      "message": "Confidence score below 95% (92%)",
      "location": "assessment.diagnoses[0]"
    },
    {
      "type": "medication_interaction",
      "severity": "critical",
      "message": "Posible interacción: Enalapril + Losartán (ambos IECA)",
      "location": "plan.medications"
    }
  ],
  "doctor_feedback": null  // Null if not yet reviewed
}
```

---

## 🎨 Diseño Visual

### 1. Patient List View (medical-ai/patients)

**Agregar columna de auditoría:**

```tsx
// En la tabla de pacientes, agregar badge de status
<Table>
  <TableRow>
    <TableCell>María González</TableCell>
    <TableCell>45 años</TableCell>
    <TableCell>2025-11-20 14:30</TableCell>
    <TableCell>
      {/* NUEVO: Status Badge */}
      <Badge variant={getAuditStatusColor(session.audit_status)}>
        {session.audit_status === 'pending_review' && '⏳ Pendiente Revisión'}
        {session.audit_status === 'approved' && '✅ Aprobado'}
        {session.audit_status === 'rejected' && '❌ Rechazado'}
        {session.audit_status === 'flagged' && '⚠️ Con Alertas'}
      </Badge>
    </TableCell>
    <TableCell>
      <Button onClick={() => openAuditPanel(session.id)}>
        Auditar
      </Button>
    </TableCell>
  </TableRow>
</Table>
```

### 2. Session Audit Panel (Slide-over)

**Componente:** `SessionAuditPanel.tsx`

```tsx
interface SessionAuditPanelProps {
  sessionId: string;
  isOpen: boolean;
  onClose: () => void;
  onApprove: (feedback: DoctorFeedback) => void;
  onReject: (feedback: DoctorFeedback) => void;
}

function SessionAuditPanel({ sessionId, isOpen, onClose, onApprove, onReject }: SessionAuditPanelProps) {
  const [auditData, setAuditData] = useState<AuditData | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'soap' | 'orchestration' | 'transcript'>('overview');
  const [feedback, setFeedback] = useState<DoctorFeedback>({
    rating: null,
    corrections: [],
    comments: '',
  });

  return (
    <SlideOver isOpen={isOpen} onClose={onClose} width="wide">
      {/* Header */}
      <div className="border-b border-slate-700 pb-4 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-white">
              Auditoría de Sesión
            </h2>
            <p className="text-sm text-slate-400 mt-1">
              {auditData?.patient.name} · {formatDate(auditData?.session_metadata.date)}
            </p>
          </div>

          {/* Quick Actions */}
          <div className="flex gap-2">
            <Button variant="success" onClick={() => onApprove(feedback)}>
              ✅ Aprobar
            </Button>
            <Button variant="danger" onClick={() => onReject(feedback)}>
              ❌ Rechazar
            </Button>
          </div>
        </div>

        {/* Flags Banner (if any) */}
        {auditData?.flags && auditData.flags.length > 0 && (
          <div className="mt-4 space-y-2">
            {auditData.flags.map((flag, idx) => (
              <Alert
                key={idx}
                variant={flag.severity === 'critical' ? 'error' : 'warning'}
              >
                <AlertTriangle className="w-4 h-4" />
                <span className="font-semibold">{flag.type}:</span> {flag.message}
                <span className="text-xs text-slate-400 ml-2">({flag.location})</span>
              </Alert>
            ))}
          </div>
        )}
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">
            <FileText className="w-4 h-4 mr-2" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="soap">
            <Stethoscope className="w-4 h-4 mr-2" />
            SOAP Note
          </TabsTrigger>
          <TabsTrigger value="orchestration">
            <Brain className="w-4 h-4 mr-2" />
            Razonamiento IA
          </TabsTrigger>
          <TabsTrigger value="transcript">
            <MessageSquare className="w-4 h-4 mr-2" />
            Transcripción
          </TabsTrigger>
        </TabsList>

        {/* Tab Content */}
        <TabsContent value="overview">
          <OverviewTab data={auditData} />
        </TabsContent>

        <TabsContent value="soap">
          <SOAPTab
            soapNote={auditData?.soap_note}
            onCorrection={(correction) => setFeedback({
              ...feedback,
              corrections: [...feedback.corrections, correction]
            })}
          />
        </TabsContent>

        <TabsContent value="orchestration">
          <OrchestrationTab
            orchestration={auditData?.orchestration}
            steps={auditData?.orchestration.steps}
          />
        </TabsContent>

        <TabsContent value="transcript">
          <TranscriptTab segments={auditData?.diarization.segments} />
        </TabsContent>
      </Tabs>

      {/* Footer: Feedback Form */}
      <div className="mt-8 pt-6 border-t border-slate-700">
        <h3 className="text-lg font-semibold text-white mb-4">
          Feedback del Doctor
        </h3>

        {/* Rating */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Calidad General del Procesamiento
          </label>
          <div className="flex gap-2">
            {[1, 2, 3, 4, 5].map((rating) => (
              <button
                key={rating}
                onClick={() => setFeedback({ ...feedback, rating })}
                className={`p-2 rounded ${
                  feedback.rating === rating
                    ? 'bg-yellow-500 text-white'
                    : 'bg-slate-700 text-slate-400 hover:bg-slate-600'
                }`}
              >
                {'★'.repeat(rating)}
              </button>
            ))}
          </div>
        </div>

        {/* Comments */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Comentarios Adicionales
          </label>
          <textarea
            className="w-full p-3 bg-slate-800 border border-slate-700 rounded-lg text-white"
            rows={4}
            placeholder="Ej: El diagnóstico es correcto pero faltó mencionar el seguimiento a 3 meses..."
            value={feedback.comments}
            onChange={(e) => setFeedback({ ...feedback, comments: e.target.value })}
          />
        </div>

        {/* Corrections Summary */}
        {feedback.corrections.length > 0 && (
          <div className="mb-4 p-3 bg-blue-950/20 border border-blue-900 rounded-lg">
            <div className="text-sm font-semibold text-blue-400 mb-2">
              Correcciones Aplicadas ({feedback.corrections.length})
            </div>
            <ul className="text-xs text-slate-300 space-y-1">
              {feedback.corrections.map((corr, idx) => (
                <li key={idx}>
                  • {corr.section}: "{corr.original}" → "{corr.corrected}"
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </SlideOver>
  );
}
```

### 3. SOAP Tab with Inline Corrections

```tsx
function SOAPTab({ soapNote, onCorrection }: SOAPTabProps) {
  const [editingSection, setEditingSection] = useState<string | null>(null);
  const [editedText, setEditedText] = useState('');

  const handleCorrection = (section: string, original: string) => {
    onCorrection({
      section,
      original,
      corrected: editedText,
      timestamp: new Date().toISOString(),
    });
    setEditingSection(null);
  };

  return (
    <div className="space-y-6">
      {/* Subjective */}
      <SOAPSection
        title="Subjetivo (S)"
        content={soapNote.subjective}
        color="emerald"
        isEditing={editingSection === 'subjective'}
        onEdit={() => {
          setEditingSection('subjective');
          setEditedText(soapNote.subjective);
        }}
        onSave={() => handleCorrection('subjective', soapNote.subjective)}
        onCancel={() => setEditingSection(null)}
        editedText={editedText}
        setEditedText={setEditedText}
      />

      {/* Objective */}
      <SOAPSection
        title="Objetivo (O)"
        content={soapNote.objective}
        color="blue"
        isEditing={editingSection === 'objective'}
        onEdit={() => {
          setEditingSection('objective');
          setEditedText(soapNote.objective);
        }}
        onSave={() => handleCorrection('objective', soapNote.objective)}
        onCancel={() => setEditingSection(null)}
        editedText={editedText}
        setEditedText={setEditedText}
      />

      {/* Assessment */}
      <SOAPSection
        title="Assessment (A)"
        content={soapNote.assessment}
        color="purple"
        isEditing={editingSection === 'assessment'}
        onEdit={() => {
          setEditingSection('assessment');
          setEditedText(JSON.stringify(soapNote.assessment, null, 2));
        }}
        onSave={() => handleCorrection('assessment', JSON.stringify(soapNote.assessment))}
        onCancel={() => setEditingSection(null)}
        editedText={editedText}
        setEditedText={setEditedText}
      />

      {/* Plan */}
      <SOAPSection
        title="Plan (P)"
        content={soapNote.plan}
        color="amber"
        isEditing={editingSection === 'plan'}
        onEdit={() => {
          setEditingSection('plan');
          setEditedText(JSON.stringify(soapNote.plan, null, 2));
        }}
        onSave={() => handleCorrection('plan', JSON.stringify(soapNote.plan))}
        onCancel={() => setEditingSection(null)}
        editedText={editedText}
        setEditedText={setEditedText}
      />
    </div>
  );
}
```

### 4. SOAPSection Component (Editable)

```tsx
interface SOAPSectionProps {
  title: string;
  content: string | object;
  color: 'emerald' | 'blue' | 'purple' | 'amber';
  isEditing: boolean;
  onEdit: () => void;
  onSave: () => void;
  onCancel: () => void;
  editedText: string;
  setEditedText: (text: string) => void;
}

function SOAPSection({
  title,
  content,
  color,
  isEditing,
  onEdit,
  onSave,
  onCancel,
  editedText,
  setEditedText
}: SOAPSectionProps) {
  const colorClasses = {
    emerald: 'border-emerald-700 bg-emerald-950/20 text-emerald-400',
    blue: 'border-blue-700 bg-blue-950/20 text-blue-400',
    purple: 'border-purple-700 bg-purple-950/20 text-purple-400',
    amber: 'border-amber-700 bg-amber-950/20 text-amber-400',
  };

  return (
    <div className={`p-4 rounded-xl border-2 ${colorClasses[color]}`}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-bold">{title}</h3>
        {!isEditing ? (
          <button
            onClick={onEdit}
            className="px-3 py-1 text-xs bg-slate-700 hover:bg-slate-600 rounded text-white"
          >
            <Edit className="w-3 h-3 inline mr-1" />
            Corregir
          </button>
        ) : (
          <div className="flex gap-2">
            <button
              onClick={onSave}
              className="px-3 py-1 text-xs bg-green-600 hover:bg-green-500 rounded text-white"
            >
              ✓ Guardar
            </button>
            <button
              onClick={onCancel}
              className="px-3 py-1 text-xs bg-red-600 hover:bg-red-500 rounded text-white"
            >
              ✗ Cancelar
            </button>
          </div>
        )}
      </div>

      {isEditing ? (
        <textarea
          className="w-full p-3 bg-slate-800 border border-slate-700 rounded text-white font-mono text-sm"
          rows={8}
          value={editedText}
          onChange={(e) => setEditedText(e.target.value)}
        />
      ) : (
        <div className="text-sm text-slate-300 whitespace-pre-wrap">
          {typeof content === 'string' ? content : JSON.stringify(content, null, 2)}
        </div>
      )}
    </div>
  );
}
```

### 5. Orchestration Tab (Reuse from Timeline)

```tsx
function OrchestrationTab({ orchestration, steps }: OrchestrationTabProps) {
  return (
    <div className="space-y-6">
      {/* Complexity Summary */}
      <div className="grid grid-cols-4 gap-4">
        <MetricCard
          label="Estrategia"
          value={orchestration.strategy}
          color="blue"
        />
        <MetricCard
          label="Pasos"
          value={orchestration.personas_invoked.length}
          color="purple"
        />
        <MetricCard
          label="Confianza"
          value={`${(orchestration.confidence_score * 100).toFixed(0)}%`}
          color="emerald"
        />
        <MetricCard
          label="Complejidad"
          value={orchestration.complexity_score.toFixed(1)}
          color="amber"
        />
      </div>

      {/* Orchestration Steps (reuse OrchestrationStep from timeline) */}
      <div className="relative">
        <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-gradient-to-b from-blue-500 via-purple-500 to-emerald-500"></div>
        <div className="space-y-6 ml-16">
          {steps.map((step, idx) => (
            <OrchestrationStep
              key={step.id}
              step={step}
              index={idx}
              totalSteps={steps.length}
              isRefinement={step.persona === orchestration.personas_invoked[idx - 1]}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
```

---

## 📡 API Endpoints (Backend)

### 1. Get Audit Data
`GET /api/sessions/{session_id}/audit`

```python
@router.get("/sessions/{session_id}/audit")
async def get_session_audit(session_id: str) -> dict:
    """Get complete audit data for doctor review."""
    # Fetch session metadata
    metadata = get_session_metadata(session_id)

    # Get SOAP note
    soap_data = get_soap_data(session_id)

    # Get orchestration steps
    orchestration = get_task_metadata(session_id, TaskType.SOAP_GENERATION)

    # Get diarization
    diarization_segments = get_diarization_segments(session_id)

    # Analyze for flags (low confidence, medication interactions, etc.)
    flags = analyze_session_flags(soap_data, orchestration)

    # Get existing doctor feedback (if any)
    doctor_feedback = get_doctor_feedback(session_id)

    return {
        "session_id": session_id,
        "patient": metadata.get("patient", {}),
        "session_metadata": {
            "date": metadata.get("created_at"),
            "duration_seconds": metadata.get("duration_seconds"),
            "doctor": metadata.get("doctor_name"),
            "status": metadata.get("audit_status", "pending_review"),
        },
        "orchestration": {
            "strategy": orchestration.get("orchestration_strategy"),
            "personas_invoked": orchestration.get("personas_invoked", []),
            "confidence_score": orchestration.get("confidence_score", 0.0),
            "complexity_score": orchestration.get("complexity_score", 0.0),
            "steps": orchestration.get("intermediate_outputs", []),
        },
        "soap_note": soap_data,
        "diarization": {
            "segments": diarization_segments,
        },
        "flags": flags,
        "doctor_feedback": doctor_feedback,
    }
```

### 2. Submit Doctor Feedback
`POST /api/sessions/{session_id}/feedback`

```python
class DoctorFeedbackRequest(BaseModel):
    rating: int  # 1-5 stars
    comments: str
    corrections: list[dict]  # [{"section": "subjective", "original": "...", "corrected": "..."}]
    decision: str  # "approved" | "rejected" | "needs_review"

@router.post("/sessions/{session_id}/feedback")
async def submit_doctor_feedback(
    session_id: str,
    feedback: DoctorFeedbackRequest
) -> dict:
    """Submit doctor's audit feedback."""
    # Save feedback to HDF5
    save_doctor_feedback(session_id, feedback.dict())

    # Update session audit status
    update_session_metadata(
        session_id,
        {
            "audit_status": feedback.decision,
            "audit_rating": feedback.rating,
            "audited_at": datetime.now(UTC).isoformat(),
            "audited_by": "Dr. Uriza",  # From auth context
        }
    )

    # If corrections were made, update SOAP note
    if feedback.corrections:
        apply_corrections_to_soap(session_id, feedback.corrections)

    logger.info(
        "DOCTOR_FEEDBACK_SUBMITTED",
        session_id=session_id,
        decision=feedback.decision,
        rating=feedback.rating,
        corrections_count=len(feedback.corrections),
    )

    return {
        "status": "feedback_saved",
        "session_id": session_id,
        "audit_status": feedback.decision,
    }
```

### 3. Analyze Session Flags
```python
def analyze_session_flags(soap_data: dict, orchestration: dict) -> list[dict]:
    """Analyze session for potential issues requiring doctor attention."""
    flags = []

    # Low confidence flag
    if orchestration.get("confidence_score", 1.0) < 0.95:
        flags.append({
            "type": "low_confidence",
            "severity": "warning",
            "message": f"Confidence score below 95% ({orchestration['confidence_score']:.0%})",
            "location": "overall",
        })

    # Medication interaction detection (example heuristic)
    medications = soap_data.get("plan", {}).get("medications", [])
    if any(med.get("name", "").lower() in ["enalapril", "losartán"] for med in medications):
        if len([m for m in medications if "enalapril" in m.get("name", "").lower() or "losartán" in m.get("name", "").lower()]) > 1:
            flags.append({
                "type": "medication_interaction",
                "severity": "critical",
                "message": "Posible interacción: Enalapril + Losartán (ambos IECA)",
                "location": "plan.medications",
            })

    # Missing objective data flag
    if not soap_data.get("objective"):
        flags.append({
            "type": "missing_objective_data",
            "severity": "warning",
            "message": "No se registraron signos vitales ni exploración física",
            "location": "objective",
        })

    return flags
```

---

## 🎯 Resultado Visual (Mockup)

### Audit Panel Overview:

```
┌─────────────────────────────────────────────────────────────────────┐
│ 🏥 Auditoría de Sesión                           ✅ Aprobar  ❌ Rechazar │
│ María González · 2025-11-20 14:30                                     │
├─────────────────────────────────────────────────────────────────────┤
│ ⚠️ ALERTA: Confidence score below 95% (92%)                          │
│ 🔴 CRÍTICO: Posible interacción medicamentosa (plan.medications)    │
├─────────────────────────────────────────────────────────────────────┤
│ [Overview] [SOAP Note] [Razonamiento IA] [Transcripción]            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│ 📊 Resumen de Procesamiento                                          │
│ ┌──────────────┬──────────────┬──────────────┬──────────────┐      │
│ │ Estrategia   │ Pasos        │ Confianza    │ Complejidad  │      │
│ │ COMPLEX      │ 3            │ 92%          │ 68.5         │      │
│ └──────────────┴──────────────┴──────────────┴──────────────┘      │
│                                                                       │
│ 🩺 SOAP Note Preview                                                 │
│ [S] Paciente refiere cefalea intensa de 3 días... [Corregir]        │
│ [O] PA: 140/90 mmHg, FC: 82 lpm, T: 36.8°C     [Corregir]        │
│ [A] Diabetes Tipo 2 descontrolada...           [Corregir]        │
│ [P] Ajustar dosis de metformina...              [Corregir]        │
│                                                                       │
├─────────────────────────────────────────────────────────────────────┤
│ 📝 Feedback del Doctor                                               │
│ Calidad General: ★★★★☆                                              │
│ Comentarios: [                                                    ]  │
│              [ El diagnóstico es correcto pero faltó mencionar... ]  │
│                                                                       │
│ ✅ Correcciones Aplicadas (2)                                        │
│   • subjective: "cefalea" → "cefalea pulsátil"                      │
│   • objective: "PA: 140/90" → "PA: 145/90 mmHg (brazo derecho)"     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📝 Beneficios

1. **Human-in-the-loop QA**: Doctor valida antes de guardar en expediente
2. **Continuous Learning**: Corrections se guardan para mejorar modelos futuros
3. **Safety Flags**: Alertas automáticas (interacciones, baja confianza)
4. **Audit Trail**: Trazabilidad completa de revisiones médicas
5. **NOM-004 Compliance**: Notas firmadas digitalmente por médico

---

## 🔮 Futuras Mejoras

- **Voice Annotations**: Doctor graba comentarios en lugar de escribir
- **Diff View**: Mostrar cambios aplicados por correcciones (before/after)
- **Bulk Approval**: Aprobar múltiples sesiones a la vez
- **ML Feedback Loop**: Correcciones entrenan fine-tuned model
- **Interoperability**: Exportar SOAP a FHIR/HL7 para EMR

---

**Status:** Design Complete ✅
**Next Step:** Implement backend endpoints + frontend components
