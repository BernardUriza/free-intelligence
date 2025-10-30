# cURL Examples - FI Consultation API

**Base URL**: `http://127.0.0.1:7001`
**Content-Type**: `application/json`
**Purpose**: Manual API testing and integration examples

---

## Health Check

```bash
curl -X GET http://127.0.0.1:7001/health

# Expected Response:
{
  "status": "healthy",
  "timestamp": "2025-10-28T12:00:00.000Z",
  "consultations_count": 0,
  "service": "fi_consultation_service"
}
```

---

## Scenario 1: Simple Consultation (Green Path)

### Step 1: Start Consultation

```bash
curl -X POST http://127.0.0.1:7001/consultations \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user-001",
    "patient_stub": {
      "age": 35,
      "gender": "male",
      "weight": 75
    }
  }'

# Expected Response:
{
  "consultation_id": "550e8400-e29b-41d4-a716-446655440000",
  "session_id": "660e8400-e29b-41d4-a716-446655440001",
  "created_at": "2025-10-28T12:00:00.000Z"
}

# Save consultation_id for next steps
export CONSULT_ID="550e8400-e29b-41d4-a716-446655440000"
```

### Step 2: User Sends Initial Message

```bash
curl -X POST http://127.0.0.1:7001/consultations/$CONSULT_ID/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "MESSAGE_RECEIVED",
    "payload": {
      "message_content": "I have a mild headache for 2 days",
      "message_role": "user",
      "metadata": {}
    },
    "user_id": "test-user-001"
  }'

# Expected Response:
{
  "event_id": "770e8400-e29b-41d4-a716-446655440002",
  "consultation_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_count": 2,
  "timestamp": "2025-10-28T12:00:05.000Z"
}
```

### Step 3: Start Data Extraction

```bash
curl -X POST http://127.0.0.1:7001/consultations/$CONSULT_ID/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "EXTRACTION_STARTED",
    "payload": {
      "iteration": 1,
      "context_message_count": 1,
      "has_previous_extraction": false
    },
    "user_id": "test-user-001"
  }'
```

### Step 4: Update Demographics

```bash
curl -X POST http://127.0.0.1:7001/consultations/$CONSULT_ID/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "DEMOGRAPHICS_UPDATED",
    "payload": {
      "age": 35,
      "gender": "male",
      "weight": 75,
      "height": 175
    },
    "user_id": "test-user-001"
  }'
```

### Step 5: Update Symptoms

```bash
curl -X POST http://127.0.0.1:7001/consultations/$CONSULT_ID/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "SYMPTOMS_UPDATED",
    "payload": {
      "primary_symptoms": ["headache"],
      "secondary_symptoms": [],
      "duration": "2 days",
      "severity": "mild",
      "location": "frontal",
      "quality": "dull ache",
      "aggravating_factors": null,
      "relieving_factors": null
    },
    "user_id": "test-user-001"
  }'
```

### Step 6: Complete Extraction

```bash
curl -X POST http://127.0.0.1:7001/consultations/$CONSULT_ID/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "EXTRACTION_COMPLETED",
    "payload": {
      "iteration": 1,
      "completeness": 85.0,
      "nom_compliance": 92.0,
      "missing_fields": [],
      "extraction_data": {
        "demographics": {"age": 35, "gender": "male", "weight": 75},
        "symptoms": {
          "primary_symptoms": ["headache"],
          "duration": "2 days",
          "severity": "mild"
        },
        "medicalHistory": {}
      }
    },
    "user_id": "test-user-001"
  }'
```

### Step 7: Start SOAP Generation

```bash
curl -X POST http://127.0.0.1:7001/consultations/$CONSULT_ID/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "SOAP_GENERATION_STARTED",
    "payload": {
      "extraction_completeness": 85.0,
      "nom_compliance": 92.0
    },
    "user_id": "test-user-001"
  }'
```

### Step 8: Complete SOAP Subjective Section

```bash
curl -X POST http://127.0.0.1:7001/consultations/$CONSULT_ID/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "SOAP_SECTION_COMPLETED",
    "payload": {
      "section_name": "subjective",
      "section_content": {
        "motivo_consulta": "Mild headache for 2 days",
        "historia_actual": "Patient reports mild frontal headache, dull in quality, present for 2 days. No associated symptoms.",
        "antecedentes": {
          "personales": [],
          "familiares": [],
          "medicamentos": [],
          "alergias": [],
          "quirurgicos": []
        }
      },
      "confidence": 0.89
    },
    "user_id": "test-user-001"
  }'
```

### Step 9: Classify Urgency

```bash
curl -X POST http://127.0.0.1:7001/consultations/$CONSULT_ID/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "URGENCY_CLASSIFIED",
    "payload": {
      "urgency_level": "low",
      "gravity_score": 2,
      "time_to_action": "routine (< 24 hours)",
      "identified_patterns": [],
      "risk_factors": []
    },
    "user_id": "test-user-001"
  }'
```

### Step 10: Complete SOAP Generation

```bash
curl -X POST http://127.0.0.1:7001/consultations/$CONSULT_ID/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "SOAP_GENERATION_COMPLETED",
    "payload": {
      "soap_data": {
        "consultation_id": "'$CONSULT_ID'",
        "subjetivo": {
          "motivo_consulta": "Mild headache for 2 days",
          "historia_actual": "Patient reports mild frontal headache...",
          "antecedentes": {
            "personales": [],
            "familiares": [],
            "medicamentos": [],
            "alergias": [],
            "quirurgicos": []
          }
        },
        "objetivo": {
          "signos_vitales": {
            "presion_arterial": "120/80",
            "frecuencia_cardiaca": 72,
            "temperatura": 36.8
          },
          "exploracion_fisica": {
            "aspecto": "Patient alert and oriented"
          }
        },
        "analisis": {
          "diagnostico_principal": {
            "condicion": "Tension headache",
            "cie10": "G44.2",
            "evidencia": ["Dull frontal pain", "No red flags"],
            "probabilidad": 0.85,
            "confianza": 0.90
          },
          "diagnosticos_diferenciales": [
            {
              "condicion": "Migraine",
              "cie10": "G43.9",
              "probabilidad": 0.10,
              "gravedad": "baja",
              "urgencia": "no_urgente",
              "defensive_score": 1.7,
              "evidencia": [],
              "descartar_mediante": ["Photophobia assessment"]
            }
          ],
          "factores_riesgo": [],
          "senos_peligro": [],
          "pronostico": {
            "inmediato": "Good",
            "corto": "Resolution expected in 3-5 days",
            "largo": "Excellent"
          }
        },
        "plan": {
          "tratamiento_farmacologico": [
            {
              "medicamento": "Ibuprofen",
              "dosis": "400mg",
              "via": "oral",
              "frecuencia": "every 8 hours",
              "duracion": "3 days",
              "indicacion": "Pain relief"
            }
          ],
          "tratamiento_no_farmacologico": [
            {
              "intervencion": "Rest and hydration",
              "frecuencia": "continuous",
              "duracion": "3 days",
              "objetivo": "Symptom relief"
            }
          ],
          "estudios_adicionales": [],
          "interconsultas": [],
          "seguimiento": {
            "proxima_cita": "7 days if persistent",
            "vigilar": ["Headache severity", "New symptoms"],
            "criterios_emergencia": ["Sudden severe headache", "Neurological symptoms"],
            "educacion_paciente": ["Adequate hydration", "Sleep hygiene"]
          }
        },
        "metadata": {
          "medico": "AI Assistant",
          "especialidad": "General Medicine",
          "fecha": "2025-10-28T12:00:00.000Z",
          "duracion_consulta": 5,
          "consentimiento_informado": true,
          "version_nom": "NOM-004-SSA3-2012"
        }
      },
      "quality_score": 0.88,
      "ready_for_commit": true
    },
    "user_id": "test-user-001"
  }'
```

### Step 11: Commit Consultation

```bash
curl -X POST http://127.0.0.1:7001/consultations/$CONSULT_ID/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "CONSULTATION_COMMITTED",
    "payload": {
      "soap_data": {},
      "committed_by": "test-user-001",
      "commit_hash": "abc123def456...",
      "quality_score": 0.88,
      "completeness": 85.0,
      "nom_compliance": 92.0
    },
    "user_id": "test-user-001"
  }'
```

### Step 12: Get Full Consultation State

```bash
curl -X GET http://127.0.0.1:7001/consultations/$CONSULT_ID

# Expected Response: Full consultation object with reconstructed state
```

### Step 13: Get SOAP View

```bash
curl -X GET http://127.0.0.1:7001/consultations/$CONSULT_ID/soap

# Expected Response:
{
  "consultation_id": "550e8400-e29b-41d4-a716-446655440000",
  "soap_note": { ... },
  "completeness": {
    "percentage": 85.0,
    "nom_compliance": 92.0,
    "ready_for_commit": true
  },
  "urgency_assessment": {
    "urgency_level": "low",
    "gravity_score": 2,
    "time_to_action": "routine (< 24 hours)"
  },
  "is_ready_for_commit": true
}
```

### Step 14: Get Event Stream

```bash
curl -X GET "http://127.0.0.1:7001/consultations/$CONSULT_ID/events?limit=100&offset=0"

# Expected Response:
{
  "consultation_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_count": 12,
  "returned_count": 12,
  "offset": 0,
  "events": [
    {
      "event_id": "...",
      "consultation_id": "...",
      "timestamp": "...",
      "event_type": "MESSAGE_RECEIVED",
      "payload": { ... },
      "metadata": { ... },
      "audit_hash": "sha256:..."
    },
    ...
  ]
}
```

---

## Scenario 2: Moderate Urgency (Yellow Path)

### Start Consultation with Comorbidities

```bash
curl -X POST http://127.0.0.1:7001/consultations \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user-002",
    "patient_stub": {
      "age": 68,
      "gender": "male",
      "weight": 95
    }
  }'

export CONSULT_ID2="<consultation_id_from_response>"
```

### Append Critical Message

```bash
curl -X POST http://127.0.0.1:7001/consultations/$CONSULT_ID2/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "MESSAGE_RECEIVED",
    "payload": {
      "message_content": "I have chest discomfort and shortness of breath after walking upstairs. I have diabetes and high blood pressure.",
      "message_role": "user"
    },
    "user_id": "test-user-002"
  }'
```

### Classify as HIGH Urgency

```bash
curl -X POST http://127.0.0.1:7001/consultations/$CONSULT_ID2/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "URGENCY_CLASSIFIED",
    "payload": {
      "urgency_level": "high",
      "gravity_score": 9,
      "time_to_action": "urgent (< 30 minutes)",
      "identified_patterns": [
        {
          "symptoms": ["chest discomfort", "dyspnea"],
          "risk_factors": ["age>65", "diabetes", "hypertension"]
        }
      ],
      "risk_factors": ["age", "diabetes", "hypertension"]
    },
    "user_id": "test-user-002"
  }'
```

---

## Scenario 3: Critical Pattern (Red Path)

### Start Consultation

```bash
curl -X POST http://127.0.0.1:7001/consultations \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user-003",
    "patient_stub": {
      "age": 52,
      "gender": "male"
    }
  }'

export CONSULT_ID3="<consultation_id_from_response>"
```

### Widow Maker Symptoms

```bash
curl -X POST http://127.0.0.1:7001/consultations/$CONSULT_ID3/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "MESSAGE_RECEIVED",
    "payload": {
      "message_content": "I have sudden tearing chest pain radiating to my back. It started 20 minutes ago and is very severe.",
      "message_role": "user"
    },
    "user_id": "test-user-003"
  }'
```

### Detect Critical Pattern

```bash
curl -X POST http://127.0.0.1:7001/consultations/$CONSULT_ID3/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "CRITICAL_PATTERN_DETECTED",
    "payload": {
      "pattern_name": "Aortic Dissection",
      "gravity_score": 10,
      "widow_maker_alert": true,
      "symptoms_matched": ["chest pain", "tearing pain", "back pain", "sudden onset"],
      "critical_differentials": ["Acute MI", "Pulmonary Embolism", "Esophageal Rupture"],
      "time_to_action": "immediate"
    },
    "user_id": "test-user-003"
  }'
```

### Override to CRITICAL Urgency

```bash
curl -X POST http://127.0.0.1:7001/consultations/$CONSULT_ID3/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "URGENCY_CLASSIFIED",
    "payload": {
      "urgency_level": "critical",
      "gravity_score": 10,
      "time_to_action": "immediate (< 5 minutes)",
      "identified_patterns": [
        {
          "name": "Aortic Dissection",
          "widow_maker_alert": true
        }
      ],
      "risk_factors": [],
      "immediate_actions": [
        "Activate emergency response",
        "STAT CT angiography",
        "Cardiothoracic surgery consult"
      ]
    },
    "user_id": "test-user-003"
  }'
```

---

## Utility Commands

### List All Consultations

```bash
curl -X GET http://127.0.0.1:7001/consultations

# Note: Endpoint may need to be added to service
```

### Get Event Count

```bash
curl -X GET "http://127.0.0.1:7001/consultations/$CONSULT_ID/events?limit=0"

# Check event_count in response
```

### Verify SHA256 Hashes

```bash
# Get all events
curl -X GET "http://127.0.0.1:7001/consultations/$CONSULT_ID/events" | \
  jq '.events[] | {event_id, event_type, has_hash: (.audit_hash != null)}'
```

### Pretty Print SOAP

```bash
curl -X GET http://127.0.0.1:7001/consultations/$CONSULT_ID/soap | jq .
```

---

## Batch Testing Script

```bash
#!/bin/bash

# Run all 3 scenarios

echo "=== Scenario 1: Green Path ==="
CONSULT1=$(curl -s -X POST http://127.0.0.1:7001/consultations \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test-user-001", "patient_stub": {"age": 35, "gender": "male"}}' \
  | jq -r '.consultation_id')

echo "Consultation ID: $CONSULT1"

# Add events for scenario 1...

echo "=== Scenario 2: Yellow Path ==="
CONSULT2=$(curl -s -X POST http://127.0.0.1:7001/consultations \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test-user-002", "patient_stub": {"age": 68, "gender": "male"}}' \
  | jq -r '.consultation_id')

echo "Consultation ID: $CONSULT2"

# Add events for scenario 2...

echo "=== Scenario 3: Red Path ==="
CONSULT3=$(curl -s -X POST http://127.0.0.1:7001/consultations \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test-user-003", "patient_stub": {"age": 52, "gender": "male"}}' \
  | jq -r '.consultation_id')

echo "Consultation ID: $CONSULT3"

# Add events for scenario 3...

echo "=== Test Summary ==="
echo "Consultation 1: $CONSULT1"
echo "Consultation 2: $CONSULT2"
echo "Consultation 3: $CONSULT3"
```

---

## Notes

- All timestamps are in ISO 8601 format with timezone
- All event payloads must match schema in `fi_consult_models.py`
- SHA256 audit hashes are calculated server-side during append
- Use `jq` for pretty JSON formatting: `curl ... | jq .`
- For Windows, use PowerShell's `Invoke-RestMethod` instead of curl
