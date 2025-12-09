#!/bin/bash

# 03_get_session.sh - Obtener detalles de sesión específica
# Uso: ./03_get_session.sh [session_id]

set -e

# Cargar variables de entorno
if [ -f .env.test ]; then
  source .env.test
fi

# Configuración
API_BASE_URL=${API_BASE_URL:-"http://localhost:7001"}
AUTH_TOKEN=${AUTH_TOKEN:-""}

# Obtener session_id (argumento o último creado)
if [ -n "$1" ]; then
  SESSION_ID="$1"
elif [ -f .last_session_id ]; then
  SESSION_ID=$(cat .last_session_id)
else
  echo "❌ Error: Proporciona session_id como argumento"
  echo "Uso: ./03_get_session.sh <session_id>"
  exit 1
fi

# Validar token
if [ -z "$AUTH_TOKEN" ]; then
  echo "❌ Error: AUTH_TOKEN no configurado"
  exit 1
fi

# Ejecutar request
echo "🔍 Obteniendo sesión: $SESSION_ID"
echo ""

RESPONSE=$(curl -s -X GET \
  "$API_BASE_URL/api/workflows/aurity/sessions/$SESSION_ID" \
  -H "Authorization: Bearer $AUTH_TOKEN")

# Verificar respuesta
if echo "$RESPONSE" | jq -e '.session_id' > /dev/null 2>&1; then
  echo "✅ Sesión encontrada"
  echo ""
  echo "$RESPONSE" | jq '.'
  exit 0
else
  echo "❌ Error obteniendo sesión"
  echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
  exit 1
fi
