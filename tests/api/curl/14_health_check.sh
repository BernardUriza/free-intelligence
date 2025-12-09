#!/bin/bash

# 14_health_check.sh - Verificar salud del sistema
# Uso: ./14_health_check.sh

set -e

# Cargar variables de entorno
if [ -f .env.test ]; then
  source .env.test
fi

# Configuración
API_BASE_URL=${API_BASE_URL:-"http://localhost:7001"}

# Ejecutar request (sin autenticación, endpoint público)
echo "🏥 Verificando salud del sistema..."
echo ""

RESPONSE=$(curl -s -X GET "$API_BASE_URL/health")

# Verificar respuesta
if echo "$RESPONSE" | jq -e '.status' > /dev/null 2>&1; then
  STATUS=$(echo "$RESPONSE" | jq -r '.status')

  if [ "$STATUS" == "healthy" ] || [ "$STATUS" == "ok" ]; then
    echo "✅ Sistema saludable (status: $STATUS)"
  else
    echo "⚠️  Sistema con problemas: $STATUS"
  fi

  echo ""
  echo "$RESPONSE" | jq '.'

  # Exit code basado en status
  if [ "$STATUS" == "healthy" ] || [ "$STATUS" == "ok" ]; then
    exit 0
  else
    exit 1
  fi
else
  echo "❌ Error verificando salud del sistema"
  echo "$RESPONSE"
  exit 1
fi
