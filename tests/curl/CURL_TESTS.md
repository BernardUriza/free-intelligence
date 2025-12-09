# AURITY - Pruebas con cURL

**Última actualización**: 2025-12-08
**Propósito**: Pruebas completas del sistema AURITY usando cURL
**Producción**: https://app.aurity.io
**Local**: http://localhost:7001

---

## 🎯 Tabla de Contenidos

1. [Configuración Inicial](#configuración-inicial)
2. [Autenticación](#autenticación)
3. [Sesiones Médicas](#sesiones-médicas)
4. [Transcripción de Audio](#transcripción-de-audio)
5. [Diarización](#diarización)
6. [Generación SOAP](#generación-soap)
7. [Check-in Receptionist](#check-in-receptionist)
8. [Monitoreo y Auditoría](#monitoreo-y-auditoría)
9. [Troubleshooting](#troubleshooting)

---

## 🔧 Configuración Inicial

### Variables de Entorno

```bash
# Crear archivo .env.curl en el root del proyecto
cat > .env.curl << 'EOF'
# Backend URL
BACKEND_URL="http://localhost:7001"
# BACKEND_URL="https://app.aurity.io"  # Producción

# Auth0 Token (obtener desde frontend)
AUTH_TOKEN="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIs..."

# Session ID de prueba (generar con uuidgen)
SESSION_ID="$(uuidgen | tr '[:upper:]' '[:lower:]')"

# Clinic ID de prueba
CLINIC_ID="clinic_001"
EOF

# Cargar variables
source .env.curl
```

### Generar Session ID Único

```bash
# macOS/Linux
export SESSION_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')
echo "Session ID: $SESSION_ID"

# Output: session_id: a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

### Verificar Conectividad

```bash
# Health check
curl -X GET "$BACKEND_URL/health" \
  -H "Accept: application/json" | jq

# Respuesta esperada:
# {
#   "status": "healthy",
#   "timestamp": "2025-12-08T10:30:00Z",
#   "version": "0.3.0"
# }
```

---

## 🔐 Autenticación

### Obtener Token desde Frontend

1. **Opción 1 - DevTools**:
```javascript
// En consola del navegador (app.aurity.io)
const token = await auth0.getAccessTokenSilently()
console.log(token)
// Copiar token y pegarlo en .env.curl
```

2. **Opción 2 - Network Tab**:
```bash
# 1. Abrir DevTools → Network
# 2. Hacer request a cualquier endpoint
# 3. Buscar header Authorization: Bearer ...
# 4. Copiar token
```

### Verificar Token

```bash
curl -X GET "$BACKEND_URL/api/workflows/aurity/sessions" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Accept: application/json" | jq

# Si falla con 401:
# - Token expirado (renovar)
# - Token inválido (verificar formato)
# - Token de ambiente incorrecto (dev vs prod)
```

---

## 🏥 Sesiones Médicas

### 1. Crear Sesión Médica (Stream Chunk 0)

```bash
# Preparar audio de prueba
echo "Hola doctor, me duele la cabeza" | \
  ffmpeg -f lavfi -i "sine=frequency=1000:duration=2" \
  -ar 16000 -ac 1 -f wav test_audio.wav -y

# Enviar primer chunk (inicializa sesión)
curl -X POST "$BACKEND_URL/api/transcription/stream" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -F "session_id=$SESSION_ID" \
  -F "chunk_number=0" \
  -F "mode=medical" \
  -F "patient_name=Juan Pérez" \
  -F "patient_age=45" \
  -F "patient_id=PAC001" \
  -F "chief_complaint=Cefalea intensa" \
  -F "timestamp_start=0.0" \
  -F "timestamp_end=2.0" \
  -F "audio=@test_audio.wav" | jq

# Respuesta esperada (202 Accepted):
# {
#   "session_id": "a1b2c3d4-...",
#   "chunk_number": 0,
#   "status": "pending",
#   "total_chunks": 1,
#   "processed_chunks": 0
# }
```

### 2. Enviar Chunks Adicionales

```bash
# Chunk 1
curl -X POST "$BACKEND_URL/api/transcription/stream" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -F "session_id=$SESSION_ID" \
  -F "chunk_number=1" \
  -F "mode=medical" \
  -F "timestamp_start=2.0" \
  -F "timestamp_end=4.0" \
  -F "audio=@test_audio.wav" | jq

# Chunk 2
curl -X POST "$BACKEND_URL/api/transcription/stream" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -F "session_id=$SESSION_ID" \
  -F "chunk_number=2" \
  -F "mode=medical" \
  -F "timestamp_start=4.0" \
  -F "timestamp_end=6.0" \
  -F "audio=@test_audio.wav" | jq
```

### 3. Polling de Estado

```bash
# Poll cada 500ms hasta completar
for i in {1..20}; do
  echo "--- Poll #$i ---"
  curl -X GET "$BACKEND_URL/api/transcription/jobs/$SESSION_ID" \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    -H "Accept: application/json" | jq '.status, .processed_chunks, .total_chunks'

  sleep 0.5
done

# Respuesta en progreso:
# {
#   "session_id": "a1b2c3d4-...",
#   "status": "in_progress",
#   "total_chunks": 3,
#   "processed_chunks": 2,
#   "progress_percent": 66,
#   "chunks": [...]
# }

# Respuesta completada:
# {
#   "session_id": "a1b2c3d4-...",
#   "status": "completed",
#   "total_chunks": 3,
#   "processed_chunks": 3,
#   "progress_percent": 100,
#   "chunks": [
#     {
#       "chunk_number": 0,
#       "transcript": "Hola doctor, me duele la cabeza",
#       "confidence": 0.95,
#       "duration": 2.0
#     },
#     ...
#   ]
# }
```

### 4. Finalizar Sesión (Guardar Audio Completo)

```bash
# Crear audio completo de prueba
cat test_audio.wav test_audio.wav test_audio.wav > full_audio.wav

# Crear JSON de transcripts WebSpeech
cat > webspeech.json << 'EOF'
[
  {
    "timestamp": 0.0,
    "text": "Hola doctor, me duele la cabeza",
    "confidence": 0.95
  },
  {
    "timestamp": 2.0,
    "text": "desde hace dos días",
    "confidence": 0.92
  },
  {
    "timestamp": 4.0,
    "text": "y también tengo náuseas",
    "confidence": 0.88
  }
]
EOF

# Enviar audio completo + transcripts
curl -X POST "$BACKEND_URL/api/transcription/end-session" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -F "session_id=$SESSION_ID" \
  -F "full_audio=@full_audio.wav" \
  -F "webspeech_final=$(cat webspeech.json | jq -c .)" | jq

# Respuesta esperada:
# {
#   "audio_path": "storage/audio/a1b2c3d4-.../full.wav",
#   "chunks_count": 3,
#   "duration": 6.0,
#   "message": "Session ended successfully"
# }
```

### 5. Ver Timeline de Sesiones

```bash
# Listar todas las sesiones
curl -X GET "$BACKEND_URL/api/workflows/aurity/sessions" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Accept: application/json" | jq

# Filtrar por fecha
curl -X GET "$BACKEND_URL/api/workflows/aurity/sessions?start_date=2025-12-01&end_date=2025-12-31" \
  -H "Authorization: Bearer $AUTH_TOKEN" | jq

# Ver detalles de sesión específica
curl -X GET "$BACKEND_URL/api/workflows/aurity/sessions/$SESSION_ID" \
  -H "Authorization: Bearer $AUTH_TOKEN" | jq
```

---

## 🎤 Transcripción de Audio

### 1. Subir Chunk con Transcripción Deepgram

```bash
# El endpoint /stream automáticamente:
# 1. Envía audio a Deepgram
# 2. Obtiene transcripción
# 3. Guarda chunk en HDF5

curl -X POST "$BACKEND_URL/api/transcription/stream" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -F "session_id=$SESSION_ID" \
  -F "chunk_number=0" \
  -F "mode=medical" \
  -F "audio=@test_audio.wav" | jq
```

### 2. Modo Chat (Sin Polling)

```bash
# Chat mode: transcripción síncrona
export CHAT_SESSION_ID="chat_user_123"

curl -X POST "$BACKEND_URL/api/transcription/stream" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -F "session_id=$CHAT_SESSION_ID" \
  -F "chunk_number=0" \
  -F "mode=chat" \
  -F "audio=@test_audio.wav" | jq

# Respuesta inmediata:
# {
#   "session_id": "chat_user_123",
#   "chunk_number": 0,
#   "status": "completed",  # ✅ Inmediato
#   "total_chunks": 1,
#   "processed_chunks": 1
# }

# Obtener transcript
curl -X GET "$BACKEND_URL/api/transcription/jobs/$CHAT_SESSION_ID" \
  -H "Authorization: Bearer $AUTH_TOKEN" | jq '.chunks[0].transcript'
```

### 3. Ver Todos los Chunks de Sesión

```bash
curl -X GET "$BACKEND_URL/api/transcription/sessions/$SESSION_ID/chunks" \
  -H "Authorization: Bearer $AUTH_TOKEN" | jq

# Respuesta:
# {
#   "session_id": "a1b2c3d4-...",
#   "total_chunks": 3,
#   "chunks": [
#     {
#       "chunk_number": 0,
#       "transcript": "...",
#       "confidence": 0.95,
#       "duration": 2.0,
#       "timestamp_start": 0.0,
#       "timestamp_end": 2.0,
#       "speaker": "PATIENT",
#       "provider": "deepgram"
#     },
#     ...
#   ]
# }
```

---

## 👥 Diarización

### 1. Ejecutar Diarización

```bash
# Requiere sesión completada con audio
curl -X POST "$BACKEND_URL/api/workflows/aurity/sessions/$SESSION_ID/diarization" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" | jq

# Respuesta (202 Accepted):
# {
#   "job_id": "diarization_a1b2c3d4-...",
#   "status": "pending",
#   "message": "Diarization job dispatched"
# }
```

### 2. Verificar Estado de Diarización

```bash
# Polling cada segundo
for i in {1..30}; do
  echo "--- Checking diarization $i/30 ---"
  curl -X GET "$BACKEND_URL/api/workflows/aurity/sessions/$SESSION_ID/diarization/status" \
    -H "Authorization: Bearer $AUTH_TOKEN" | jq '.status'

  sleep 1
done

# Respuesta completada:
# {
#   "status": "completed",
#   "segments": [
#     {
#       "start": 0.0,
#       "end": 2.5,
#       "speaker": "SPEAKER_00",  # Doctor
#       "text": "Buenas tardes, ¿cómo se siente?"
#     },
#     {
#       "start": 2.5,
#       "end": 5.0,
#       "speaker": "SPEAKER_01",  # Paciente
#       "text": "Me duele mucho la cabeza"
#     }
#   ]
# }
```

### 3. Actualizar Etiquetas de Speaker

```bash
# Marcar SPEAKER_00 como DOCTOR
curl -X PUT "$BACKEND_URL/api/workflows/aurity/sessions/$SESSION_ID/diarization/segments" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "segment_id": 0,
    "speaker_label": "DOCTOR"
  }' | jq

# Marcar SPEAKER_01 como PATIENT
curl -X PUT "$BACKEND_URL/api/workflows/aurity/sessions/$SESSION_ID/diarization/segments" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "segment_id": 1,
    "speaker_label": "PATIENT"
  }' | jq
```

---

## 📋 Generación SOAP

### 1. Generar Nota SOAP

```bash
# Requiere sesión con transcripción completa
curl -X POST "$BACKEND_URL/api/workflows/aurity/sessions/$SESSION_ID/soap" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" | jq

# Respuesta (202 Accepted):
# {
#   "job_id": "soap_a1b2c3d4-...",
#   "status": "pending",
#   "message": "SOAP generation job dispatched"
# }
```

### 2. Polling de SOAP Generado

```bash
# Esperar hasta completar (puede tomar 10-30 segundos)
for i in {1..60}; do
  echo "--- Checking SOAP $i/60 ---"

  RESPONSE=$(curl -s -X GET "$BACKEND_URL/api/workflows/aurity/sessions/$SESSION_ID" \
    -H "Authorization: Bearer $AUTH_TOKEN")

  STATUS=$(echo "$RESPONSE" | jq -r '.soap_status // "pending"')
  echo "Status: $STATUS"

  if [ "$STATUS" = "completed" ]; then
    echo "$RESPONSE" | jq '.soap_note'
    break
  fi

  sleep 1
done

# Respuesta completada:
# {
#   "subjective": "Paciente masculino de 45 años...",
#   "objective": "Signos vitales: PA 120/80...",
#   "assessment": "1. Cefalea tensional...",
#   "plan": "1. Ibuprofeno 400mg c/8h..."
# }
```

### 3. Feedback de Doctor en SOAP

```bash
# Enviar correcciones/aprobación
curl -X POST "$BACKEND_URL/api/workflows/aurity/sessions/$SESSION_ID/feedback" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "feedback_type": "soap_correction",
    "original_text": "Cefalea tensional",
    "corrected_text": "Migraña con aura",
    "section": "assessment",
    "severity": "minor",
    "comments": "El paciente reportó aura visual, más compatible con migraña"
  }' | jq

# Respuesta:
# {
#   "feedback_id": "feedback_001",
#   "status": "saved",
#   "message": "Feedback recorded for future model training"
# }
```

---

## 🏨 Check-in Receptionist

### 1. Generar QR Code de Clínica

```bash
# Generar QR para tablet en sala de espera
curl -X POST "$BACKEND_URL/api/checkin/qr/generate" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "clinic_id": "clinic_001",
    "expiry_minutes": 1440
  }' | jq > qr_response.json

# Extraer QR code base64
cat qr_response.json | jq -r '.qr_code_base64' | base64 -d > qr_checkin.png

echo "QR guardado en qr_checkin.png"
echo "URL de checkin: $(cat qr_response.json | jq -r '.qr_url')"
```

### 2. Iniciar Sesión de Check-in

```bash
# Simular escaneo de QR
curl -X POST "$BACKEND_URL/api/checkin/session/start" \
  -H "Content-Type: application/json" \
  -d '{
    "clinic_id": "clinic_001",
    "device_type": "tablet"
  }' | jq > checkin_session.json

export CHECKIN_SESSION_ID=$(cat checkin_session.json | jq -r '.session_id')
echo "Check-in session: $CHECKIN_SESSION_ID"
```

### 3. Identificar Paciente por Nombre

```bash
curl -X POST "$BACKEND_URL/api/checkin/identify/name" \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$CHECKIN_SESSION_ID\",
    \"first_name\": \"Juan\",
    \"last_name\": \"Pérez\",
    \"date_of_birth\": \"1980-05-15\"
  }" | jq

# Respuesta exitosa:
# {
#   "patient_id": "pat_001",
#   "display_name": "Juan P.",
#   "appointments": [
#     {
#       "appointment_id": "apt_001",
#       "doctor_name": "Dr. García",
#       "scheduled_at": "2025-12-08T14:00:00Z",
#       "specialty": "Medicina General"
#     }
#   ]
# }
```

### 4. Identificar por CURP

```bash
curl -X POST "$BACKEND_URL/api/checkin/identify/curp" \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$CHECKIN_SESSION_ID\",
    \"curp\": \"PERJ800515HDFRNN01\"
  }" | jq
```

### 5. Ver Acciones Pendientes

```bash
# Ver formularios/documentos que debe completar
curl -X GET "$BACKEND_URL/api/checkin/actions/$CHECKIN_SESSION_ID" \
  -H "Accept: application/json" | jq

# Respuesta:
# {
#   "pending_actions": [
#     {
#       "action_id": "act_001",
#       "action_type": "medical_history_form",
#       "title": "Actualizar Historia Clínica",
#       "description": "Complete su historia clínica actualizada",
#       "priority": "high",
#       "status": "pending"
#     },
#     {
#       "action_id": "act_002",
#       "action_type": "consent_form",
#       "title": "Consentimiento Informado",
#       "description": "Firme el consentimiento para tratamiento",
#       "priority": "high",
#       "status": "pending"
#     }
#   ]
# }
```

### 6. Completar Acción

```bash
curl -X POST "$BACKEND_URL/api/checkin/actions/complete" \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$CHECKIN_SESSION_ID\",
    \"action_id\": \"act_001\",
    \"response_data\": {
      \"allergies\": \"Penicilina\",
      \"current_medications\": \"Metformina 500mg\",
      \"chronic_conditions\": \"Diabetes tipo 2\"
    }
  }" | jq
```

### 7. Completar Check-in

```bash
curl -X POST "$BACKEND_URL/api/checkin/complete" \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$CHECKIN_SESSION_ID\",
    \"appointment_id\": \"apt_001\"
  }" | jq

# Respuesta:
# {
#   "status": "completed",
#   "queue_position": 3,
#   "estimated_wait_minutes": 15,
#   "message": "Check-in completado. Por favor tome asiento en la sala de espera."
# }
```

### 8. Ver Sala de Espera

```bash
curl -X GET "$BACKEND_URL/api/checkin/waiting-room/clinic_001" \
  -H "Accept: application/json" | jq

# Respuesta:
# {
#   "clinic_id": "clinic_001",
#   "total_waiting": 5,
#   "patients": [
#     {
#       "display_name": "María G.",
#       "queue_position": 1,
#       "check_in_time": "2025-12-08T13:45:00Z",
#       "status": "waiting"
#     },
#     {
#       "display_name": "Juan P.",
#       "queue_position": 2,
#       "check_in_time": "2025-12-08T13:50:00Z",
#       "status": "waiting"
#     }
#   ]
# }
```

---

## 📊 Monitoreo y Auditoría

### 1. Monitorear Sesión en Vivo

```bash
# Ver estado en tiempo real
curl -X GET "$BACKEND_URL/api/workflows/aurity/sessions/$SESSION_ID/monitor" \
  -H "Authorization: Bearer $AUTH_TOKEN" | jq

# Respuesta:
# {
#   "session_id": "a1b2c3d4-...",
#   "current_task": "TRANSCRIPTION",
#   "tasks_completed": ["AUDIO_CAPTURE"],
#   "tasks_pending": ["DIARIZATION", "SOAP_GENERATION"],
#   "audio_duration_seconds": 120.5,
#   "chunks_count": 12,
#   "last_activity": "2025-12-08T14:30:15Z"
# }
```

### 2. Ver Audit Log

```bash
curl -X GET "$BACKEND_URL/api/workflows/aurity/sessions/$SESSION_ID/audit" \
  -H "Authorization: Bearer $AUTH_TOKEN" | jq

# Respuesta:
# {
#   "session_id": "a1b2c3d4-...",
#   "events": [
#     {
#       "timestamp": "2025-12-08T14:00:00Z",
#       "event_type": "SESSION_CREATED",
#       "user_id": "user_123",
#       "details": {"patient_id": "PAC001"}
#     },
#     {
#       "timestamp": "2025-12-08T14:00:05Z",
#       "event_type": "CHUNK_UPLOADED",
#       "details": {"chunk_number": 0, "duration": 2.0}
#     },
#     {
#       "timestamp": "2025-12-08T14:02:00Z",
#       "event_type": "TRANSCRIPTION_COMPLETED",
#       "details": {"chunks_count": 12, "total_duration": 120.5}
#     }
#   ]
# }
```

### 3. Exportar Transcripción

```bash
# Descargar como TXT
curl -X GET "$BACKEND_URL/api/export/transcript/$SESSION_ID?format=txt" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -o "transcript_$SESSION_ID.txt"

# Descargar como JSON
curl -X GET "$BACKEND_URL/api/export/transcript/$SESSION_ID?format=json" \
  -H "Authorization: Bearer $AUTH_TOKEN" | jq > "transcript_$SESSION_ID.json"

# Descargar como DOCX
curl -X GET "$BACKEND_URL/api/export/transcript/$SESSION_ID?format=docx" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -o "transcript_$SESSION_ID.docx"
```

### 4. Exportar Nota SOAP

```bash
curl -X GET "$BACKEND_URL/api/export/soap/$SESSION_ID?format=pdf" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -o "soap_note_$SESSION_ID.pdf"
```

---

## 🛠️ Troubleshooting

### Verificar Integridad de HDF5

```bash
# Ver checksum de sesión
curl -X GET "$BACKEND_URL/api/internal/sessions/$SESSION_ID/integrity" \
  -H "Authorization: Bearer $AUTH_TOKEN" | jq

# Respuesta:
# {
#   "session_id": "a1b2c3d4-...",
#   "file_path": "storage/sessions/a1b2c3d4-.../session.h5",
#   "checksum_expected": "abc123...",
#   "checksum_actual": "abc123...",
#   "is_valid": true
# }
```

### Reintentar Tarea Fallida

```bash
# Reintentar transcripción de chunk específico
curl -X POST "$BACKEND_URL/api/internal/sessions/$SESSION_ID/retry" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "TRANSCRIPTION",
    "chunk_number": 5
  }' | jq
```

### Ver Logs de Sesión

```bash
curl -X GET "$BACKEND_URL/api/workflows/aurity/sessions/$SESSION_ID/logs" \
  -H "Authorization: Bearer $AUTH_TOKEN" | jq

# Filtrar por nivel
curl -X GET "$BACKEND_URL/api/workflows/aurity/sessions/$SESSION_ID/logs?level=ERROR" \
  -H "Authorization: Bearer $AUTH_TOKEN" | jq
```

### Test End-to-End Completo

```bash
#!/bin/bash
# test_session_e2e.sh

set -e

echo "=== AURITY E2E Test ==="

# 1. Generar session ID
export SESSION_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')
echo "Session ID: $SESSION_ID"

# 2. Crear audio de prueba
echo "Generando audio de prueba..."
ffmpeg -f lavfi -i "sine=frequency=1000:duration=3" \
  -ar 16000 -ac 1 -f wav test.wav -y -loglevel quiet

# 3. Iniciar sesión con chunk 0
echo "Subiendo chunk 0..."
curl -s -X POST "$BACKEND_URL/api/transcription/stream" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -F "session_id=$SESSION_ID" \
  -F "chunk_number=0" \
  -F "mode=medical" \
  -F "patient_name=Test Patient" \
  -F "patient_age=30" \
  -F "audio=@test.wav" | jq -r '.status'

# 4. Polling de transcripción
echo "Esperando transcripción..."
for i in {1..20}; do
  STATUS=$(curl -s -X GET "$BACKEND_URL/api/transcription/jobs/$SESSION_ID" \
    -H "Authorization: Bearer $AUTH_TOKEN" | jq -r '.status')

  echo "  Intento $i/20: $STATUS"

  if [ "$STATUS" = "completed" ]; then
    break
  fi
  sleep 1
done

# 5. Finalizar sesión
echo "Finalizando sesión..."
curl -s -X POST "$BACKEND_URL/api/transcription/end-session" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -F "session_id=$SESSION_ID" \
  -F "full_audio=@test.wav" | jq -r '.message'

# 6. Ejecutar diarización
echo "Ejecutando diarización..."
curl -s -X POST "$BACKEND_URL/api/workflows/aurity/sessions/$SESSION_ID/diarization" \
  -H "Authorization: Bearer $AUTH_TOKEN" | jq -r '.status'

# 7. Generar SOAP
echo "Generando nota SOAP..."
curl -s -X POST "$BACKEND_URL/api/workflows/aurity/sessions/$SESSION_ID/soap" \
  -H "Authorization: Bearer $AUTH_TOKEN" | jq -r '.status'

# 8. Polling SOAP
echo "Esperando SOAP..."
for i in {1..60}; do
  SOAP_STATUS=$(curl -s -X GET "$BACKEND_URL/api/workflows/aurity/sessions/$SESSION_ID" \
    -H "Authorization: Bearer $AUTH_TOKEN" | jq -r '.soap_status // "pending"')

  echo "  Intento $i/60: $SOAP_STATUS"

  if [ "$SOAP_STATUS" = "completed" ]; then
    break
  fi
  sleep 1
done

# 9. Ver resultado final
echo ""
echo "=== Resultado Final ==="
curl -s -X GET "$BACKEND_URL/api/workflows/aurity/sessions/$SESSION_ID" \
  -H "Authorization: Bearer $AUTH_TOKEN" | jq '{
    session_id,
    transcription_status: .transcription_status,
    diarization_status: .diarization_status,
    soap_status: .soap_status,
    audio_duration: .audio_duration_seconds
  }'

# Cleanup
rm -f test.wav

echo ""
echo "✅ Test completado"
echo "Session ID: $SESSION_ID"
```

Hacer ejecutable:
```bash
chmod +x test_session_e2e.sh
./test_session_e2e.sh
```

---

## 📝 Notas Finales

### Rate Limits

- **Transcripción**: 10 requests/segundo por sesión
- **Check-in**: 5 intentos de identificación por sesión
- **SOAP**: 1 request/minuto por sesión

### Formatos de Audio Soportados

- WAV (PCM 16-bit, 16kHz mono recomendado)
- WebM (Opus codec)
- MP3 (CBR 128kbps+)
- FLAC (lossless)
- OGG (Vorbis codec)

### Tiempos Esperados

- **Transcripción chunk**: 200-500ms (Deepgram)
- **Diarización sesión completa**: 5-15 segundos
- **Generación SOAP**: 10-30 segundos (LLM)
- **Check-in completo**: 30-60 segundos

### Seguridad

- **NUNCA** hacer commit de tokens en `.env.curl`
- Tokens expiran cada 24 horas (renovar diariamente)
- Usar HTTPS en producción (siempre)
- No exponer `/api/internal/*` al frontend

---

**Autor**: Bernard Uriza Orozco
**Proyecto**: AURITY v0.3.0
**Última revisión**: 2025-12-08
