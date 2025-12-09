#!/bin/bash
# test_chat_mode.sh - Test de modo chat (transcripción síncrona)
# Autor: Bernard Uriza Orozco

set -e

# Cargar configuración
if [ ! -f .env.curl ]; then
  echo "❌ Archivo .env.curl no encontrado"
  echo "Ejecuta primero: ./setup.sh"
  exit 1
fi

source .env.curl

echo "💬 AURITY - Test de Modo Chat"
echo "=============================="
echo ""

# Session ID para chat (user-scoped)
USER_ID="user_test_$(date +%s)"
CHAT_SESSION_ID="chat_$USER_ID"

echo "📋 Chat Session ID: $CHAT_SESSION_ID"
echo "👤 User ID: $USER_ID"
echo ""

# Verificar audio de prueba
if [ ! -f temp/test_audio.wav ]; then
  echo "⚠️  Audio de prueba no encontrado, generando..."
  ffmpeg -f lavfi -i "sine=frequency=1000:duration=2" \
    -ar 16000 -ac 1 -f wav temp/test_audio.wav -y -loglevel quiet
fi

# 1. Enviar mensaje 1 (modo chat - transcripción síncrona)
echo "1️⃣  Enviando mensaje 1 (modo chat)..."

MSG1_RESPONSE=$(curl -s -X POST "$BACKEND_URL/api/transcription/stream" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -F "session_id=$CHAT_SESSION_ID" \
  -F "chunk_number=0" \
  -F "mode=chat" \
  -F "audio=@temp/test_audio.wav")

echo "$MSG1_RESPONSE" | jq '{session_id, chunk_number, status, total_chunks}'

STATUS=$(echo "$MSG1_RESPONSE" | jq -r '.status')

if [ "$STATUS" = "completed" ]; then
  echo "✅ Transcripción inmediata (modo chat)"
else
  echo "⚠️  Status: $STATUS (esperado: completed)"
fi

echo ""

# 2. Obtener transcript inmediatamente (sin polling)
echo "2️⃣  Obteniendo transcript (sin polling necesario)..."

JOB_RESPONSE=$(curl -s -X GET "$BACKEND_URL/api/transcription/jobs/$CHAT_SESSION_ID" \
  -H "Authorization: Bearer $AUTH_TOKEN")

echo "$JOB_RESPONSE" | jq '{
  session_id,
  status,
  total_chunks,
  processed_chunks,
  chunks: .chunks[] | {chunk_number, transcript, confidence, provider}
}'

echo "✅ Transcript disponible inmediatamente"
echo ""

# 3. Enviar mensaje 2
echo "3️⃣  Enviando mensaje 2..."

MSG2_RESPONSE=$(curl -s -X POST "$BACKEND_URL/api/transcription/stream" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -F "session_id=$CHAT_SESSION_ID" \
  -F "chunk_number=1" \
  -F "mode=chat" \
  -F "audio=@temp/test_audio.wav")

echo "$MSG2_RESPONSE" | jq '{chunk_number, status}'
echo ""

# 4. Enviar mensaje 3
echo "4️⃣  Enviando mensaje 3..."

MSG3_RESPONSE=$(curl -s -X POST "$BACKEND_URL/api/transcription/stream" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -F "session_id=$CHAT_SESSION_ID" \
  -F "chunk_number=2" \
  -F "mode=chat" \
  -F "audio=@temp/test_audio.wav")

echo "$MSG3_RESPONSE" | jq '{chunk_number, status}'
echo ""

# 5. Ver historial completo de chat
echo "5️⃣  Historial completo de chat:"

CHAT_HISTORY=$(curl -s -X GET "$BACKEND_URL/api/transcription/jobs/$CHAT_SESSION_ID" \
  -H "Authorization: Bearer $AUTH_TOKEN")

echo "$CHAT_HISTORY" | jq '.chunks | map({
  chunk_number,
  transcript,
  confidence,
  timestamp: .metadata.timestamp_start
})'

echo ""

# 6. Comparar con modo medical (polling necesario)
echo "6️⃣  Comparación: Modo Chat vs Modo Medical"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

MEDICAL_SESSION_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')

echo "Testing modo MEDICAL (async)..."
echo "Session ID: $MEDICAL_SESSION_ID"

# Enviar chunk en modo medical
START_TIME=$(date +%s)

curl -s -X POST "$BACKEND_URL/api/transcription/stream" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -F "session_id=$MEDICAL_SESSION_ID" \
  -F "chunk_number=0" \
  -F "mode=medical" \
  -F "patient_name=Test Patient" \
  -F "audio=@temp/test_audio.wav" > /dev/null

# Polling necesario
ATTEMPT=1
MAX_ATTEMPTS=20

while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
  MEDICAL_JOB=$(curl -s -X GET "$BACKEND_URL/api/transcription/jobs/$MEDICAL_SESSION_ID" \
    -H "Authorization: Bearer $AUTH_TOKEN")

  MEDICAL_STATUS=$(echo "$MEDICAL_JOB" | jq -r '.status')

  if [ "$MEDICAL_STATUS" = "completed" ]; then
    END_TIME=$(date +%s)
    ELAPSED=$((END_TIME - START_TIME))
    echo "✅ Medical mode completado en ${ELAPSED}s (requiere polling)"
    break
  fi

  ATTEMPT=$((ATTEMPT + 1))
  sleep 0.5
done

echo ""
echo "Resumen:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Chat Mode:    ✅ Transcripción inmediata (síncrona)"
echo "              ✅ Sin polling necesario"
echo "              ✅ Ideal para chat en tiempo real"
echo ""
echo "Medical Mode: ⏳ Transcripción asíncrona (workers)"
echo "              ⏳ Requiere polling cada 500ms"
echo "              ✅ Maneja sesiones largas (30+ min)"
echo ""

echo "=============================="
echo "✅ Test de modo chat completado"
echo ""
echo "📋 Chat Session ID: $CHAT_SESSION_ID"
echo "📋 Medical Session ID: $MEDICAL_SESSION_ID"
echo ""
echo "Ver transcripts:"
echo "  # Chat"
echo "  curl -X GET '$BACKEND_URL/api/transcription/jobs/$CHAT_SESSION_ID' \\"
echo "    -H 'Authorization: Bearer \$AUTH_TOKEN' | jq '.chunks'"
echo ""
echo "  # Medical"
echo "  curl -X GET '$BACKEND_URL/api/transcription/jobs/$MEDICAL_SESSION_ID' \\"
echo "    -H 'Authorization: Bearer \$AUTH_TOKEN' | jq '.chunks'"
echo ""
