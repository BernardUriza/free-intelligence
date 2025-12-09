#!/bin/bash
# test_medical_session.sh - Test completo de sesión médica
# Autor: Bernard Uriza Orozco

set -e

# Cargar configuración
if [ ! -f .env.curl ]; then
  echo "❌ Archivo .env.curl no encontrado"
  echo "Ejecuta primero: ./setup.sh"
  exit 1
fi

source .env.curl

echo "🏥 AURITY - Test de Sesión Médica"
echo "=================================="
echo ""

# Generar session ID
SESSION_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')
echo "📋 Session ID: $SESSION_ID"
echo ""

# Verificar audio de prueba
if [ ! -f temp/test_audio.wav ]; then
  echo "⚠️  Audio de prueba no encontrado, generando..."
  ffmpeg -f lavfi -i "sine=frequency=1000:duration=2" \
    -ar 16000 -ac 1 -f wav temp/test_audio.wav -y -loglevel quiet
fi

# 1. Subir chunk 0 (iniciar sesión)
echo "1️⃣  Subiendo chunk 0 (iniciando sesión)..."
RESPONSE=$(curl -s -X POST "$BACKEND_URL/api/transcription/stream" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -F "session_id=$SESSION_ID" \
  -F "chunk_number=0" \
  -F "mode=medical" \
  -F "patient_name=Juan Pérez Test" \
  -F "patient_age=45" \
  -F "patient_id=TEST_PAC_001" \
  -F "chief_complaint=Cefalea intensa desde hace 3 días" \
  -F "timestamp_start=0.0" \
  -F "timestamp_end=2.0" \
  -F "audio=@temp/test_audio.wav")

echo "$RESPONSE" | jq '{session_id, chunk_number, status}'

if [ $(echo "$RESPONSE" | jq -r '.status') != "pending" ]; then
  echo "❌ Error al subir chunk 0"
  echo "$RESPONSE" | jq
  exit 1
fi

echo "✅ Chunk 0 subido"
echo ""

# 2. Subir chunks adicionales
echo "2️⃣  Subiendo chunks adicionales..."

for i in 1 2 3; do
  START=$((i * 2))
  END=$((START + 2))

  echo "   Chunk $i (${START}s - ${END}s)..."

  curl -s -X POST "$BACKEND_URL/api/transcription/stream" \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    -F "session_id=$SESSION_ID" \
    -F "chunk_number=$i" \
    -F "mode=medical" \
    -F "timestamp_start=$START.0" \
    -F "timestamp_end=$END.0" \
    -F "audio=@temp/test_audio.wav" > /dev/null

  echo "   ✅ Chunk $i subido"
done

echo ""

# 3. Polling de transcripción
echo "3️⃣  Esperando transcripción..."

MAX_ATTEMPTS=30
ATTEMPT=1

while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
  JOB_STATUS=$(curl -s -X GET "$BACKEND_URL/api/transcription/jobs/$SESSION_ID" \
    -H "Authorization: Bearer $AUTH_TOKEN")

  STATUS=$(echo "$JOB_STATUS" | jq -r '.status')
  PROCESSED=$(echo "$JOB_STATUS" | jq -r '.processed_chunks')
  TOTAL=$(echo "$JOB_STATUS" | jq -r '.total_chunks')
  PROGRESS=$(echo "$JOB_STATUS" | jq -r '.progress_percent')

  echo "   Intento $ATTEMPT/$MAX_ATTEMPTS: $STATUS ($PROCESSED/$TOTAL chunks, $PROGRESS%)"

  if [ "$STATUS" = "completed" ]; then
    echo "✅ Transcripción completa"
    break
  fi

  if [ "$STATUS" = "failed" ]; then
    echo "❌ Transcripción fallida"
    echo "$JOB_STATUS" | jq
    exit 1
  fi

  ATTEMPT=$((ATTEMPT + 1))
  sleep 1
done

if [ "$STATUS" != "completed" ]; then
  echo "❌ Timeout esperando transcripción"
  exit 1
fi

echo ""

# 4. Ver chunks transcritos
echo "4️⃣  Chunks transcritos:"
curl -s -X GET "$BACKEND_URL/api/transcription/sessions/$SESSION_ID/chunks" \
  -H "Authorization: Bearer $AUTH_TOKEN" | jq '.chunks[] | {chunk_number, transcript, confidence}'

echo ""

# 5. Finalizar sesión
echo "5️⃣  Finalizando sesión (guardando audio completo)..."

# Crear audio completo (concatenar chunks)
cat temp/test_audio.wav temp/test_audio.wav temp/test_audio.wav temp/test_audio.wav > temp/full_audio.wav

# Crear JSON de webspeech
cat > temp/webspeech.json << 'EOF'
[
  {"timestamp": 0.0, "text": "Hola doctor, me duele mucho la cabeza", "confidence": 0.95},
  {"timestamp": 2.0, "text": "desde hace tres días", "confidence": 0.92},
  {"timestamp": 4.0, "text": "y también tengo náuseas", "confidence": 0.88},
  {"timestamp": 6.0, "text": "por las mañanas", "confidence": 0.90}
]
EOF

END_RESPONSE=$(curl -s -X POST "$BACKEND_URL/api/transcription/end-session" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -F "session_id=$SESSION_ID" \
  -F "full_audio=@temp/full_audio.wav" \
  -F "webspeech_final=$(cat temp/webspeech.json | jq -c .)")

echo "$END_RESPONSE" | jq

echo "✅ Sesión finalizada"
echo ""

# 6. Ejecutar diarización
echo "6️⃣  Ejecutando diarización..."

DIAR_RESPONSE=$(curl -s -X POST "$BACKEND_URL/api/workflows/aurity/sessions/$SESSION_ID/diarization" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json")

echo "$DIAR_RESPONSE" | jq '{job_id, status}'

echo "⏳ Esperando diarización (puede tomar 10-20 segundos)..."
sleep 5
echo "✅ Diarización despachada"
echo ""

# 7. Generar SOAP
echo "7️⃣  Generando nota SOAP..."

SOAP_RESPONSE=$(curl -s -X POST "$BACKEND_URL/api/workflows/aurity/sessions/$SESSION_ID/soap" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json")

echo "$SOAP_RESPONSE" | jq '{job_id, status}'

echo "⏳ Esperando SOAP (puede tomar 20-40 segundos)..."

MAX_SOAP_ATTEMPTS=60
SOAP_ATTEMPT=1

while [ $SOAP_ATTEMPT -le $MAX_SOAP_ATTEMPTS ]; do
  SESSION_DETAILS=$(curl -s -X GET "$BACKEND_URL/api/workflows/aurity/sessions/$SESSION_ID" \
    -H "Authorization: Bearer $AUTH_TOKEN")

  SOAP_STATUS=$(echo "$SESSION_DETAILS" | jq -r '.soap_status // "pending"')

  echo "   Intento $SOAP_ATTEMPT/$MAX_SOAP_ATTEMPTS: SOAP $SOAP_STATUS"

  if [ "$SOAP_STATUS" = "completed" ]; then
    echo "✅ SOAP generado"
    echo ""
    echo "📋 Nota SOAP:"
    echo "$SESSION_DETAILS" | jq '.soap_note'
    break
  fi

  if [ "$SOAP_STATUS" = "failed" ]; then
    echo "❌ SOAP fallido"
    break
  fi

  SOAP_ATTEMPT=$((SOAP_ATTEMPT + 1))
  sleep 1
done

echo ""

# 8. Ver timeline de sesiones
echo "8️⃣  Sesión en timeline:"
curl -s -X GET "$BACKEND_URL/api/workflows/aurity/sessions" \
  -H "Authorization: Bearer $AUTH_TOKEN" | \
  jq --arg sid "$SESSION_ID" '.[] | select(.session_id == $sid) | {session_id, patient_name, created_at, status}'

echo ""

# 9. Ver audit log
echo "9️⃣  Audit log de sesión:"
curl -s -X GET "$BACKEND_URL/api/workflows/aurity/sessions/$SESSION_ID/audit" \
  -H "Authorization: Bearer $AUTH_TOKEN" | jq '.events[] | {timestamp, event_type, details}'

echo ""
echo "=================================="
echo "✅ Test completado exitosamente"
echo ""
echo "📋 Session ID: $SESSION_ID"
echo ""
echo "Ver detalles completos:"
echo "  curl -X GET '$BACKEND_URL/api/workflows/aurity/sessions/$SESSION_ID' \\"
echo "    -H 'Authorization: Bearer \$AUTH_TOKEN' | jq"
echo ""
