#!/bin/bash

# 02_list_sessions.sh - Listar sesiones médicas
# Uso: ./02_list_sessions.sh [user_id] [limit]

set -e

# Cargar variables de entorno
if [ -f .env.test ]; then
  source .env.test
fi

# Configuración
API_BASE_URL=${API_BASE_URL:-"http://localhost:7001"}
AUTH_TOKEN=${AUTH_TOKEN:-""}

# Parámetros opcionales
USER_ID=${1:-""}
LIMIT=${2:-10}

# Validar token
if [ -z "$AUTH_TOKEN" ]; then
  echo "❌ Error: AUTH_TOKEN no configurado"
  exit 1
fi

# Construir query params
QUERY_PARAMS="limit=$LIMIT"
if [ -n "$USER_ID" ]; then
  QUERY_PARAMS="$QUERY_PARAMS&user_id=$USER_ID"
fi

# Ejecutar request
echo "📋 Listando sesiones..."
echo ""

RESPONSE=$(curl -s -X GET \
  "$API_BASE_URL/api/workflows/aurity/sessions?$QUERY_PARAMS" \
  -H "Authorization: Bearer $AUTH_TOKEN")

# Verificar respuesta
if echo "$RESPONSE" | jq -e '.sessions' > /dev/null 2>&1; then
  TOTAL=$(echo "$RESPONSE" | jq '.sessions | length')
  echo "✅ Encontradas $TOTAL sesiones"
  echo ""
  echo "$RESPONSE" | jq '.'
  exit 0
else
  echo "❌ Error listando sesiones"
  echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
  exit 1
fi
