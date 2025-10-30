# AURITY ↔ Free Intelligence Integration

**Last Updated**: 2025-10-28
**Status**: Implementation Ready
**API Gateway**: `backend/aurity_gateway.py`

---

## 🎯 Overview

Integration between **AURITY** (frontend/sensors) and **Free Intelligence** (backend/brain).

```
┌──────────────────────────────────────────────────────────────┐
│                      AURITY                                   │
│  (La Cara y Los Sensores)                                    │
├──────────────────────────────────────────────────────────────┤
│  - React 19 UI (consultas médicas)                           │
│  - Redux state management                                     │
│  - WebRTC (audio/video streams)                              │
│  - IoT sensors (MQTT)                                        │
└─────────────────────┬────────────────────────────────────────┘
                      │
                      │ HTTP/WebSocket
                      ▼
┌──────────────────────────────────────────────────────────────┐
│              API GATEWAY (puerto 7002)                        │
│              backend/aurity_gateway.py                        │
├──────────────────────────────────────────────────────────────┤
│  Endpoints:                                                   │
│  - POST /aurity/redux-action                                 │
│  - GET /aurity/consultation/{id}                             │
│  - WebSocket /aurity/consultation/{id}/stream                │
└─────────────────────┬────────────────────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────────────────────┐
│              FREE INTELLIGENCE                                │
│  (El Sistema Nervioso y Los Tentáculos)                     │
├──────────────────────────────────────────────────────────────┤
│  Backend Services:                                            │
│  ├─ fi_consult_service.py (event sourcing)                   │
│  ├─ adapters_redux.py (Redux → Events)                       │
│  ├─ fi_event_store.py (HDF5 + SHA256)                        │
│  ├─ llm_router.py (Ollama/Claude)                            │
│  ├─ decision_mw.py (reglas de negocio)                       │
│  └─ metrics.py (observabilidad)                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 📡 Endpoints

### 1. POST `/aurity/redux-action`

Recibe Redux action de AURITY, traduce a domain event, persiste en event store.

**Request**:
```json
{
  "type": "medicalChat/addMessage",
  "payload": {
    "role": "user",
    "content": "Patient has chest pain for 30 minutes",
    "timestamp": "2025-10-28T12:00:00Z"
  },
  "consultation_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "aurity_user"
}
```

**Response**:
```json
{
  "success": true,
  "event_id": "7f27ad07-f829-4d62-a92a-f1237a81f3bb",
  "event_type": "MESSAGE_RECEIVED",
  "consultation_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-10-28T12:00:01.234Z",
  "message": "Redux action 'medicalChat/addMessage' processed successfully"
}
```

**Redux Actions Soportadas** (30 total, ver `docs/MAPPING.json`):
- `medicalChat/addMessage` → `MESSAGE_RECEIVED`
- `medicalChat/updateMessage` → `MESSAGE_UPDATED`
- `medicalChat/deleteMessage` → `MESSAGE_DELETED`
- `extraction/startExtraction` → `EXTRACTION_STARTED`
- `extraction/completeExtraction` → `EXTRACTION_COMPLETED`
- `wipData/updateDemographics` → `DEMOGRAPHICS_UPDATED`
- `wipData/updateSymptoms` → `SYMPTOMS_UPDATED`
- `soap/generateSOAP` → `SOAP_GENERATION_STARTED`
- `soap/sectionCompleted` → `SOAP_SECTION_COMPLETED`
- `soap/generationCompleted` → `SOAP_GENERATION_COMPLETED`
- ... (ver `docs/MAPPING.json` para lista completa)

**Error Handling**:
- `400 Bad Request`: Invalid Redux action structure
- `500 Internal Server Error`: Failed to process action

---

### 2. GET `/aurity/consultation/{consultation_id}`

Reconstruye estado actual de consulta desde event stream.

**Request**:
```
GET /aurity/consultation/550e8400-e29b-41d4-a716-446655440000
```

**Response**:
```json
{
  "consultation_id": "550e8400-e29b-41d4-a716-446655440000",
  "state": {
    "messages": [
      {
        "role": "user",
        "content": "Patient has chest pain",
        "timestamp": "2025-10-28T12:00:00Z"
      },
      {
        "role": "assistant",
        "content": "Can you describe the pain? Is it sharp or dull?",
        "timestamp": "2025-10-28T12:00:05Z"
      }
    ],
    "demographics": {
      "age": 58,
      "gender": "M",
      "name": "Robert Chen"
    },
    "symptoms": {
      "primary_symptoms": ["chest pain", "shortness of breath"],
      "duration": "30 minutes",
      "severity": "HIGH"
    },
    "soap": {
      "subjective": "58-year-old male with crushing chest pain...",
      "objective": "...",
      "assessment": "Possible acute coronary syndrome",
      "plan": "Immediate EKG, cardiac markers, aspirin 325mg"
    },
    "urgency": "CRITICAL"
  },
  "event_count": 47,
  "last_updated": "2025-10-28T12:05:30.123Z"
}
```

**Error Handling**:
- `404 Not Found`: Consultation not found
- `500 Internal Server Error`: Failed to reconstruct state

---

### 3. WebSocket `/aurity/consultation/{consultation_id}/stream`

Stream de eventos en tiempo real.

**Client Code (JavaScript)**:
```javascript
const consultationId = '550e8400-e29b-41d4-a716-446655440000';
const ws = new WebSocket(
  `ws://localhost:7002/aurity/consultation/${consultationId}/stream`
);

ws.onopen = () => {
  console.log('WebSocket connected');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === 'HISTORICAL_EVENT') {
    // Catchup: eventos históricos
    console.log('Historical event:', data);
  } else if (data.type === 'EVENT_APPENDED') {
    // Evento nuevo en tiempo real
    console.log('New event:', data);
    // Update Redux store
    dispatch(appendEvent(data));
  }
};

ws.onclose = () => {
  console.log('WebSocket disconnected');
};

// Ping/Pong (keep-alive)
setInterval(() => {
  ws.send(JSON.stringify({ type: 'PING' }));
}, 30000);
```

**Message Types**:
- `HISTORICAL_EVENT`: Eventos históricos (catchup al conectar)
- `EVENT_APPENDED`: Nuevo evento en tiempo real
- `PONG`: Respuesta a ping (keep-alive)

---

## 🔄 Integration Flow

### Flow 1: Usuario envía mensaje

```
AURITY (React)
  │
  ├─ 1. User types: "I have chest pain"
  ├─ 2. Redux dispatch: { type: 'medicalChat/addMessage', payload: {...} }
  │
  └─→ POST /aurity/redux-action
      │
      ▼
API Gateway (aurity_gateway.py)
  │
  ├─ 3. Validate Redux action
  ├─ 4. Translate to domain event (MESSAGE_RECEIVED)
  ├─ 5. Append to event store (HDF5 + SHA256)
  ├─ 6. Broadcast to WebSocket subscribers
  │
  └─→ Return success response
      │
      ▼
FREE INTELLIGENCE
  │
  ├─ 7. Event persisted in HDF5
  ├─ 8. LLM processes message (llm_router)
  ├─ 9. Decision rules applied (decision_mw)
  ├─ 10. New event: MESSAGE_RECEIVED (assistant response)
  │
  └─→ Broadcast via WebSocket
      │
      ▼
AURITY (React)
  │
  └─ 11. Redux receives event via WebSocket
      └─ 12. UI updates with assistant response
```

### Flow 2: Reconstruir estado al cargar consulta

```
AURITY (React)
  │
  ├─ 1. User opens consultation page
  ├─ 2. componentDidMount() or useEffect()
  │
  └─→ GET /aurity/consultation/{id}
      │
      ▼
API Gateway
  │
  ├─ 3. Load event stream from HDF5
  ├─ 4. Reconstruct state from events
  │
  └─→ Return current state
      │
      ▼
AURITY (React)
  │
  ├─ 5. Redux hydration: setState(response.state)
  └─ 6. UI renders with current state
```

---

## 🚀 Running the Gateway

### Development

```bash
# Start API Gateway
python3 backend/aurity_gateway.py

# Server starts on http://localhost:7002
```

### Production (Docker)

```bash
# Build Docker image
docker build -t fi-aurity-gateway .

# Run container
docker run -d \
  -p 7002:7002 \
  -v $(pwd)/storage:/app/storage \
  --name fi-gateway \
  fi-aurity-gateway
```

---

## 🧪 Testing

### cURL Examples

**1. Health Check**:
```bash
curl http://localhost:7002/health
```

**2. Send Redux Action**:
```bash
curl -X POST http://localhost:7002/aurity/redux-action \
  -H "Content-Type: application/json" \
  -d '{
    "type": "medicalChat/addMessage",
    "payload": {
      "role": "user",
      "content": "Patient has chest pain",
      "timestamp": "2025-10-28T12:00:00Z"
    },
    "consultation_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "test_user"
  }'
```

**3. Get Consultation State**:
```bash
curl http://localhost:7002/aurity/consultation/550e8400-e29b-41d4-a716-446655440000
```

**4. WebSocket (wscat)**:
```bash
npm install -g wscat
wscat -c ws://localhost:7002/aurity/consultation/550e8400-e29b-41d4-a716-446655440000/stream
```

---

## 📊 Monitoring

**Logs**:
```bash
# Tail logs (JSON format)
tail -f logs/fi_gateway.log | jq .
```

**Metrics** (via `backend/metrics.py`):
- Latency: p50, p95, p99
- Event throughput: events/second
- WebSocket connections: active count
- Error rate: by endpoint

---

## 🔒 Security

**CORS**:
- Allowed origins: `http://localhost:3000`, `http://localhost:5173` (AURITY dev servers)
- Production: Configure specific AURITY domain

**Authentication** (TODO):
- JWT tokens
- API keys per AURITY instance
- Rate limiting

**Data Privacy**:
- No PHI in logs (only consultation IDs)
- SHA256 audit trail
- WORM event store (append-only, no delete)

---

## 📚 References

- **Redux Actions Mapping**: `docs/MAPPING.json`
- **Event Store**: `backend/fi_event_store.py`
- **Redux Adapter**: `backend/adapters_redux.py`
- **FI Consult Service**: `backend/fi_consult_service.py`
- **ARCH.md**: `docs/ARCH.md`
- **FLOW.md**: `docs/FLOW.md`

---

**Next Steps**:
1. ✅ Implement AURITY Gateway (HECHO)
2. Test integration with AURITY frontend
3. Add authentication (JWT)
4. Deploy to NAS (Docker Compose)
5. Monitor production metrics
