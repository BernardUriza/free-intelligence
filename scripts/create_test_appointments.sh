#!/bin/bash
# Create test data for appointments calendar testing
# Card: FI-CHECKIN-005 (Phase 3)

set -e

API_BASE="http://localhost:7001/api"
CLINIC_ID="7f6ef952-d755-43d9-b668-32c3b6879149"

echo "🏥 Creating test doctors..."

# Create Dr. García (Cardiology)
DOCTOR1=$(curl -s -X POST "${API_BASE}/clinics/${CLINIC_ID}/doctors" \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "María",
    "apellido": "García",
    "display_name": "Dra. García",
    "especialidad": "cardiology",
    "cedula_profesional": "12345678",
    "avg_consultation_minutes": 30
  }')

DOCTOR1_ID=$(echo $DOCTOR1 | jq -r '.doctor_id')
echo "✅ Created Dr. García (Cardiology): $DOCTOR1_ID"

# Create Dr. Rodríguez (Pediatrics)
DOCTOR2=$(curl -s -X POST "${API_BASE}/clinics/${CLINIC_ID}/doctors" \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Carlos",
    "apellido": "Rodríguez",
    "display_name": "Dr. Rodríguez",
    "especialidad": "pediatrics",
    "cedula_profesional": "87654321",
    "avg_consultation_minutes": 20
  }')

DOCTOR2_ID=$(echo $DOCTOR2 | jq -r '.doctor_id')
echo "✅ Created Dr. Rodríguez (Pediatrics): $DOCTOR2_ID"

# Create Dr. López (Orthopedics)
DOCTOR3=$(curl -s -X POST "${API_BASE}/clinics/${CLINIC_ID}/doctors" \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Ana",
    "apellido": "López",
    "display_name": "Dra. López",
    "especialidad": "orthopedics",
    "cedula_profesional": "11223344",
    "avg_consultation_minutes": 25
  }')

DOCTOR3_ID=$(echo $DOCTOR3 | jq -r '.doctor_id')
echo "✅ Created Dr. López (Orthopedics): $DOCTOR3_ID"

echo ""
echo "📅 Creating test appointments for today..."

# Get today's date
TODAY=$(date +%Y-%m-%d)

# Generate patient IDs (UUIDs)
PATIENT1="550e8400-e29b-41d4-a716-446655440001"
PATIENT2="550e8400-e29b-41d4-a716-446655440002"
PATIENT3="550e8400-e29b-41d4-a716-446655440003"
PATIENT4="550e8400-e29b-41d4-a716-446655440004"

# Appointment 1: Dr. García at 9:00 AM (30 min)
APT1=$(curl -s -X POST "${API_BASE}/clinics/${CLINIC_ID}/appointments" \
  -H "Content-Type: application/json" \
  -d "{
    \"patient_id\": \"${PATIENT1}\",
    \"doctor_id\": \"${DOCTOR1_ID}\",
    \"scheduled_at\": \"${TODAY}T09:00:00Z\",
    \"appointment_type\": \"FIRST_TIME\",
    \"estimated_duration\": 30,
    \"reason\": \"Consulta de cardiología\",
    \"notes\": \"Paciente con hipertensión\"
  }")

echo "✅ Appointment: Dr. García @ 9:00 AM (30 min)"

# Appointment 2: Dr. García at 10:00 AM (30 min)
APT2=$(curl -s -X POST "${API_BASE}/clinics/${CLINIC_ID}/appointments" \
  -H "Content-Type: application/json" \
  -d "{
    \"patient_id\": \"${PATIENT2}\",
    \"doctor_id\": \"${DOCTOR1_ID}\",
    \"scheduled_at\": \"${TODAY}T10:00:00Z\",
    \"appointment_type\": \"FOLLOW_UP\",
    \"estimated_duration\": 30,
    \"reason\": \"Seguimiento cardiaco\",
    \"notes\": \"Revisión de medicamentos\"
  }")

echo "✅ Appointment: Dr. García @ 10:00 AM (30 min)"

# Appointment 3: Dr. Rodríguez at 9:00 AM (20 min)
APT3=$(curl -s -X POST "${API_BASE}/clinics/${CLINIC_ID}/appointments" \
  -H "Content-Type: application/json" \
  -d "{
    \"patient_id\": \"${PATIENT3}\",
    \"doctor_id\": \"${DOCTOR2_ID}\",
    \"scheduled_at\": \"${TODAY}T09:00:00Z\",
    \"appointment_type\": \"FIRST_TIME\",
    \"estimated_duration\": 20,
    \"reason\": \"Consulta pediátrica\",
    \"notes\": \"Revisión de crecimiento\"
  }")

echo "✅ Appointment: Dr. Rodríguez @ 9:00 AM (20 min)"

# Appointment 4: Dr. López at 11:00 AM (25 min)
APT4=$(curl -s -X POST "${API_BASE}/clinics/${CLINIC_ID}/appointments" \
  -H "Content-Type: application/json" \
  -d "{
    \"patient_id\": \"${PATIENT4}\",
    \"doctor_id\": \"${DOCTOR3_ID}\",
    \"scheduled_at\": \"${TODAY}T11:00:00Z\",
    \"appointment_type\": \"FOLLOW_UP\",
    \"estimated_duration\": 25,
    \"reason\": \"Dolor de rodilla\",
    \"notes\": \"Evaluación para fisioterapia\"
  }")

echo "✅ Appointment: Dr. López @ 11:00 AM (25 min)"

echo ""
echo "✨ Test data created successfully!"
echo ""
echo "📊 Summary:"
echo "  Clinic ID: ${CLINIC_ID}"
echo "  Doctors: 3 (García, Rodríguez, López)"
echo "  Appointments: 4 (scheduled for today)"
echo ""
echo "🌐 Open frontend: http://localhost:9000/admin/appointments"
echo "📡 Backend running: http://localhost:7001"
echo ""
echo "🧪 Test scenarios:"
echo "  1. Drag Dr. García's 9:00 AM appointment to 2:00 PM"
echo "  2. Drag Dr. García's 10:00 AM appointment to Dr. Rodríguez"
echo "  3. Resize Dr. López's appointment from 25 min to 45 min"
echo "  4. Edit Dr. Rodríguez's appointment details"
echo ""
