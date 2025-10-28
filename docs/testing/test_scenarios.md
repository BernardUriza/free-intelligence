# Test Scenarios - FI Consultation Module

**Purpose**: Acceptance testing for SOAP consultation event-sourcing MVP
**Format**: Given/When/Then (Gherkin style)
**PHI Policy**: NO real patient data - all scenarios use synthetic/demo data

---

## Scenario 1: Green Path - Simple Consultation (No Urgency)

**Category**: Happy path
**Risk Level**: LOW
**Expected Duration**: ~2 minutes
**Complexity**: Simple

### Given
- A new consultation session is created
- Patient stub: age=35, gender=male, weight=75kg
- Symptoms: "mild headache for 2 days, no other symptoms"
- No significant medical history
- No red flags detected

### When
1. User sends initial message: "I have a mild headache for 2 days"
2. System validates input as medical (category: symptom)
3. System extracts demographics and symptoms (iteration 1)
4. Completeness reaches 85% after 2 iterations
5. System generates SOAP note:
   - **Subjective**: Mild headache, 2 days duration
   - **Objective**: Vital signs within normal limits (inferred)
   - **Assessment**: Primary diagnosis = Tension headache (ICD-10: G44.2)
     - Differentials: Migraine (G43.9), Sinusitis (J01.9)
     - Defensive scores: All low gravity (1-3)
   - **Plan**:
     - OTC analgesics (ibuprofen 400mg q8h PRN)
     - Rest, hydration
     - Follow-up in 7 days if persistent
6. User reviews and confirms SOAP
7. System commits consultation with SHA256 hash

### Then
- ✅ Consultation state reconstructed correctly from events
- ✅ Event count >= 10 (messages, extraction, SOAP, commit)
- ✅ All events have valid audit_hash (SHA256)
- ✅ SOAP completeness >= 80%
- ✅ NOM-004 compliance >= 90%
- ✅ Urgency level = LOW
- ✅ No critical patterns detected
- ✅ Consultation status = COMMITTED
- ✅ commit_hash present and valid

### Expected Events
```
1. MESSAGE_RECEIVED (user: "I have a mild headache...")
2. EXTRACTION_STARTED (iteration=1)
3. DEMOGRAPHICS_UPDATED (age=35, gender=male)
4. SYMPTOMS_UPDATED (primary_symptoms=["headache"])
5. EXTRACTION_COMPLETED (completeness=60%)
6. EXTRACTION_STARTED (iteration=2)
7. CONTEXT_UPDATED (medical_history=[])
8. EXTRACTION_COMPLETED (completeness=85%)
9. SOAP_GENERATION_STARTED
10. SOAP_SECTION_COMPLETED (subjective)
11. SOAP_SECTION_COMPLETED (objective)
12. SOAP_SECTION_COMPLETED (assessment)
13. SOAP_SECTION_COMPLETED (plan)
14. SOAP_GENERATION_COMPLETED (quality=0.88)
15. URGENCY_CLASSIFIED (level=LOW, gravity=2)
16. CONSULTATION_COMMITTED (commit_hash=sha256:...)
```

### API Calls
```bash
# 1. Start consultation
POST /consultations
Body: {"user_id": "test-user-001", "patient_stub": {"age": 35, "gender": "male", "weight": 75}}
Response: {"consultation_id": "...", "session_id": "...", "created_at": "..."}

# 2. Append message event
POST /consultations/{id}/events
Body: {
  "event_type": "MESSAGE_RECEIVED",
  "payload": {
    "message_content": "I have a mild headache for 2 days",
    "message_role": "user"
  },
  "user_id": "test-user-001"
}

# 3. Get consultation state
GET /consultations/{id}
Response: {consultation with messages, extraction_data, soap_note}

# 4. Get SOAP view
GET /consultations/{id}/soap
Response: {soap_note, completeness, urgency_assessment, is_ready_for_commit=true}
```

---

## Scenario 2: Yellow Path - Moderate Urgency with Comorbidities

**Category**: Complex consultation
**Risk Level**: MEDIUM-HIGH
**Expected Duration**: ~5 minutes
**Complexity**: Moderate

### Given
- A new consultation session is created
- Patient stub: age=68, gender=male, weight=95kg
- Medical history: Type 2 diabetes, hypertension, ex-smoker
- Current medications: Metformin, Lisinopril
- Symptoms: "chest discomfort and shortness of breath after walking upstairs"

### When
1. User sends message describing symptoms
2. System validates and detects urgency indicators
3. System extracts data across 3 iterations:
   - Iteration 1: Demographics + primary symptoms
   - Iteration 2: Medical history + medications
   - Iteration 3: Additional context (smoking history, family history)
4. Completeness reaches 90% after 3 iterations
5. System classifies urgency:
   - Gravity score = 7 (chest discomfort + dyspnea)
   - Age modifier +1 (>65 years)
   - Comorbidity modifiers +1 (diabetes + hypertension)
   - Final gravity = 9 → URGENCY = HIGH
6. System generates SOAP with defensive medicine:
   - **Assessment**:
     - Primary: Unstable angina (I20.0)
     - Differentials (defensive-ranked):
       1. Acute MI (I21.9) - gravity=10, defensive_score=8.5
       2. Pulmonary embolism (I26.9) - gravity=9, defensive_score=7.8
       3. Heart failure exacerbation (I50.9) - gravity=8, defensive_score=7.1
       4. GERD (K21.9) - gravity=3, defensive_score=3.5
7. System generates urgent action plan:
   - **Plan**:
     - STAT ECG
     - Troponin levels (STAT)
     - Chest X-ray (URGENT)
     - Cardiology referral (URGENT)
     - Aspirin 325mg immediate
     - Hold metformin (renal protection)

### Then
- ✅ Urgency correctly classified as HIGH
- ✅ Gravity score = 9
- ✅ Time to action = "< 30 minutes"
- ✅ Defensive medicine applied (gravity * 0.7 + probability * 0.3)
- ✅ Critical differentials prioritized (MI, PE)
- ✅ Appropriate studies ordered (ECG STAT, troponin STAT)
- ✅ Specialist referral included (Cardiology URGENT)
- ✅ Risk factors documented (age, diabetes, HTN, smoking)
- ✅ SOAP completeness >= 90%
- ✅ Event stream contains URGENCY_CLASSIFIED event

### Expected Events
```
1. MESSAGE_RECEIVED (user message)
2. EXTRACTION_STARTED (iteration=1)
3. DEMOGRAPHICS_UPDATED
4. SYMPTOMS_UPDATED (primary=["chest discomfort", "dyspnea"])
5. EXTRACTION_COMPLETED (completeness=45%)
6. EXTRACTION_STARTED (iteration=2)
7. CONTEXT_UPDATED (history, meds)
8. EXTRACTION_COMPLETED (completeness=70%)
9. EXTRACTION_STARTED (iteration=3)
10. CONTEXT_UPDATED (smoking, family history)
11. EXTRACTION_COMPLETED (completeness=90%)
12. URGENCY_CLASSIFIED (level=HIGH, gravity=9, risk_factors=[...])
13. SOAP_GENERATION_STARTED
14. SOAP_SECTION_COMPLETED (subjective)
15. SOAP_SECTION_COMPLETED (objective)
16. SOAP_SECTION_COMPLETED (assessment with defensive ranking)
17. SOAP_SECTION_COMPLETED (plan with STAT orders)
18. SOAP_GENERATION_COMPLETED
19. CONSULTATION_COMMITTED
```

### API Validation Points
```bash
# After urgency classification
GET /consultations/{id}/soap

# Verify response contains:
{
  "urgency_assessment": {
    "urgency_level": "high",
    "gravity_score": 9,
    "time_to_action": "< 30 minutes",
    "risk_factors": ["age>65", "diabetes", "hypertension", "ex-smoker"],
    "immediate_actions": ["STAT ECG", "Troponin levels", "Cardiology consult"]
  },
  "soap_note": {
    "analisis": {
      "diagnosticos_diferenciales": [
        {
          "condicion": "Acute MI",
          "gravedad": "critica",
          "defensive_score": 8.5  // gravity * 0.7 + probability * 0.3
        },
        ...
      ]
    },
    "plan": {
      "estudios_adicionales": [
        {"estudio": "ECG", "urgencia": "stat"},
        {"estudio": "Troponin", "urgencia": "stat"}
      ]
    }
  }
}
```

---

## Scenario 3: Red Path - Critical Pattern ("Widow Maker")

**Category**: Emergency/Critical
**Risk Level**: CRITICAL
**Expected Duration**: ~1 minute (expedited)
**Complexity**: High urgency

### Given
- A new consultation session is created
- Patient stub: age=52, gender=male
- Symptoms: "sudden tearing chest pain radiating to back, started 20 minutes ago"

### When
1. User sends message describing symptoms
2. System validates input
3. **CRITICAL PATTERN DETECTED** during initial validation:
   - Pattern name: "Aortic Dissection"
   - Symptoms matched: ["chest pain", "tearing pain", "back pain", "sudden onset"]
   - Widow maker alert: TRUE
   - Gravity score: 10
4. System OVERRIDES urgency to CRITICAL immediately
5. System triggers emergency protocol:
   - Skip iterative extraction (use single-pass)
   - Expedite SOAP generation
   - Force defensive medicine mode
6. System generates SOAP with critical focus:
   - **Assessment**:
     - Primary: Acute aortic dissection (I71.0) - CRITICAL
     - Differentials:
       1. Acute MI (I21.9) - gravity=10
       2. Pulmonary embolism (I26.9) - gravity=9
       3. Esophageal rupture (K22.3) - gravity=9
   - **Plan**:
     - IMMEDIATE activation of emergency response
     - STAT CT angiography chest
     - STAT cardiothoracic surgery consult
     - IV access x2
     - Blood pressure control (avoid thrombolytics!)
     - NPO (nil per os)

### Then
- ✅ CRITICAL_PATTERN_DETECTED event present
- ✅ widow_maker_alert = true
- ✅ Urgency level = CRITICAL
- ✅ Gravity score = 10
- ✅ Time to action = "immediate (<5 minutes)"
- ✅ All differentials have gravity >= 9
- ✅ Emergency protocol activated
- ✅ SOAP generated in expedited mode
- ✅ Critical studies ordered (CT angio STAT)
- ✅ Surgical consult included
- ✅ Contraindications documented (avoid thrombolytics)

### Expected Events
```
1. MESSAGE_RECEIVED (user: "sudden tearing chest pain...")
2. CRITICAL_PATTERN_DETECTED (pattern="Aortic Dissection", widow_maker=true)
3. URGENCY_CLASSIFIED (level=CRITICAL, gravity=10, time_to_action="immediate")
4. EXTRACTION_STARTED (iteration=1, expedited=true)
5. DEMOGRAPHICS_UPDATED
6. SYMPTOMS_UPDATED
7. EXTRACTION_COMPLETED (completeness=60%, sufficient for emergency)
8. SOAP_GENERATION_STARTED (expedited=true)
9. SOAP_SECTION_COMPLETED (subjective)
10. SOAP_SECTION_COMPLETED (objective - inferred)
11. SOAP_SECTION_COMPLETED (assessment with critical differentials)
12. SOAP_SECTION_COMPLETED (plan with STAT orders)
13. SOAP_GENERATION_COMPLETED (quality=0.75, acceptable for emergency)
14. AUDIT_ENTRY_CREATED (level=critical, message="Widow maker detected")
15. CONSULTATION_COMMITTED (expedited commit)
```

### API Validation
```bash
# Critical pattern should be detected immediately
POST /consultations/{id}/events
Body: {
  "event_type": "MESSAGE_RECEIVED",
  "payload": {
    "message_content": "sudden tearing chest pain radiating to back...",
    "message_role": "user"
  },
  "user_id": "test-user-003"
}

# Verify immediate classification
GET /consultations/{id}/events
# Should show CRITICAL_PATTERN_DETECTED within first 3 events

# Verify urgency
GET /consultations/{id}/soap
Response should contain:
{
  "urgency_assessment": {
    "urgency_level": "critical",
    "gravity_score": 10,
    "time_to_action": "immediate",
    "identified_patterns": [
      {
        "name": "Aortic Dissection",
        "widow_maker_alert": true,
        "symptoms_matched": ["chest pain", "tearing", "back pain", "sudden"],
        "critical_differentials": ["Acute MI", "Pulmonary Embolism"]
      }
    ],
    "immediate_actions": [
      "Activate emergency response",
      "STAT CT angiography",
      "Cardiothoracic surgery consult",
      "Blood pressure control"
    ]
  }
}
```

---

## Test Execution Checklist

### Pre-execution
- [ ] EventStore initialized (corpus.h5 exists)
- [ ] FastAPI service running on port 7001
- [ ] Logger configured with America/Mexico_City timezone
- [ ] Test user IDs prepared (test-user-001, test-user-002, test-user-003)

### For Each Scenario
- [ ] Start consultation (POST /consultations)
- [ ] Capture consultation_id and session_id
- [ ] Append events sequentially
- [ ] Verify event stream (GET /consultations/{id}/events)
- [ ] Reconstruct state (GET /consultations/{id})
- [ ] Verify SOAP (GET /consultations/{id}/soap)
- [ ] Verify all audit_hash values present and valid
- [ ] Verify event count matches expected
- [ ] Verify consultation is_committed = true
- [ ] Export event stream to JSON for manual review

### Post-execution
- [ ] Verify all 3 consultations persisted in HDF5
- [ ] Verify file size reasonable (< 1MB for 3 consultations)
- [ ] Verify SHA256 hashes integrity
- [ ] Check logs for errors/warnings
- [ ] Document any deviations from expected behavior

---

## Success Criteria

### All Scenarios Must Pass:
1. ✅ Event stream complete and ordered chronologically
2. ✅ State reconstruction accurate (no data loss)
3. ✅ All events have valid SHA256 audit hashes
4. ✅ SOAP notes conform to NOM-004-SSA3-2012
5. ✅ Urgency classification correct for each scenario
6. ✅ Defensive medicine applied where appropriate
7. ✅ Critical patterns detected in real-time (Scenario 3)
8. ✅ API responses < 2 seconds per request
9. ✅ No PHI exposed in logs or error messages
10. ✅ HDF5 corpus remains < 10MB after all tests

---

## Failure Modes to Test

### Error Recovery
- [ ] Invalid event payload (malformed JSON)
- [ ] Missing required fields
- [ ] Duplicate event_id
- [ ] Event for non-existent consultation
- [ ] Corrupted SHA256 hash
- [ ] Network timeout during append
- [ ] HDF5 file locked (concurrent access)

### Expected Behaviors
- Return HTTP 400 for validation errors
- Return HTTP 404 for missing consultation
- Log errors to audit trail
- Maintain append-only integrity (no data loss)

---

## Notes

**PHI Compliance**: All test data is synthetic. No real patient information used.

**Timezone**: All timestamps in America/Mexico_City (ISO 8601 format)

**Performance Target**: Full consultation (start → commit) in < 2 minutes for simple cases

**Audit Trail**: Every event must have non-null audit_hash after commit

**Event Naming**: All events follow UPPER_SNAKE_CASE convention from MAPPING.json
