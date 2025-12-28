# API Contract - Aurity Backend

**Version:** 1.0.0  
**Base URL:** `${NEXT_PUBLIC_BACKEND_URL}/api/workflows/aurity`  
**Authentication:** Auth0 JWT Bearer Token  
**Date:** December 18, 2025

---

## 🔐 Authentication

All endpoints require a valid Auth0 JWT token in the `Authorization` header:

```http
Authorization: Bearer <jwt_token>
```

### Token Claims

```json
{
  "sub": "auth0|user123",
  "email": "doctor@clinic.com",
  "https://aurity.app/roles": ["FI-clinician", "FI-staff"]
}
```

### Roles

- `FI-superadmin` - Full system access
- `FI-clinician` - Medical staff (doctors, nurses)
- `FI-staff` - Administrative staff
- `FI-patient` - Patient portal access

---

## 📋 Core Endpoints

### 1. Chat Assistant

**POST** `/assistant/chat`

Send message to AI assistant.

**Request:**
```json
{
  "messages": [
    {
      "role": "user",
      "content": "Agregar alergia a penicilina"
    }
  ],
  "user": "auth0|doctor123",
  "session_id": "session_20250118_001",
  "enable_thinking": true
}
```

**Response:**
```json
{
  "id": "chat_response_123",
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "He registrado la alergia a penicilina en el expediente."
      },
      "finish_reason": "stop"
    }
  ],
  "persona": "general_assistant",
  "thinking": "Usuario solicita agregar alergia...",
  "emotional_analysis": {
    "state": "neutral",
    "confidence": 0.85,
    "suggested_tone": "professional"
  }
}
```

**Streaming Version:**

**POST** `/assistant/chat/stream`

Same request, but returns SSE stream:

```
event: meta
data: {"thinking": "Analizando solicitud..."}

event: message
data: {"choices": [{"delta": {"content": "He registrado"}}]}

event: message
data: {"choices": [{"delta": {"content": " la alergia"}}]}

data: [DONE]
```

---

### 2. Sessions Management

**GET** `/sessions`

List all sessions for current user.

**Query Parameters:**
- `limit` (optional): Number of sessions (default: 50)
- `offset` (optional): Pagination offset (default: 0)
- `status` (optional): Filter by status (`active`, `completed`, `archived`)

**Response:**
```json
{
  "sessions": [
    {
      "session_id": "session_20250118_001",
      "patient_name": "Juan Pérez",
      "start_time": "2025-01-18T10:30:00Z",
      "end_time": "2025-01-18T11:15:00Z",
      "status": "completed",
      "doctor_id": "auth0|doctor123"
    }
  ],
  "total": 150,
  "has_more": true
}
```

---

**POST** `/sessions`

Create new session.

**Request:**
```json
{
  "patient_id": "patient_123",
  "session_type": "consultation",
  "metadata": {
    "clinic_id": "clinic_001",
    "appointment_id": "apt_456"
  }
}
```

**Response:**
```json
{
  "session_id": "session_20250118_001",
  "created_at": "2025-01-18T10:30:00Z",
  "status": "active"
}
```

---

**GET** `/sessions/{session_id}/monitor`

Get real-time session status (SSE stream).

**Response (SSE):**
```
event: status
data: {"status": "active", "duration_seconds": 45}

event: transcription
data: {"text": "Paciente refiere dolor abdominal"}

event: soap_update
data: {"section": "subjective", "content": "Dolor abdominal..."}
```

---

### 3. SOAP Notes

**GET** `/sessions/{session_id}/soap`

Get SOAP note for session.

**Response:**
```json
{
  "session_id": "session_20250118_001",
  "subjective": "Paciente refiere dolor de cabeza desde hace 2 días...",
  "objective": "TA: 120/80 mmHg, FC: 72 lpm, Temp: 36.5°C...",
  "assessment": "Probable cefalea tensional...",
  "plan": "Prescribir paracetamol 500mg c/8h PRN...",
  "created_at": "2025-01-18T11:00:00Z",
  "updated_at": "2025-01-18T11:10:00Z"
}
```

---

**PUT** `/sessions/{session_id}/soap`

Update SOAP note.

**Request:**
```json
{
  "subjective": "Updated subjective...",
  "objective": "Updated objective...",
  "assessment": "Updated assessment...",
  "plan": "Updated plan..."
}
```

**Response:**
```json
{
  "session_id": "session_20250118_001",
  "updated_at": "2025-01-18T11:15:00Z",
  "status": "success"
}
```

---

### 4. Audio Transcription

**POST** `/stream`

Upload audio chunk for transcription.

**Request (multipart/form-data):**
```
session_id: session_20250118_001
chunk_number: 1
mode: medical
audio: <binary_file.webm>
```

**Response:**
```json
{
  "session_id": "session_20250118_001",
  "chunk_number": 1,
  "status": "processing"
}
```

---

**GET** `/jobs/{session_id}`

Get transcription status.

**Query Parameters:**
- `chunk_number` (optional): Specific chunk to check

**Response:**
```json
{
  "session_id": "session_20250118_001",
  "status": "completed",
  "chunks": [
    {
      "chunk_number": 1,
      "status": "completed",
      "transcript": "Paciente refiere dolor abdominal agudo...",
      "duration_seconds": 30
    }
  ]
}
```

---

### 5. Personas (AI Assistants)

**GET** `/personas`

Get available AI personas.

**Response:**
```json
{
  "personas": [
    {
      "id": "general_assistant",
      "name": "Asistente General",
      "description": "Asistente médico general",
      "model": "claude-3-5-sonnet-20241022",
      "temperature": 0.7,
      "max_tokens": 2048,
      "voice": "nova"
    },
    {
      "id": "soap_editor",
      "name": "Editor SOAP",
      "description": "Especialista en notas SOAP",
      "model": "claude-3-5-sonnet-20241022",
      "temperature": 0.3,
      "max_tokens": 4096
    }
  ]
}
```

---

### 6. Timeline & History

**GET** `/timeline/sessions`

Get session timeline with events.

**Query Parameters:**
- `start_date` (optional): ISO 8601 date
- `end_date` (optional): ISO 8601 date
- `limit` (optional): Max results (default: 50)

**Response:**
```json
{
  "timeline": [
    {
      "session_id": "session_20250118_001",
      "timestamp": "2025-01-18T10:30:00Z",
      "event_type": "session_start",
      "metadata": {
        "patient_name": "Juan Pérez",
        "doctor_id": "auth0|doctor123"
      }
    },
    {
      "session_id": "session_20250118_001",
      "timestamp": "2025-01-18T11:00:00Z",
      "event_type": "soap_generated",
      "metadata": {
        "sections": ["subjective", "objective", "assessment", "plan"]
      }
    }
  ],
  "total": 250,
  "has_more": true
}
```

---

### 7. KPIs & Metrics

**GET** `/kpis`

Get system metrics.

**Query Parameters:**
- `window` (optional): Time window (`5m`, `15m`, `1h`, `24h`)
- `view` (optional): View type (`summary`, `chips`, `timeseries`)

**Response:**
```json
{
  "timestamp": "2025-01-18T12:00:00Z",
  "window": "5m",
  "metrics": {
    "sessions_active": 5,
    "sessions_completed_today": 42,
    "avg_session_duration_minutes": 25.5,
    "transcription_avg_latency_ms": 1200,
    "soap_generation_avg_latency_ms": 800,
    "system_health": "healthy"
  }
}
```

---

### 8. System Health

**GET** `/system/health`

Get backend health status.

**Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2025-01-18T12:00:00Z",
  "services": {
    "database": "healthy",
    "storage": "healthy",
    "llm_provider": "healthy",
    "transcription": "healthy"
  }
}
```

---

## 🔒 Error Responses

All endpoints return consistent error format:

**4xx Client Errors:**
```json
{
  "detail": "Invalid request parameters",
  "error_code": "INVALID_INPUT",
  "timestamp": "2025-01-18T12:00:00Z"
}
```

**5xx Server Errors:**
```json
{
  "detail": "Internal server error",
  "error_code": "INTERNAL_ERROR",
  "request_id": "req_abc123",
  "timestamp": "2025-01-18T12:00:00Z"
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `UNAUTHORIZED` | 401 | Invalid or missing JWT token |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `INVALID_INPUT` | 400 | Invalid request parameters |
| `RATE_LIMIT` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |
| `SERVICE_UNAVAILABLE` | 503 | Backend service down |

---

## 📊 Rate Limits

| Endpoint | Rate Limit |
|----------|-----------|
| `/assistant/chat` | 60 requests/minute |
| `/stream` | 10 uploads/minute |
| `/sessions` | 120 requests/minute |
| Other endpoints | 300 requests/minute |

**Rate Limit Headers:**
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1705582800
```

---

## 🔄 Versioning

API version is specified in URL:
- Current: `/api/workflows/aurity/*` (v1, implicit)
- Future: `/api/v2/workflows/aurity/*`

Breaking changes will increment major version.

---

## 📝 Notes

1. **HIPAA Compliance:** Never log PHI/PII in plaintext
2. **Idempotency:** POST requests support `Idempotency-Key` header
3. **Pagination:** Use `limit` and `offset` for large datasets
4. **Timestamps:** All timestamps in ISO 8601 UTC format
5. **Content-Type:** All requests/responses use `application/json` (except multipart uploads)

---

## 🚀 Quick Start Example

```typescript
// Configure API client
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:7001';

// Get access token
const token = await getAccessTokenSilently();

// Make authenticated request
const response = await fetch(`${BACKEND_URL}/api/workflows/aurity/sessions`, {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  },
});

const data = await response.json();
console.log(data.sessions);
```

---

**Maintained by:** Backend Team  
**Contact:** [Create issue on GitHub]  
**Last Updated:** December 18, 2025
