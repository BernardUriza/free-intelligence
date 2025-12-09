# AURITY - Ejemplos de Uso Común con cURL

Colección de comandos cURL listos para copiar-pegar para casos de uso comunes.

**Requisito previo:** Ejecutar `source .env.curl` en tu terminal

---

## 📋 Sesiones Médicas

### Crear sesión médica simple

```bash
# 1. Generar session ID
SESSION_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')

# 2. Subir primer chunk
curl -X POST "$BACKEND_URL/api/transcription/stream" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -F "session_id=$SESSION_ID" \
  -F "chunk_number=0" \
  -F "mode=medical" \
  -F "patient_name=María González" \
  -F "patient_age=52" \
  -F "audio=@temp/test_audio.wav"

# 3. Polling de status
curl -X GET "$BACKEND_URL/api/transcription/jobs/$SESSION_ID" \
  -H "Authorization: Bearer $AUTH_TOKEN" | jq '.status'

# 4. Ver transcript
curl -X GET "$BACKEND_URL/api/transcription/sessions/$SESSION_ID/chunks" \
  -H "Authorization: Bearer $AUTH_TOKEN" | jq '.chunks[].transcript'
```

### Listar mis sesiones de hoy

```bash
TODAY=$(date +%Y-%m-%d)

curl -X GET "$BACKEND_URL/api/workflows/aurity/sessions?start_date=$TODAY" \
  -H "Authorization: Bearer $AUTH_TOKEN" | \
  jq '.[] | {session_id, patient_name, created_at, status}'
```

### Ver detalles completos de sesión

```bash
curl -X GET "$BACKEND_URL/api/workflows/aurity/sessions/$SESSION_ID" \
  -H "Authorization: Bearer $AUTH_TOKEN" | jq '{
  session_id,
  patient_name,
  created_at,
  status,
  transcription_status: .tasks.TRANSCRIPTION.status,
  diarization_status: .tasks.DIARIZATION.status,
  soap_status: .tasks.SOAP_GENERATION.status,
  duration: .metadata.audio_duration_seconds,
  chunks: .metadata.chunks_count
}'
```

---

## 🎤 Transcripción

### Ver transcripción con timestamps

```bash
curl -X GET "$BACKEND_URL/api/transcription/sessions/$SESSION_ID/chunks" \
  -H "Authorization: Bearer $AUTH_TOKEN" | \
  jq '.chunks[] | {
    chunk: .chunk_number,
    start: .metadata.timestamp_start,
    end: .metadata.timestamp_end,
    text: .transcript
  }'
```

---

## 📝 One-liners Útiles

```bash
# Contar sesiones de hoy
curl -s -X GET "$BACKEND_URL/api/workflows/aurity/sessions?start_date=$(date +%Y-%m-%d)" \
  -H "Authorization: Bearer $AUTH_TOKEN" | jq '. | length'

# Última sesión creada
curl -s -X GET "$BACKEND_URL/api/workflows/aurity/sessions" \
  -H "Authorization: Bearer $AUTH_TOKEN" | jq '.[0]'
```
