#!/bin/bash
# Test assistant API endpoint in production

echo "🧪 Probando endpoint del asistente en producción..."
echo "=================================================="
echo ""

echo "Enviando mensaje de prueba..."
curl -X POST "https://app.aurity.io/api/workflows/aurity/assistant/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hola, solo estoy probando el endpoint",
    "doctor_id": "test_doctor_123",
    "doctor_name": "Dr. Test",
    "response_mode": "concise"
  }' \
  2>&1

echo ""
echo ""
echo "=================================================="
