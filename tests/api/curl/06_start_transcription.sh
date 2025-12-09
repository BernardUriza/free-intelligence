#!/bin/bash

# 06_start_transcription.sh - Iniciar transcripción de audio
# Uso: ./06_start_transcription.sh <session_id> [--language=es] [--model=nova-2]

set -e

# Cargar variables de entorno
if [ -f .env.test ]; then
  source .env.test
fi

# Configuración
API_BASE_URL=${API_BASE_URL:-"http://localhost:7001"}
AUTH_TOKEN=${AUTH_TOKEN:-""}

# Validar argumentos
if [ -z "$1" ]; then
  echo "❌ Error: Falta session_id"
  echo "Uso: ./06_start_transcription.sh <session_id>"
  exit 1
fi

SESSION_ID="$1"

# Parámetros opcionales (valores por defecto)
LANGUAGE="es"
MODEL="nova-2"

# Parsear argumentos opcionales
for arg in "$@"; do
  case $arg in
    --language=*)
      LANGUAGE="${arg#*=}"
      ;;
    --model=*)
      MODEL="${arg#*=}"
      ;;
  esac
done

# Validar token
if [ -z "$AUTH_TOKEN" ]; then
  echo "❌ Error: AUTH_TOKEN no configurado"
  exit 1
fi

# Crear payload
PAYLOAD=$(cat <<EOF
{
  "session_id": "$SESSION_ID",
  "language": "$LANGUAGE",
  "model": "$MODEL",
  "diarize": true
}
EOF
)

# Ejecutar request
echo "🎯 Iniciando transcripción..."
echo "   Sesión: $SESSION_ID"
echo "   Idioma: $LANGUAGE"
echo "   Modelo: $MODEL"
echo ""

RESPONSE=$(curl -s -X POST \
  "$API_BASE_URL/api/workflows/aurity/sessions/$SESSION_ID/transcribe" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d "$PAYLOAD")

# Verificar respuesta
if echo "$RESPONSE" | jq -e '.task_id' > /dev/null 2>&1; then
  echo "✅ Transcripción iniciada"
  echo ""
  echo "$RESPONSE" | jq '.'
  exit 0
else
  echo "❌ Error iniciando transcripción"
  echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
  exit 1
fi
