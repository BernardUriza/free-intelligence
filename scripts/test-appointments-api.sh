#!/bin/bash

# Test Appointments API Endpoints
# Quick validation script for debugging appointment calendar issues

set -e

API_BASE="${API_BASE:-http://localhost:7001}"
CLINIC_ID="${CLINIC_ID:-}"
APPOINTMENT_ID="${APPOINTMENT_ID:-}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔍 Testing Appointments API Endpoints${NC}\n"

# 1. Health Check
echo -e "${YELLOW}1. Health Check${NC}"
curl -s "${API_BASE}/health" | jq '.' || echo -e "${RED}❌ Backend not responding${NC}"
echo ""

# 2. List Clinics
echo -e "${YELLOW}2. List Clinics${NC}"
CLINICS=$(curl -s "${API_BASE}/api/clinics" | jq -r '.clinics[0].clinic_id')
if [ -n "$CLINICS" ]; then
    echo -e "${GREEN}✅ Found clinics${NC}"
    CLINIC_ID="$CLINICS"
    echo "   Using clinic_id: $CLINIC_ID"
else
    echo -e "${RED}❌ No clinics found${NC}"
    exit 1
fi
echo ""

# 3. List Doctors for Clinic
echo -e "${YELLOW}3. List Doctors${NC}"
DOCTORS=$(curl -s "${API_BASE}/api/clinics/${CLINIC_ID}/doctors" | jq -r '.doctors | length')
if [ "$DOCTORS" -gt 0 ]; then
    echo -e "${GREEN}✅ Found ${DOCTORS} doctors${NC}"
    curl -s "${API_BASE}/api/clinics/${CLINIC_ID}/doctors" | jq '.doctors[] | {doctor_id, nombre, apellido, especialidad}'
else
    echo -e "${YELLOW}⚠️  No doctors found for this clinic${NC}"
fi
echo ""

# 4. List Appointments (Today)
echo -e "${YELLOW}4. List Appointments (Today)${NC}"
TODAY=$(date +%Y-%m-%d)
echo "   Date: $TODAY"
APPOINTMENTS_RESPONSE=$(curl -s "${API_BASE}/api/clinics/${CLINIC_ID}/appointments?date=${TODAY}")
APPOINTMENTS_COUNT=$(echo "$APPOINTMENTS_RESPONSE" | jq -r '.total // 0')

if [ "$APPOINTMENTS_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✅ Found ${APPOINTMENTS_COUNT} appointments${NC}"
    echo "$APPOINTMENTS_RESPONSE" | jq '.appointments[] | {appointment_id, scheduled_at, patient_id, doctor_id, status}'

    # Save first appointment ID for testing update
    APPOINTMENT_ID=$(echo "$APPOINTMENTS_RESPONSE" | jq -r '.appointments[0].appointment_id')
else
    echo -e "${YELLOW}⚠️  No appointments found for today${NC}"
fi
echo ""

# 5. List Appointments (All - no date filter)
echo -e "${YELLOW}5. List Appointments (All)${NC}"
ALL_APPOINTMENTS=$(curl -s "${API_BASE}/api/clinics/${CLINIC_ID}/appointments")
ALL_COUNT=$(echo "$ALL_APPOINTMENTS" | jq -r '.total // 0')

if [ "$ALL_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✅ Found ${ALL_COUNT} total appointments${NC}"
    echo "$ALL_APPOINTMENTS" | jq '.appointments[0:3] | .[] | {appointment_id, scheduled_at, status}'
else
    echo -e "${YELLOW}⚠️  No appointments found${NC}"
fi
echo ""

# 6. Test Update Appointment (if we have one)
if [ -n "$APPOINTMENT_ID" ]; then
    echo -e "${YELLOW}6. Test Update Appointment${NC}"
    echo "   Appointment ID: $APPOINTMENT_ID"

    # Try to update duration
    UPDATE_RESPONSE=$(curl -s -X PATCH \
        "${API_BASE}/api/clinics/${CLINIC_ID}/appointments/${APPOINTMENT_ID}" \
        -H "Content-Type: application/json" \
        -d '{"estimated_duration": 30}')

    UPDATE_SUCCESS=$(echo "$UPDATE_RESPONSE" | jq -r '.appointment_id // empty')

    if [ -n "$UPDATE_SUCCESS" ]; then
        echo -e "${GREEN}✅ Successfully updated appointment${NC}"
        echo "$UPDATE_RESPONSE" | jq '{appointment_id, estimated_duration, scheduled_at, status}'
    else
        echo -e "${RED}❌ Failed to update appointment${NC}"
        echo "$UPDATE_RESPONSE" | jq '.'
    fi
else
    echo -e "${YELLOW}6. Test Update Appointment - Skipped (no appointments)${NC}"
fi
echo ""

# 7. Summary
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}📊 Summary${NC}"
echo -e "   Clinic ID: ${CLINIC_ID}"
echo -e "   Doctors: ${DOCTORS}"
echo -e "   Appointments (today): ${APPOINTMENTS_COUNT}"
echo -e "   Appointments (total): ${ALL_COUNT}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 8. Common Issues Check
echo -e "${YELLOW}🔧 Common Issues Check${NC}"

# Check if any appointments have invalid dates
if [ "$ALL_COUNT" -gt 0 ]; then
    INVALID_DATES=$(echo "$ALL_APPOINTMENTS" | jq '[.appointments[] | select(.scheduled_at == null or .scheduled_at == "")] | length')
    if [ "$INVALID_DATES" -gt 0 ]; then
        echo -e "${RED}❌ Found ${INVALID_DATES} appointments with invalid dates${NC}"
    else
        echo -e "${GREEN}✅ All appointments have valid dates${NC}"
    fi

    # Check for missing doctor_id
    MISSING_DOCTORS=$(echo "$ALL_APPOINTMENTS" | jq '[.appointments[] | select(.doctor_id == null or .doctor_id == "")] | length')
    if [ "$MISSING_DOCTORS" -gt 0 ]; then
        echo -e "${RED}❌ Found ${MISSING_DOCTORS} appointments with missing doctor_id${NC}"
    else
        echo -e "${GREEN}✅ All appointments have doctor_id${NC}"
    fi
fi

echo ""
echo -e "${GREEN}✨ Test Complete${NC}"
