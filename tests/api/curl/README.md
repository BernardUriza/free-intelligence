# AURITY API Testing Suite - cURL Scripts

**Last Updated**: 2025-12-08
**Environment**: Production-ready test suite
**Base URL**: `http://localhost:7001` (development) | `https://app.aurity.io` (production)

---

## 📋 **Tabla de Contenidos**

1. [Quick Start](#quick-start)
2. [Configuración](#configuración)
3. [Scripts Disponibles](#scripts-disponibles)
4. [Flujo Completo de Pruebas](#flujo-completo-de-pruebas)
5. [Troubleshooting](#troubleshooting)

---

## 🚀 **Quick Start**

```bash
# 1. Ir al directorio de tests
cd tests/api/curl

# 2. Configurar variables de entorno
export API_BASE_URL="http://localhost:7001"
export AUTH_TOKEN="your_auth0_jwt_token_here"

# 3. Ejecutar suite completa
./run_all_tests.sh

# 4. O ejecutar test específico
./01_create_session.sh
```

---

## ⚙️ **Configuración**

### Variables de Entorno

Crear archivo `.env.test`:

```bash
# Backend URL
API_BASE_URL=http://localhost:7001

# Auth0 JWT Token
AUTH_TOKEN=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IjEyMyJ9...

# Session IDs para tests
TEST_SESSION_ID=test-session-$(date +%s)
TEST_USER_ID=test-user-123

# Paths de archivos de prueba
TEST_AUDIO_FILE=./fixtures/audio/sample_30s.wav
TEST_AUDIO_CHUNK=./fixtures/audio/chunk_5s.wav
```

Cargar variables:
```bash
source .env.test
```

### Obtener Token de Auth0

**Opción 1: Desde la UI de AURITY**
```bash
# 1. Login en https://app.aurity.io
# 2. Abrir DevTools (F12) → Console
# 3. Ejecutar:
localStorage.getItem('auth0_token')

# 4. Copiar y exportar:
export AUTH_TOKEN="eyJhbGciOiJS..."
```

**Opción 2: Auth0 CLI**
```bash
# Obtener token directo de Auth0
curl --request POST \
  --url https://aurity.us.auth0.com/oauth/token \
  --header 'content-type: application/json' \
  --data '{
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET",
    "audience": "https://api.aurity.io",
    "grant_type": "client_credentials"
  }' | jq -r '.access_token'
```

---

## 📜 **Scripts Disponibles**

### 1. **Gestión de Sesiones**

#### `01_create_session.sh` - Crear Sesión Nueva
```bash
./01_create_session.sh

# Output esperado:
{
  "session_id": "session-1733683200",
  "status": "created",
  "created_at": "2025-12-08T10:30:00Z"
}
```

#### `02_list_sessions.sh` - Listar Sesiones
```bash
./02_list_sessions.sh

# Filtrar por usuario
./02_list_sessions.sh user_123

# Output:
{
  "sessions": [
    {
      "session_id": "session-001",
      "status": "active",
      "created_at": "2025-12-08T10:00:00Z"
    }
  ],
  "total": 1
}
```

#### `03_get_session.sh` - Obtener Sesión Específica
```bash
./03_get_session.sh session-123

# Output:
{
  "session_id": "session-123",
  "status": "active",
  "tasks": {
    "TRANSCRIPTION": {"status": "completed", "chunks": 12},
    "DIARIZATION": {"status": "in_progress", "progress": 0.67},
    "SOAP_GENERATION": {"status": "pending"}
  },
  "metadata": {
    "patient_id": "patient-456",
    "provider_id": "provider-789"
  }
}
```

---

### 2. **Grabación de Audio**

#### `04_upload_audio.sh` - Subir Audio Completo
```bash
# Subir archivo de audio completo
./04_upload_audio.sh session-123 ./fixtures/audio/consultation_30min.wav

# Output:
{
  "session_id": "session-123",
  "audio_uploaded": true,
  "duration_seconds": 1800,
  "file_size_bytes": 10485760,
  "format": "wav",
  "sample_rate": 16000
}
```

#### `05_stream_audio_chunk.sh` - Streaming de Audio (Chunks)
```bash
# Enviar chunk de audio (5 segundos)
./05_stream_audio_chunk.sh session-123 ./fixtures/audio/chunk_001.wav 0

# Enviar múltiples chunks
for i in {0..10}; do
  ./05_stream_audio_chunk.sh session-123 "./fixtures/audio/chunk_$(printf %03d $i).wav" $i
  sleep 1
done

# Output por chunk:
{
  "session_id": "session-123",
  "chunk_index": 0,
  "duration_seconds": 5.0,
  "bytes_received": 80000,
  "transcription_started": true
}
```

---

### 3. **Transcripción**

#### `06_start_transcription.sh` - Iniciar Transcripción
```bash
./06_start_transcription.sh session-123

# Con opciones
./06_start_transcription.sh session-123 --language=es --model=nova-2

# Output:
{
  "session_id": "session-123",
  "task_id": "TRANSCRIPTION",
  "status": "started",
  "worker_id": "worker-001"
}
```

#### `07_get_transcription.sh` - Obtener Transcripción
```bash
./07_get_transcription.sh session-123

# Output:
{
  "session_id": "session-123",
  "transcript": {
    "full_text": "Doctor: Buenos días, ¿cómo se encuentra?\nPaciente: Bien, gracias...",
    "chunks": [
      {
        "chunk_index": 0,
        "text": "Doctor: Buenos días, ¿cómo se encuentra?",
        "speaker": "doctor",
        "start_time": 0.0,
        "end_time": 3.5,
        "confidence": 0.95
      }
    ]
  },
  "metadata": {
    "total_chunks": 12,
    "duration_seconds": 1800,
    "language": "es"
  }
}
```

---

### 4. **Diarización**

#### `08_start_diarization.sh` - Identificar Speakers
```bash
./08_start_diarization.sh session-123

# Output:
{
  "session_id": "session-123",
  "task_id": "DIARIZATION",
  "status": "started",
  "speakers_detected": 2
}
```

#### `09_get_diarization.sh` - Obtener Resultados de Diarización
```bash
./09_get_diarization.sh session-123

# Output:
{
  "session_id": "session-123",
  "speakers": [
    {
      "speaker_id": "SPEAKER_00",
      "role": "doctor",
      "segments": [
        {"start": 0.0, "end": 3.5, "text": "Buenos días, ¿cómo se encuentra?"}
      ],
      "total_speaking_time": 900
    },
    {
      "speaker_id": "SPEAKER_01",
      "role": "patient",
      "segments": [
        {"start": 3.5, "end": 8.2, "text": "Bien, gracias. Vengo por..."}
      ],
      "total_speaking_time": 850
    }
  ]
}
```

---

### 5. **Generación de SOAP**

#### `10_generate_soap.sh` - Generar Nota SOAP
```bash
./10_generate_soap.sh session-123

# Output:
{
  "session_id": "session-123",
  "soap_note": {
    "subjective": "Paciente masculino de 45 años refiere dolor abdominal...",
    "objective": "TA: 120/80 mmHg, FC: 72 lpm, Temp: 36.5°C...",
    "assessment": "Gastritis aguda, posible úlcera péptica...",
    "plan": "1. Omeprazol 20mg c/12h por 14 días\n2. Ranitidina PRN..."
  },
  "generated_at": "2025-12-08T11:00:00Z",
  "version": 1
}
```

#### `11_get_soap_versions.sh` - Historial de Versiones SOAP
```bash
./11_get_soap_versions.sh session-123

# Output:
{
  "session_id": "session-123",
  "versions": [
    {
      "version": 1,
      "created_at": "2025-12-08T11:00:00Z",
      "soap_note": {...}
    },
    {
      "version": 2,
      "created_at": "2025-12-08T11:15:00Z",
      "soap_note": {...},
      "changes": "Actualización de plan terapéutico"
    }
  ],
  "latest_version": 2
}
```

---

### 6. **Análisis de Emoción**

#### `12_analyze_emotion.sh` - Análisis de Sentimiento
```bash
./12_analyze_emotion.sh session-123

# Output:
{
  "session_id": "session-123",
  "emotion_analysis": {
    "overall_sentiment": "neutral",
    "patient_emotions": {
      "anxiety": 0.45,
      "pain": 0.32,
      "satisfaction": 0.15
    },
    "doctor_emotions": {
      "empathy": 0.78,
      "professionalism": 0.92
    },
    "critical_moments": [
      {
        "timestamp": 120.5,
        "emotion": "high_anxiety",
        "text": "Me preocupa mucho este dolor..."
      }
    ]
  }
}
```

---

### 7. **Monitoreo y Estado**

#### `13_session_status.sh` - Estado Completo de Sesión
```bash
./13_session_status.sh session-123

# Output:
{
  "session_id": "session-123",
  "status": "processing",
  "progress": 0.75,
  "tasks": {
    "TRANSCRIPTION": {"status": "completed", "progress": 1.0},
    "DIARIZATION": {"status": "completed", "progress": 1.0},
    "SOAP_GENERATION": {"status": "in_progress", "progress": 0.5},
    "EMOTION_ANALYSIS": {"status": "pending", "progress": 0.0}
  },
  "duration_seconds": 1800,
  "created_at": "2025-12-08T10:00:00Z",
  "updated_at": "2025-12-08T10:35:00Z"
}
```

#### `14_health_check.sh` - Verificar Salud del Sistema
```bash
./14_health_check.sh

# Output:
{
  "status": "healthy",
  "services": {
    "api": "up",
    "workers": "up",
    "storage": "up",
    "database": "up"
  },
  "version": "0.3.0",
  "uptime_seconds": 86400
}
```

---

### 8. **Verificación de Integridad**

#### `15_verify_h5_integrity.sh` - Verificar Archivo HDF5
```bash
./15_verify_h5_integrity.sh session-123

# Output:
{
  "session_id": "session-123",
  "file_path": "storage/sessions/session-123.h5",
  "integrity_check": "passed",
  "checksum": "sha256:a3f2b1c4d5e6...",
  "file_size_bytes": 10485760,
  "tasks_count": 4,
  "versions_count": 12,
  "last_modified": "2025-12-08T11:00:00Z"
}
```

---

### 9. **Suite Completa**

#### `run_all_tests.sh` - Ejecutar Todos los Tests
```bash
./run_all_tests.sh

# Output:
========================================
AURITY API Test Suite
========================================
[1/15] Creating session... ✓
[2/15] Listing sessions... ✓
[3/15] Getting session details... ✓
[4/15] Uploading audio... ✓
[5/15] Streaming audio chunks... ✓
[6/15] Starting transcription... ✓
[7/15] Getting transcription... ✓
[8/15] Starting diarization... ✓
[9/15] Getting diarization... ✓
[10/15] Generating SOAP... ✓
[11/15] Getting SOAP versions... ✓
[12/15] Analyzing emotion... ✓
[13/15] Checking session status... ✓
[14/15] Health check... ✓
[15/15] Verifying H5 integrity... ✓
========================================
Results: 15/15 passed (100%)
Duration: 45.3s
========================================
```

---

## 🔄 **Flujo Completo de Pruebas**

### Escenario 1: Consulta Médica Completa

```bash
#!/bin/bash
# test_full_consultation.sh

set -e

echo "=== Flujo: Consulta Médica Completa ==="

# 1. Crear sesión
SESSION_ID=$(./01_create_session.sh | jq -r '.session_id')
echo "✓ Sesión creada: $SESSION_ID"

# 2. Subir audio completo
./04_upload_audio.sh $SESSION_ID ./fixtures/audio/consultation_30min.wav
echo "✓ Audio subido"

# 3. Iniciar transcripción
./06_start_transcription.sh $SESSION_ID
echo "✓ Transcripción iniciada"

# 4. Esperar transcripción (polling)
while true; do
  STATUS=$(./13_session_status.sh $SESSION_ID | jq -r '.tasks.TRANSCRIPTION.status')
  if [ "$STATUS" == "completed" ]; then
    break
  fi
  echo "  Transcribiendo... ($STATUS)"
  sleep 5
done
echo "✓ Transcripción completada"

# 5. Iniciar diarización
./08_start_diarization.sh $SESSION_ID
echo "✓ Diarización iniciada"

# 6. Esperar diarización
while true; do
  STATUS=$(./13_session_status.sh $SESSION_ID | jq -r '.tasks.DIARIZATION.status')
  if [ "$STATUS" == "completed" ]; then
    break
  fi
  echo "  Diarizando... ($STATUS)"
  sleep 5
done
echo "✓ Diarización completada"

# 7. Generar SOAP
./10_generate_soap.sh $SESSION_ID
echo "✓ Nota SOAP generada"

# 8. Analizar emociones
./12_analyze_emotion.sh $SESSION_ID
echo "✓ Análisis emocional completado"

# 9. Verificar integridad
./15_verify_h5_integrity.sh $SESSION_ID
echo "✓ Integridad verificada"

# 10. Obtener resultados finales
echo ""
echo "=== Resultados ==="
./03_get_session.sh $SESSION_ID | jq '.'

echo ""
echo "✅ Consulta procesada exitosamente: $SESSION_ID"
```

### Escenario 2: Streaming en Tiempo Real

```bash
#!/bin/bash
# test_realtime_streaming.sh

set -e

echo "=== Flujo: Streaming en Tiempo Real ==="

# 1. Crear sesión
SESSION_ID=$(./01_create_session.sh | jq -r '.session_id')
echo "✓ Sesión creada: $SESSION_ID"

# 2. Simular streaming de audio
echo "Streaming audio chunks..."
for i in {0..59}; do
  ./05_stream_audio_chunk.sh $SESSION_ID "./fixtures/audio/chunk_$(printf %03d $i).wav" $i &

  # Enviar 2 chunks por segundo (simulando real-time)
  if [ $((i % 2)) -eq 0 ]; then
    sleep 1
  fi
done

wait
echo "✓ Streaming completado (60 chunks / 30 minutos)"

# 3. Verificar estado final
./13_session_status.sh $SESSION_ID | jq '.'
```

---

## 🛠️ **Troubleshooting**

### Error: "Unauthorized (401)"

```bash
# Verificar que el token sea válido
echo $AUTH_TOKEN

# Decodificar token (verificar expiración)
echo $AUTH_TOKEN | cut -d '.' -f 2 | base64 -d | jq '.'

# Obtener nuevo token
# (Ver sección "Obtener Token de Auth0")
```

### Error: "Session not found (404)"

```bash
# Listar sesiones existentes
./02_list_sessions.sh

# Verificar que el session_id sea correcto
./03_get_session.sh $SESSION_ID
```

### Error: "File too large (413)"

```bash
# Verificar tamaño del archivo
ls -lh ./fixtures/audio/consultation.wav

# Si > 50MB, dividir en chunks:
ffmpeg -i consultation.wav -f segment -segment_time 30 chunk_%03d.wav
```

### Error: "Connection refused"

```bash
# Verificar que el backend esté corriendo
curl http://localhost:7001/health

# Si no responde, iniciar backend:
cd /path/to/free-intelligence
make dev-backend
```

### Logs Detallados

```bash
# Activar verbose mode en curl
export CURL_VERBOSE=1

# Ver headers completos
./01_create_session.sh -v

# Ver logs del backend
tail -f data/logs/backend.log
```

---

## 📊 **Performance Benchmarks**

### Tiempos Esperados

| Operación | Tiempo Promedio | Notas |
|-----------|----------------|-------|
| Crear sesión | 50-100ms | Operación ligera |
| Upload audio (30 min) | 2-5s | Depende de red |
| Transcripción | 60-120s | ~2-4x realtime |
| Diarización | 30-60s | Post-transcripción |
| Generar SOAP | 10-20s | LLM inference |
| Análisis emocional | 15-30s | NLP processing |

### Stress Test

```bash
# Crear 100 sesiones simultáneas
for i in {1..100}; do
  ./01_create_session.sh &
done
wait

echo "✓ 100 sesiones creadas"
```

---

## 📚 **Referencias**

- **API Architecture**: `backend/docs/API_ARCHITECTURE.md`
- **Storage Architecture**: `docs/STORAGE_ARCHITECTURE.md`
- **Full Stack Navigation**: `docs/FULL_STACK_NAVIGATION.md`
- **Backend README**: `backend/README.md`

---

## ✅ **Checklist de Tests**

Antes de un release:

- [ ] `run_all_tests.sh` pasa con 100%
- [ ] Test de streaming en tiempo real funciona
- [ ] Health check retorna "healthy"
- [ ] Integridad de HDF5 verificada
- [ ] SOAP generation produce notas válidas
- [ ] Diarización identifica correctamente speakers
- [ ] Análisis emocional detecta sentimientos clave
- [ ] Tokens de Auth0 válidos y no expirados
- [ ] Logs sin errores críticos

---

**Última actualización**: 2025-12-08
**Mantenedor**: Bernard Uriza Orozco
**Versión**: 0.3.0
