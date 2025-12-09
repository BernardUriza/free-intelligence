#!/bin/bash

# 04_upload_audio.sh - Subir archivo de audio completo
# Uso: ./04_upload_audio.sh <session_id> <audio_file>

set -e

# Cargar variables de entorno
if [ -f .env.test ]; then
  source .env.test
fi

# Configuración
API_BASE_URL=${API_BASE_URL:-"http://localhost:7001"}
AUTH_TOKEN=${AUTH_TOKEN:-""}

# Validar argumentos
if [ -z "$1" ] || [ -z "$2" ]; then
  echo "❌ Error: Faltan argumentos"
  echo "Uso: ./04_upload_audio.sh <session_id> <audio_file>"
  exit 1
fi

SESSION_ID="$1"
AUDIO_FILE="$2"

# Verificar que el archivo existe
if [ ! -f "$AUDIO_FILE" ]; then
  echo "❌ Error: Archivo no encontrado: $AUDIO_FILE"
  exit 1
fi

# Validar token
if [ -z "$AUTH_TOKEN" ]; then
  echo "❌ Error: AUTH_TOKEN no configurado"
  exit 1
fi

# Obtener metadata del archivo
FILE_SIZE=$(ls -lh "$AUDIO_FILE" | awk '{print $5}')
FILE_TYPE=$(file -b --mime-type "$AUDIO_FILE")

# Ejecutar request
echo "🎤 Subiendo audio..."
echo "   Sesión: $SESSION_ID"
echo "   Archivo: $AUDIO_FILE"
echo "   Tamaño: $FILE_SIZE"
echo "   Tipo: $FILE_TYPE"
echo ""

RESPONSE=$(curl -s -X POST \
  "$API_BASE_URL/api/workflows/aurity/sessions/$SESSION_ID/audio" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -F "file=@$AUDIO_FILE")

# Verificar respuesta
if echo "$RESPONSE" | jq -e '.audio_uploaded' > /dev/null 2>&1; then
  echo "✅ Audio subido exitosamente"
  echo ""
  echo "$RESPONSE" | jq '.'
  exit 0
else
  echo "❌ Error subiendo audio"
  echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
  exit 1
fi
