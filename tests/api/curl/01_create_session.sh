#!/bin/bash

# 01_create_session.sh - Crear nueva sesión médica
# Uso: ./01_create_session.sh [patient_id] [provider_id]

set -e

# Cargar variables de entorno
if [ -f .env.test ]; then
  source .env.test
fi

# Configuración
API_BASE_URL=${API_BASE_URL:-"http://localhost:7001"}
AUTH_TOKEN=${AUTH_TOKEN:-""}

# Parámetros opcionales
PATIENT_ID=${1:-"patient-$(date +%s)"}
PROVIDER_ID=${2:-"provider-demo-001"}

# Validar token
if [ -z "$AUTH_TOKEN" ]; then
  echo "❌ Error: AUTH_TOKEN no configurado"
  echo "Exporta tu token: export AUTH_TOKEN='eyJhbGci...'"
  exit 1
fi

# Crear payload
PAYLOAD=$(cat <<EOF
{
  "patient_id": "$PATIENT_ID",
  "provider_id": "$PROVIDER_ID",
  "session_type": "consultation",
  "metadata": {
    "created_by": "curl_test",
    "test_mode": true
  }
}
EOF
)

# Ejecutar request
echo "📝 Creando sesión médica..."
echo "   Patient: $PATIENT_ID"
echo "   Provider: $PROVIDER_ID"
echo ""

RESPONSE=$(curl -s -X POST \
  "$API_BASE_URL/api/workflows/aurity/sessions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d "$PAYLOAD")

# Verificar respuesta
if echo "$RESPONSE" | jq -e '.session_id' > /dev/null 2>&1; then
  echo "✅ Sesión creada exitosamente"
  echo ""
  echo "$RESPONSE" | jq '.'

  # Guardar session_id para otros scripts
  SESSION_ID=$(echo "$RESPONSE" | jq -r '.session_id')
  echo "$SESSION_ID" > .last_session_id

  exit 0
else
  echo "❌ Error creando sesión"
  echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
  exit 1
fi
