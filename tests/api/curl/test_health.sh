#!/bin/bash

# test_health.sh - Prueba simple de health check
# Verifica que el backend esté respondiendo

set -e

API_BASE_URL=${API_BASE_URL:-"http://localhost:7001"}

echo "🏥 Verificando salud del sistema..."
echo "   URL: $API_BASE_URL/health"
echo ""

RESPONSE=$(curl -s "$API_BASE_URL/health")

if echo "$RESPONSE" | jq -e '.status' > /dev/null 2>&1; then
  STATUS=$(echo "$RESPONSE" | jq -r '.status')

  if [ "$STATUS" == "ok" ]; then
    echo "✅ Sistema saludable"
    echo ""
    echo "$RESPONSE" | jq '.'
    exit 0
  else
    echo "⚠️  Sistema responde pero status: $STATUS"
    echo "$RESPONSE" | jq '.'
    exit 1
  fi
else
  echo "❌ Error en health check"
  echo "$RESPONSE"
  exit 1
fi
