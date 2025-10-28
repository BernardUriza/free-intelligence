#!/bin/bash
# Test Scenario 1: Green Path (Simple Headache - LOW urgency)

BASE_URL="http://localhost:7001"
CONSULTATION_ID=""

echo "🧪 Starting Scenario 1: Green Path (Simple Headache)"
echo "=" && echo ""

# Step 1: Start consultation
echo "📝 Step 1: Start consultation"
RESPONSE=$(curl -s -X POST "$BASE_URL/consultations" \
  -H "Content-Type: application/json" \
  -d '{"patient_id":"test-patient-green-001","user_id":"Dr. Green","metadata":{"scenario":"green","test_case":"simple_headache"}}')

CONSULTATION_ID=$(echo "$RESPONSE" | jq -r '.consultation_id')
echo "✅ Consultation ID: $CONSULTATION_ID"
echo ""

# Step 2: User message
echo "📝 Step 2: User sends message"
curl -s -X POST "$BASE_URL/consultations/$CONSULTATION_ID/events" \
  -H "Content-Type: application/json" \
  -d '{"event_type":"MESSAGE_RECEIVED","payload":{"role":"user","content":"Hi, I have a headache that started this morning. Its been about 3 hours now.","timestamp":"2025-10-28T09:20:15Z"},"user_id":"Dr. Green"}' | jq '.'
echo ""

# Step 3: Start extraction
echo "📝 Step 3: Start extraction"
curl -s -X POST "$BASE_URL/consultations/$CONSULTATION_ID/events" \
  -H "Content-Type: application/json" \
  -d '{"event_type":"EXTRACTION_STARTED","payload":{"iteration":1},"user_id":"system"}' | jq '.'
echo ""

# Step 4: Update demographics
echo "📝 Step 4: Update demographics"
curl -s -X POST "$BASE_URL/consultations/$CONSULTATION_ID/events" \
  -H "Content-Type: application/json" \
  -d '{"event_type":"DEMOGRAPHICS_UPDATED","payload":{"name":"Maria Garcia","age":28,"gender":"F"},"user_id":"system"}' | jq '.'
echo ""

# Step 5: Update symptoms
echo "📝 Step 5: Update symptoms"
curl -s -X POST "$BASE_URL/consultations/$CONSULTATION_ID/events" \
  -H "Content-Type: application/json" \
  -d '{"event_type":"SYMPTOMS_UPDATED","payload":{"primary_symptoms":["headache"],"duration":"3 hours","severity":"MILD","location":"frontal","triggers":["work stress"]}},"user_id":"system"}' | jq '.'
echo ""

# Step 6: Classify urgency
echo "📝 Step 6: Classify urgency"
curl -s -X POST "$BASE_URL/consultations/$CONSULTATION_ID/events" \
  -H "Content-Type: application/json" \
  -d '{"event_type":"URGENCY_CLASSIFIED","payload":{"urgency":"LOW","reason":"Simple tension headache, no red flags"},"user_id":"system"}' | jq '.'
echo ""

# Step 7: Complete extraction
echo "📝 Step 7: Complete extraction"
curl -s -X POST "$BASE_URL/consultations/$CONSULTATION_ID/events" \
  -H "Content-Type: application/json" \
  -d '{"event_type":"EXTRACTION_COMPLETED","payload":{"iterations":1,"completeness_percent":85},"user_id":"system"}' | jq '.'
echo ""

# Step 8: Start SOAP generation
echo "📝 Step 8: Start SOAP generation"
curl -s -X POST "$BASE_URL/consultations/$CONSULTATION_ID/events" \
  -H "Content-Type: application/json" \
  -d '{"event_type":"SOAP_GENERATION_STARTED","payload":{},"user_id":"system"}' | jq '.'
echo ""

# Step 9: Complete SOAP sections
echo "📝 Step 9: Complete SOAP sections"
curl -s -X POST "$BASE_URL/consultations/$CONSULTATION_ID/events" \
  -H "Content-Type: application/json" \
  -d '{"event_type":"SOAP_SECTION_COMPLETED","payload":{"section":"subjective"},"user_id":"system"}' | jq '.'

curl -s -X POST "$BASE_URL/consultations/$CONSULTATION_ID/events" \
  -H "Content-Type: application/json" \
  -d '{"event_type":"SOAP_SECTION_COMPLETED","payload":{"section":"objective"},"user_id":"system"}' | jq '.'

curl -s -X POST "$BASE_URL/consultations/$CONSULTATION_ID/events" \
  -H "Content-Type: application/json" \
  -d '{"event_type":"SOAP_SECTION_COMPLETED","payload":{"section":"assessment"},"user_id":"system"}' | jq '.'

curl -s -X POST "$BASE_URL/consultations/$CONSULTATION_ID/events" \
  -H "Content-Type: application/json" \
  -d '{"event_type":"SOAP_SECTION_COMPLETED","payload":{"section":"plan"},"user_id":"system"}' | jq '.'
echo ""

# Step 10: Complete SOAP generation
echo "📝 Step 10: Complete SOAP generation"
curl -s -X POST "$BASE_URL/consultations/$CONSULTATION_ID/events" \
  -H "Content-Type: application/json" \
  -d '{"event_type":"SOAP_GENERATION_COMPLETED","payload":{"total_sections":4},"user_id":"system"}' | jq '.'
echo ""

# Step 11: Get consultation state
echo "📝 Step 11: Get consultation state"
curl -s "$BASE_URL/consultations/$CONSULTATION_ID" | jq '.'
echo ""

# Step 12: Get SOAP note
echo "📝 Step 12: Get SOAP note"
curl -s "$BASE_URL/consultations/$CONSULTATION_ID/soap" | jq '.'
echo ""

# Step 13: Get event stream
echo "📝 Step 13: Get event stream"
curl -s "$BASE_URL/consultations/$CONSULTATION_ID/events" | jq '.'
echo ""

echo "✅ Scenario 1 completed!"
echo "Consultation ID: $CONSULTATION_ID"
