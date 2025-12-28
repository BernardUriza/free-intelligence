# FI Receptionist - Backend Implementation Spec

## Contexto del Proyecto

**AURITY** está construyendo un sistema de **Recepcionista IA** para clínicas médicas llamado **"FI Receptionist"** (Free Intelligence Receptionist). El frontend (Next.js) ya tiene implementados los componentes de UI. Tu tarea es implementar el backend en **FastAPI/Python** que soporte todas las funcionalidades.

---

## Visión del Producto

FI Receptionist es un sistema de digital signage + check-in inteligente para salas de espera de clínicas médicas. Inspirado en el modelo de "Telesecundaria" mexicana + sistemas modernos de recepcionistas IA.

### Propuesta de Valor
1. **Reduce tiempo de espera percibido** - Research muestra 35% reducción con digital signage
2. **Elimina filas en recepción** - Check-in self-service por QR
3. **Mejora engagement** - Contenido educativo, trivias, ejercicios de respiración
4. **Reduce no-shows** - Recordatorios inteligentes
5. **On-Premise First** - Datos médicos nunca salen de la clínica (HIPAA compliant)

### Modelo de Negocio (SaaS)
- **Starter**: $99/mes - 1 TV, contenido básico, check-in QR
- **Professional**: $299/mes - 3 TVs, chat IA, integraciones calendario
- **Enterprise**: $599/mes - TVs ilimitadas, EMR, white-label, API

---

## Arquitectura General

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FI RECEPTIONIST PLATFORM                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  TV Display │  │ Kiosk/Tablet│  │  Mobile App │  │  Web Widget │        │
│  │  (Waiting)  │  │  (Check-in) │  │  (Patient)  │  │  (Website)  │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                │                │                │                │
│         └────────────────┴────────────────┴────────────────┘                │
│                                   │                                          │
│                          ┌────────▼────────┐                                │
│                          │   FastAPI       │                                │
│                          │  Backend API    │                                │
│                          └────────┬────────┘                                │
│                                   │                                          │
│    ┌──────────────────────────────┼──────────────────────────────┐          │
│    │                              │                              │          │
│    ▼                              ▼                              ▼          │
│ ┌──────────┐              ┌──────────────┐              ┌──────────────┐   │
│ │ Content  │              │ Conversation │              │ Integration  │   │
│ │ Engine   │              │    Engine    │              │    Hub       │   │
│ │          │              │              │              │              │   │
│ │ • Tips   │              │ • Intent     │              │ • EMR/HIS    │   │
│ │ • Trivia │              │ • Context    │              │ • Calendly   │   │
│ │ • Videos │              │ • Actions    │              │ • Stripe     │   │
│ │ • Slides │              │ • Memory     │              │ • WhatsApp   │   │
│ └──────────┘              └──────────────┘              └──────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## MÓDULO 1: Check-in QR System (PRIORITARIO)

### Flujo de Usuario

```
Paciente llega → Ve QR en TV → Escanea con celular →
Se identifica (código/CURP/nombre) → Confirma identidad →
Completa acciones pendientes (pagar, firmar) → Check-in exitoso →
TV se actualiza con "María García ha llegado"
```

### Endpoints Requeridos

#### 1.1 QR Code Generation
```python
POST /api/checkin/qr/generate
Request:
{
    "clinic_id": "string"
}
Response:
{
    "qr_data": "string (base64 PNG)",
    "qr_url": "https://app.aurity.io/checkin?clinic=xxx&t=xxx&n=xxx",
    "expires_at": "ISO datetime (5 minutes from now)"
}
```

#### 1.2 Session Management
```python
POST /api/checkin/session/start
Request:
{
    "clinic_id": "string",
    "device_type": "mobile" | "kiosk" | "tablet"
}
Response:
{
    "session_id": "uuid",
    "clinic_id": "string",
    "current_step": "identify",
    "started_at": "ISO datetime",
    "expires_at": "ISO datetime (15 min)"
}

GET /api/checkin/session/{session_id}
Response: CheckinSession object
```

#### 1.3 Patient Identification
```python
# By 6-digit code (sent via SMS/email when booking)
POST /api/checkin/identify/code
Request:
{
    "clinic_id": "string",
    "checkin_code": "123456"
}

# By CURP (Mexican national ID)
POST /api/checkin/identify/curp
Request:
{
    "clinic_id": "string",
    "curp": "GARM850101HDFRRL09"
}

# By name + date of birth
POST /api/checkin/identify/name
Request:
{
    "clinic_id": "string",
    "first_name": "María",
    "last_name": "García Ramírez",
    "date_of_birth": "1985-01-01"
}

# All return:
Response:
{
    "success": true,
    "patient": {
        "patient_id": "uuid",
        "full_name": "María García Ramírez",
        "masked_curp": "GARM****01HDFRRL09"
    },
    "appointment": {
        "appointment_id": "uuid",
        "scheduled_at": "ISO datetime",
        "doctor_name": "Dr. López",
        "appointment_type": "follow_up"
    },
    "pending_actions": [PendingAction, ...]
}
```

#### 1.4 Pending Actions
```python
GET /api/checkin/actions/{appointment_id}
Response:
{
    "actions": [
        {
            "action_id": "uuid",
            "action_type": "pay_copay",
            "status": "pending",
            "title": "Pagar copago",
            "description": "Copago de seguro",
            "is_required": true,
            "is_blocking": true,
            "amount": 150.00,
            "currency": "MXN"
        },
        {
            "action_id": "uuid",
            "action_type": "sign_consent",
            "status": "pending",
            "title": "Firmar consentimiento",
            "document_url": "/documents/consent-form.pdf",
            "is_required": true,
            "is_blocking": false
        }
    ]
}

POST /api/checkin/actions/{action_id}/complete
Request: (varies by action_type)
{
    "signature_data": "base64 (for sign_consent)",
    "payment_intent_id": "stripe_xxx (for pay_copay)",
    "file_id": "uuid (for upload_labs)"
}

POST /api/checkin/actions/{action_id}/skip
# Only for non-required actions
```

#### 1.5 Complete Check-in
```python
POST /api/checkin/complete
Request:
{
    "session_id": "uuid",
    "appointment_id": "uuid",
    "completed_actions": ["action_id_1", "action_id_2"],
    "skipped_actions": ["action_id_3"]
}
Response:
{
    "success": true,
    "checkin_time": "ISO datetime",
    "position_in_queue": 3,
    "estimated_wait_minutes": 15,
    "message": "Te llamaremos por tu nombre"
}
```

#### 1.6 Waiting Room State
```python
GET /api/checkin/waiting-room/{clinic_id}
Response:
{
    "state": {
        "clinic_id": "string",
        "patients_waiting": [
            {
                "patient_id": "uuid",
                "patient_name": "María García",
                "display_name": "María G.",  # Privacy-aware
                "checked_in_at": "ISO datetime",
                "position_in_queue": 1,
                "estimated_wait_minutes": 5,
                "doctor_name": "Dr. López",
                "is_next": true
            }
        ],
        "total_waiting": 3,
        "avg_wait_time_minutes": 12,
        "patients_seen_today": 24,
        "updated_at": "ISO datetime"
    }
}

# WebSocket for real-time updates
WS /api/checkin/waiting-room/{clinic_id}/ws
# Sends WaitingRoomState JSON on each change
```

### Data Models (SQLAlchemy/PostgreSQL)

```python
class Appointment(Base):
    __tablename__ = "appointments"

    appointment_id = Column(UUID, primary_key=True, default=uuid4)
    clinic_id = Column(String, ForeignKey("clinics.clinic_id"), nullable=False)
    patient_id = Column(UUID, ForeignKey("patients.patient_id"), nullable=False)
    doctor_id = Column(UUID, ForeignKey("doctors.doctor_id"), nullable=False)

    # Scheduling
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    estimated_duration = Column(Integer, default=30)  # minutes
    appointment_type = Column(Enum(AppointmentType), nullable=False)

    # Status tracking
    status = Column(Enum(AppointmentStatus), default="scheduled")
    checked_in_at = Column(DateTime(timezone=True), nullable=True)
    called_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Check-in code (6 digits, expires same day)
    checkin_code = Column(String(6), nullable=False)
    checkin_code_expires_at = Column(DateTime(timezone=True), nullable=False)

    # Context
    reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class PendingAction(Base):
    __tablename__ = "pending_actions"

    action_id = Column(UUID, primary_key=True, default=uuid4)
    appointment_id = Column(UUID, ForeignKey("appointments.appointment_id"))

    action_type = Column(Enum(PendingActionType), nullable=False)
    status = Column(Enum(PendingActionStatus), default="pending")

    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    is_required = Column(Boolean, default=False)
    is_blocking = Column(Boolean, default=False)

    # For payments
    amount = Column(Numeric(10, 2), nullable=True)
    currency = Column(String(3), default="MXN")

    # For documents
    document_type = Column(String, nullable=True)
    document_url = Column(String, nullable=True)
    signed_at = Column(DateTime(timezone=True), nullable=True)

    # For uploads
    uploaded_file_id = Column(UUID, nullable=True)

    completed_at = Column(DateTime(timezone=True), nullable=True)
```

---

## MÓDULO 2: TV Content Engine

### Endpoints Existentes (ya implementados, referencia)
```python
GET /api/workflows/aurity/tv-content/list?active_only=true
POST /api/workflows/aurity/waiting-room/generate-tip
POST /api/workflows/aurity/waiting-room/generate-trivia
GET /api/workflows/aurity/clinic-media/list?active_only=true
```

### Nuevos Endpoints para Content por Especialidad
```python
GET /api/content/templates?specialty=dental
Response:
{
    "specialty": "dental",
    "tips": [...],
    "trivia": [...],
    "educational_videos": [...],
    "faq": [...]
}

POST /api/content/generate
Request:
{
    "content_type": "tip" | "trivia" | "faq_answer",
    "specialty": "dental",
    "context": "morning",  # optional
    "language": "es"
}
```

---

## MÓDULO 3: Conversational Engine (Fase 2)

Sistema de chat contextual para cuando el paciente escanea el QR e interactúa.

### Endpoints
```python
POST /api/conversation/start
Request:
{
    "clinic_id": "string",
    "patient_id": "uuid (optional)",
    "appointment_id": "uuid (optional)",
    "channel": "qr_checkin" | "whatsapp" | "web_widget"
}
Response:
{
    "conversation_id": "uuid",
    "context": {...},
    "greeting": "Hola María, ¿en qué puedo ayudarte?"
}

POST /api/conversation/{conversation_id}/message
Request:
{
    "message": "¿Cuánto voy a esperar?",
    "metadata": {...}
}
Response:
{
    "response": "Dr. García está con un paciente, estimo 12 minutos...",
    "suggested_actions": [
        {"type": "view_prep_instructions", "label": "Ver indicaciones"},
        {"type": "reschedule", "label": "Reagendar cita"}
    ],
    "context_updated": true
}

# Intent detection for actions
POST /api/conversation/detect-intent
Request:
{
    "message": "Quiero pagar mi copago"
}
Response:
{
    "intent": "pay_copay",
    "confidence": 0.95,
    "entities": {
        "amount": null  # Will lookup from appointment
    },
    "suggested_action": {
        "type": "initiate_payment",
        "params": {...}
    }
}
```

### Conversation Context Schema
```python
class ConversationContext:
    conversation_id: str
    clinic_id: str
    patient_id: Optional[str]
    appointment_id: Optional[str]

    # Medical context (from patient record)
    specialty: str  # "dental", "general", etc.
    appointment_type: str  # "first_visit", "follow_up"
    pending_actions: List[str]

    # Conversation state
    current_topic: str
    history: List[Message]

    # For LLM
    system_prompt: str  # Generated based on context
```

---

## MÓDULO 4: Integration Hub (Fase 2-3)

### 4.1 Calendar Integration
```python
# Google Calendar OAuth flow
GET /api/integrations/google-calendar/auth
POST /api/integrations/google-calendar/callback

# Sync appointments
POST /api/integrations/google-calendar/sync
GET /api/integrations/google-calendar/availability?doctor_id=xxx&date=2024-01-15
```

### 4.2 Payment Integration (Stripe)
```python
POST /api/payments/create-intent
Request:
{
    "appointment_id": "uuid",
    "action_id": "uuid",
    "amount": 150.00,
    "currency": "MXN"
}
Response:
{
    "client_secret": "pi_xxx_secret_xxx",
    "payment_intent_id": "pi_xxx"
}

POST /api/payments/webhook  # Stripe webhook
```

### 4.3 WhatsApp Integration (Twilio)
```python
POST /api/notifications/whatsapp/send
Request:
{
    "patient_id": "uuid",
    "template": "appointment_reminder",
    "variables": {
        "patient_name": "María",
        "appointment_time": "10:30",
        "doctor_name": "Dr. López",
        "checkin_code": "123456"
    }
}

POST /api/notifications/whatsapp/webhook  # Incoming messages
```

---

## MÓDULO 5: Multi-Tenant Support

### Clinic Management
```python
GET /api/clinics/{clinic_id}
Response:
{
    "clinic_id": "string",
    "name": "Clínica Dental Sonrisa",
    "specialty": "dental",
    "timezone": "America/Mexico_City",
    "branding": {
        "logo_url": "...",
        "primary_color": "#6366f1",
        "welcome_message": "Bienvenido a Clínica Sonrisa"
    },
    "features": {
        "checkin_qr": true,
        "chat_enabled": true,
        "payments_enabled": true,
        "whatsapp_enabled": false
    },
    "subscription": {
        "plan": "professional",
        "valid_until": "2024-12-31"
    }
}

# Feature flags per clinic
GET /api/clinics/{clinic_id}/features
```

### Doctor Management
```python
GET /api/clinics/{clinic_id}/doctors
POST /api/clinics/{clinic_id}/doctors
GET /api/doctors/{doctor_id}/schedule
```

---

## MÓDULO 6: Analytics & KPIs

### Endpoints
```python
GET /api/analytics/clinic/{clinic_id}/dashboard
Response:
{
    "period": "2024-01-01/2024-01-31",
    "engagement": {
        "avg_content_views_per_visit": 4.2,
        "qr_scan_rate": 0.67,  # 67% of visitors scan QR
        "chat_interactions_per_visit": 1.3
    },
    "operational": {
        "avg_wait_time_reduction_pct": 23,
        "no_show_reduction_pct": 18,
        "check_in_time_saved_minutes": 3.5
    },
    "satisfaction": {
        "nps_score": 72,
        "google_reviews_requested": 45,
        "google_reviews_received": 12
    },
    "financial": {
        "copays_collected_via_fi": 15000.00,
        "staff_hours_saved": 40,
        "estimated_monthly_savings": 8500.00
    }
}

GET /api/analytics/clinic/{clinic_id}/realtime
# WebSocket for live dashboard
WS /api/analytics/clinic/{clinic_id}/ws
```

---

## Stack Técnico Recomendado

```yaml
Backend:
  Framework: FastAPI 0.109+
  ORM: SQLAlchemy 2.0+ with asyncpg
  Database: PostgreSQL 15+
  Cache: Redis 7+
  Queue: Celery + Redis (for async tasks)
  WebSockets: FastAPI native / Socket.IO

AI/LLM:
  Provider: Anthropic Claude (via existing FI integration)
  Embeddings: OpenAI text-embedding-3-small (for FAQ search)

Integrations:
  Payments: Stripe Python SDK
  Calendar: Google Calendar API v3
  Messaging: Twilio Python SDK

Infrastructure:
  Deployment: Docker + docker-compose
  On-Premise: Support for air-gapped deployment
  Secrets: HashiCorp Vault / environment variables
```

---

## Prioridades de Implementación

### Sprint 1 (2 semanas) - MVP Check-in
1. ✅ Database models (Appointment, PendingAction, CheckinSession)
2. ✅ QR generation endpoint
3. ✅ Patient identification (3 methods)
4. ✅ Complete check-in flow
5. ✅ Waiting room state + WebSocket

### Sprint 2 (2 semanas) - Multi-tenant + Payments
1. Clinic management CRUD
2. Doctor management
3. Stripe integration for copay payments
4. Check-in code generation on appointment creation

### Sprint 3 (2 semanas) - Notifications + Analytics
1. WhatsApp integration (appointment reminders)
2. Email notifications
3. Basic analytics dashboard
4. Google Calendar sync (optional)

### Sprint 4 (2 semanas) - Conversational AI
1. Conversation engine with context
2. Intent detection
3. Action execution from chat
4. FAQ with semantic search

---

## Frontend Reference

El frontend ya está implementado en Next.js. Revisa estos archivos para entender la estructura de datos esperada:

```
types/checkin.ts          # TypeScript types (match these exactly)
lib/api/checkin.ts        # API client (endpoints to implement)
components/checkin/       # UI components
app/checkin/page.tsx      # Check-in page
app/dashboard/page.tsx    # TV display with QR
```

---

## Testing

Cada endpoint debe tener:
1. Unit tests con pytest
2. Integration tests con TestClient
3. Mock data fixtures para demos

```python
# Example test
def test_identify_by_code():
    response = client.post("/api/checkin/identify/code", json={
        "clinic_id": "test-clinic",
        "checkin_code": "123456"
    })
    assert response.status_code == 200
    assert response.json()["success"] == True
    assert "patient" in response.json()
    assert "appointment" in response.json()
```

---

## Notas Importantes

1. **HIPAA Compliance**: Todos los datos de pacientes deben estar encriptados at-rest y in-transit
2. **Audit Trail**: Loggear todas las acciones de check-in para compliance
3. **Rate Limiting**: Implementar rate limiting en identificación (prevenir brute force de códigos)
4. **CURP Validation**: Validar formato de CURP antes de buscar en DB
5. **Timezone Handling**: Todas las fechas en UTC, convertir a timezone de clínica en respuestas
6. **Soft Deletes**: Usar soft deletes para appointments y patients
7. **WebSocket Auth**: Validar clinic_id en WebSocket connections

---

¿Preguntas? El frontend está listo para consumir estos endpoints. ¡A construir!
