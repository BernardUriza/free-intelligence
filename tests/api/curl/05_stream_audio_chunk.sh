#!/bin/bash

# 05_stream_audio_chunk.sh - Enviar chunk de audio (streaming)
# Uso: ./05_stream_audio_chunk.sh <session_id> <audio_chunk_file> <chunk_index>

set -e

# Cargar variables de entorno
if [ -f .env.test ]; then
  source .env.test
fi

# Configuración
API_BASE_URL=${API_BASE_URL:-"http://localhost:7001"}
AUTH_TOKEN=${AUTH_TOKEN:-""}

# Validar argumentos
if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]; then
  echo "❌ Error: Faltan argumentos"
  echo "Uso: ./05_stream_audio_chunk.sh <session_id> <audio_chunk_file> <chunk_index>"
  exit 1
fi

SESSION_ID="$1"
AUDIO_CHUNK="$2"
CHUNK_INDEX="$3"

# Verificar que el archivo existe
if [ ! -f "$AUDIO_CHUNK" ]; then
  echo "❌ Error: Archivo no encontrado: $AUDIO_CHUNK"
  exit 1
fi

# Validar token
if [ -z "$AUTH_TOKEN" ]; then
  echo "❌ Error: AUTH_TOKEN no configurado"
  exit 1
fi

# Ejecutar request
echo "📡 Streaming chunk #$CHUNK_INDEX..."

RESPONSE=$(curl -s -X POST \
  "$API_BASE_URL/api/workflows/aurity/sessions/$SESSION_ID/audio/stream" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -F "chunk=@$AUDIO_CHUNK" \
  -F "chunk_index=$CHUNK_INDEX")

# Verificar respuesta
if echo "$RESPONSE" | jq -e '.chunk_index' > /dev/null 2>&1; then
  echo "✅ Chunk #$CHUNK_INDEX procesado"
  echo "$RESPONSE" | jq -c '.'
  exit 0
else
  echo "❌ Error en chunk #$CHUNK_INDEX"
  echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
  exit 1
fi
