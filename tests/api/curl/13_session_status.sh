#!/bin/bash

# 13_session_status.sh - Obtener estado completo de sesión
# Uso: ./13_session_status.sh <session_id>

set -e

# Cargar variables de entorno
if [ -f .env.test ]; then
  source .env.test
fi

# Configuración
API_BASE_URL=${API_BASE_URL:-"http://localhost:7001"}
AUTH_TOKEN=${AUTH_TOKEN:-""}

# Obtener session_id
if [ -n "$1" ]; then
  SESSION_ID="$1"
elif [ -f .last_session_id ]; then
  SESSION_ID=$(cat .last_session_id)
else
  echo "❌ Error: Proporciona session_id como argumento"
  exit 1
fi

# Validar token
if [ -z "$AUTH_TOKEN" ]; then
  echo "❌ Error: AUTH_TOKEN no configurado"
  exit 1
fi

# Ejecutar request
echo "📊 Obteniendo estado de sesión: $SESSION_ID"
echo ""

RESPONSE=$(curl -s -X GET \
  "$API_BASE_URL/api/workflows/aurity/sessions/$SESSION_ID/status" \
  -H "Authorization: Bearer $AUTH_TOKEN")

# Verificar respuesta
if echo "$RESPONSE" | jq -e '.session_id' > /dev/null 2>&1; then
  echo "✅ Estado obtenido"
  echo ""

  # Mostrar resumen
  STATUS=$(echo "$RESPONSE" | jq -r '.status')
  PROGRESS=$(echo "$RESPONSE" | jq -r '.progress // 0')

  echo "Estado: $STATUS"
  echo "Progreso: $(echo "$PROGRESS * 100" | bc)%"
  echo ""

  # Mostrar estado de tasks
  echo "Tasks:"
  echo "$RESPONSE" | jq -r '.tasks | to_entries[] | "  - \(.key): \(.value.status) (\(.value.progress // 0 * 100)%)"'
  echo ""

  # JSON completo
  echo "Detalles completos:"
  echo "$RESPONSE" | jq '.'

  exit 0
else
  echo "❌ Error obteniendo estado"
  echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
  exit 1
fi
