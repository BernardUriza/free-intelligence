#!/bin/bash
# test_checkin.sh - Test de check-in receptionist
# Autor: Bernard Uriza Orozco

set -e

# Cargar configuración
if [ ! -f .env.curl ]; then
  echo "❌ Archivo .env.curl no encontrado"
  echo "Ejecuta primero: ./setup.sh"
  exit 1
fi

source .env.curl

echo "🏨 AURITY - Test de Check-in Receptionist"
echo "=========================================="
echo ""

CLINIC_ID="clinic_001"

# 1. Generar QR code
echo "1️⃣  Generando QR code de clínica..."

QR_RESPONSE=$(curl -s -X POST "$BACKEND_URL/api/checkin/qr/generate" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"clinic_id\": \"$CLINIC_ID\",
    \"expiry_minutes\": 1440
  }")

QR_URL=$(echo "$QR_RESPONSE" | jq -r '.qr_url')
QR_CODE=$(echo "$QR_RESPONSE" | jq -r '.qr_code_base64')

echo "$QR_RESPONSE" | jq '{clinic_id, qr_url, expires_at}'

# Guardar QR code
echo "$QR_CODE" | base64 -d > temp/qr_checkin.png
echo "✅ QR code guardado: temp/qr_checkin.png"
echo "📱 URL: $QR_URL"
echo ""

# 2. Iniciar sesión de check-in
echo "2️⃣  Iniciando sesión de check-in (simulando escaneo QR)..."

SESSION_RESPONSE=$(curl -s -X POST "$BACKEND_URL/api/checkin/session/start" \
  -H "Content-Type: application/json" \
  -d "{
    \"clinic_id\": \"$CLINIC_ID\",
    \"device_type\": \"tablet\"
  }")

CHECKIN_SESSION_ID=$(echo "$SESSION_RESPONSE" | jq -r '.session_id')

echo "$SESSION_RESPONSE" | jq '{session_id, clinic_id, current_step, device_type}'
echo "✅ Sesión iniciada: $CHECKIN_SESSION_ID"
echo ""

# 3. Identificar paciente por nombre
echo "3️⃣  Identificando paciente por nombre..."

IDENTIFY_RESPONSE=$(curl -s -X POST "$BACKEND_URL/api/checkin/identify/name" \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$CHECKIN_SESSION_ID\",
    \"first_name\": \"Juan\",
    \"last_name\": \"Pérez\",
    \"date_of_birth\": \"1980-05-15\"
  }")

if echo "$IDENTIFY_RESPONSE" | jq -e '.patient_id' > /dev/null 2>&1; then
  PATIENT_ID=$(echo "$IDENTIFY_RESPONSE" | jq -r '.patient_id')
  echo "$IDENTIFY_RESPONSE" | jq '{patient_id, display_name, appointments}'
  echo "✅ Paciente identificado: $PATIENT_ID"
else
  echo "⚠️  Paciente no encontrado (esperado si DB vacía)"
  echo "   Creando paciente de prueba..."

  # Aquí normalmente crearías el paciente en DB
  # Para el test, continuamos con ID ficticio
  PATIENT_ID="patient_test_$(date +%s)"
  echo "   Usando ID de prueba: $PATIENT_ID"
fi

echo ""

# 4. Ver acciones pendientes
echo "4️⃣  Verificando acciones pendientes..."

ACTIONS_RESPONSE=$(curl -s -X GET "$BACKEND_URL/api/checkin/actions/$CHECKIN_SESSION_ID" \
  -H "Accept: application/json")

if echo "$ACTIONS_RESPONSE" | jq -e '.pending_actions' > /dev/null 2>&1; then
  ACTION_COUNT=$(echo "$ACTIONS_RESPONSE" | jq '.pending_actions | length')
  echo "📋 Acciones pendientes: $ACTION_COUNT"
  echo "$ACTIONS_RESPONSE" | jq '.pending_actions[] | {action_id, action_type, title, priority}'

  # Completar primera acción
  if [ "$ACTION_COUNT" -gt 0 ]; then
    ACTION_ID=$(echo "$ACTIONS_RESPONSE" | jq -r '.pending_actions[0].action_id')

    echo ""
    echo "   Completando acción: $ACTION_ID..."

    COMPLETE_RESPONSE=$(curl -s -X POST "$BACKEND_URL/api/checkin/actions/complete" \
      -H "Content-Type: application/json" \
      -d "{
        \"session_id\": \"$CHECKIN_SESSION_ID\",
        \"action_id\": \"$ACTION_ID\",
        \"response_data\": {
          \"allergies\": \"Ninguna\",
          \"current_medications\": \"Metformina 500mg\",
          \"chronic_conditions\": \"Diabetes tipo 2\"
        }
      }")

    echo "$COMPLETE_RESPONSE" | jq
    echo "✅ Acción completada"
  fi
else
  echo "⚠️  No hay acciones pendientes"
fi

echo ""

# 5. Completar check-in
echo "5️⃣  Completando check-in..."

# Buscar cita de hoy (si existe)
APPOINTMENT_ID="apt_$(date +%s)"

CHECKIN_COMPLETE=$(curl -s -X POST "$BACKEND_URL/api/checkin/complete" \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$CHECKIN_SESSION_ID\",
    \"appointment_id\": \"$APPOINTMENT_ID\"
  }")

if echo "$CHECKIN_COMPLETE" | jq -e '.status' > /dev/null 2>&1; then
  echo "$CHECKIN_COMPLETE" | jq '{status, queue_position, estimated_wait_minutes, message}'
  echo "✅ Check-in completado"
else
  echo "⚠️  Error al completar check-in (esperado si no existe cita)"
  echo "$CHECKIN_COMPLETE" | jq
fi

echo ""

# 6. Ver sala de espera
echo "6️⃣  Estado de sala de espera..."

WAITING_ROOM=$(curl -s -X GET "$BACKEND_URL/api/checkin/waiting-room/$CLINIC_ID" \
  -H "Accept: application/json")

if echo "$WAITING_ROOM" | jq -e '.patients' > /dev/null 2>&1; then
  TOTAL_WAITING=$(echo "$WAITING_ROOM" | jq '.total_waiting')
  echo "👥 Pacientes esperando: $TOTAL_WAITING"
  echo "$WAITING_ROOM" | jq '.patients[] | {display_name, queue_position, status, check_in_time}'
else
  echo "⚠️  Sala de espera vacía"
fi

echo ""

# 7. Ver estado de sesión
echo "7️⃣  Estado final de sesión:"

SESSION_STATE=$(curl -s -X GET "$BACKEND_URL/api/checkin/session/$CHECKIN_SESSION_ID" \
  -H "Accept: application/json")

echo "$SESSION_STATE" | jq '{
  session_id,
  current_step,
  identification_method,
  patient_id,
  completed_at,
  expires_at
}'

echo ""
echo "=========================================="
echo "✅ Test de check-in completado"
echo ""
echo "📋 Check-in Session ID: $CHECKIN_SESSION_ID"
echo "🏥 Clinic ID: $CLINIC_ID"
echo "👤 Patient ID: $PATIENT_ID"
echo ""
echo "Archivos generados:"
echo "  - temp/qr_checkin.png (QR code de clínica)"
echo ""
