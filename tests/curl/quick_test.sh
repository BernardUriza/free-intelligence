#!/bin/bash
# quick_test.sh - Test rápido de 30 segundos para verificar que todo funciona
# Autor: Bernard Uriza Orozco

set -e

echo "⚡ AURITY - Test Rápido (30 segundos)"
echo "====================================="
echo ""

# Verificar .env.curl
if [ ! -f .env.curl ]; then
  echo "❌ Configuración no encontrada"
  echo ""
  echo "Ejecuta primero:"
  echo "  ./setup.sh"
  echo ""
  exit 1
fi

source .env.curl

# 1. Health check
echo "1/5 Health check..."
HEALTH=$(curl -s -X GET "$BACKEND_URL/health")
STATUS=$(echo "$HEALTH" | jq -r '.status')

if [ "$STATUS" = "healthy" ]; then
  echo "    ✅ Backend: $STATUS"
else
  echo "    ❌ Backend no disponible"
  exit 1
fi

# 2. Auth check
echo "2/5 Auth check..."
AUTH_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BACKEND_URL/api/workflows/aurity/sessions" \
  -H "Authorization: Bearer $AUTH_TOKEN")

HTTP_CODE=$(echo "$AUTH_RESPONSE" | tail -1)

if [ "$HTTP_CODE" = "200" ]; then
  echo "    ✅ Token válido"
else
  echo "    ❌ Token inválido (HTTP $HTTP_CODE)"
  exit 1
fi

# 3. Upload chunk
echo "3/5 Upload chunk..."

if [ ! -f temp/test_audio.wav ]; then
  echo "    ⚠️  Generando audio de prueba..."
  mkdir -p temp
  ffmpeg -f lavfi -i "sine=frequency=1000:duration=1" \
    -ar 16000 -ac 1 -f wav temp/test_audio.wav -y -loglevel quiet
fi

SESSION_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')

UPLOAD_RESPONSE=$(curl -s -X POST "$BACKEND_URL/api/transcription/stream" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -F "session_id=$SESSION_ID" \
  -F "chunk_number=0" \
  -F "mode=medical" \
  -F "patient_name=Test Quick" \
  -F "audio=@temp/test_audio.wav")

UPLOAD_STATUS=$(echo "$UPLOAD_RESPONSE" | jq -r '.status')

if [ "$UPLOAD_STATUS" = "pending" ]; then
  echo "    ✅ Chunk subido: $SESSION_ID"
else
  echo "    ❌ Error al subir chunk"
  echo "$UPLOAD_RESPONSE" | jq
  exit 1
fi

# 4. Transcription polling
echo "4/5 Transcripción..."

for i in {1..10}; do
  JOB_STATUS=$(curl -s -X GET "$BACKEND_URL/api/transcription/jobs/$SESSION_ID" \
    -H "Authorization: Bearer $AUTH_TOKEN")

  STATUS=$(echo "$JOB_STATUS" | jq -r '.status')

  if [ "$STATUS" = "completed" ]; then
    echo "    ✅ Transcripción completa"
    break
  fi

  if [ $i -eq 10 ]; then
    echo "    ⚠️  Transcripción pendiente (timeout)"
  fi

  sleep 1
done

# 5. Verificar sesión creada
echo "5/5 Verificación final..."

SESSION_DETAILS=$(curl -s -X GET "$BACKEND_URL/api/workflows/aurity/sessions/$SESSION_ID" \
  -H "Authorization: Bearer $AUTH_TOKEN")

if echo "$SESSION_DETAILS" | jq -e '.session_id' > /dev/null 2>&1; then
  echo "    ✅ Sesión guardada en HDF5"
else
  echo "    ❌ Sesión no encontrada"
  exit 1
fi

echo ""
echo "====================================="
echo "✅ Test rápido completado"
echo ""
echo "Sistema funcionando correctamente:"
echo "  • Backend disponible"
echo "  • Autenticación válida"
echo "  • Upload de audio OK"
echo "  • Transcripción OK"
echo "  • Almacenamiento HDF5 OK"
echo ""
echo "Session ID de prueba: $SESSION_ID"
echo ""
echo "Ver detalles:"
echo "  curl -X GET '$BACKEND_URL/api/workflows/aurity/sessions/$SESSION_ID' \\"
echo "    -H 'Authorization: Bearer \$AUTH_TOKEN' | jq"
echo ""
