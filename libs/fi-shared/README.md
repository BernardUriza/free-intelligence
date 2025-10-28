# @fi/shared

Shared TypeScript types, models, and API client for the **Free Intelligence** monorepo.

## Purpose

This package provides a **single source of truth** for types and models shared between:

- **FI Backend** (Python/FastAPI) - Event sourcing, HDF5 storage
- **AURITY Frontend** (Next.js/React) - UI framework

## Architecture Context

```
free-intelligence/               # Monorepo
├── backend/                     # 🎯 FI Backend (Python)
│   ├── fi_consult_service.py
│   └── fi_event_store.py
├── libs/
│   └── fi-shared/              # 🎯 Shared types (TypeScript)
│       ├── types/events.ts
│       ├── models/consultation.ts
│       └── api/fi-client.ts
└── apps/
    └── aurity/                 # 🎯 AURITY Frontend (Next.js)
        ├── aurity/             # Framework core
        └── app/                # UI (uses @fi/shared)
```

**FI** and **AURITY** are **peer frameworks**:
- **FI** = Backend framework (event sourcing, Python, HDF5)
- **AURITY** = Frontend framework (UI, React, TypeScript)
- **@fi/shared** = Bridge between them

## Installation

In your app (e.g., AURITY):

```bash
pnpm add @fi/shared
```

Or use workspace references in `package.json`:

```json
{
  "dependencies": {
    "@fi/shared": "workspace:*"
  }
}
```

## Usage

### Import types

```typescript
import {
  MessageRole,
  UrgencyLevel,
  ConsultationState,
  SOAPNote,
} from '@fi/shared';
```

### Use API client

```typescript
import { createFIClient } from '@fi/shared';

const fiClient = createFIClient({
  baseUrl: 'http://localhost:7001',
});

// Start consultation
const { consultation_id } = await fiClient.startConsultation({
  patient_id: 'patient-001',
  user_id: 'dr-bernard',
});

// Append event
await fiClient.appendEvent(consultation_id, {
  event_type: 'MESSAGE_RECEIVED',
  data: {
    message: {
      role: 'user',
      content: 'I have a headache',
      timestamp: new Date().toISOString(),
    },
  },
});

// Get state
const { consultation } = await fiClient.getConsultation(consultation_id);
console.log(consultation.messages);
```

## Package Structure

```
libs/fi-shared/
├── src/
│   ├── types/
│   │   └── events.ts           # Domain events (12 event types)
│   ├── models/
│   │   └── consultation.ts     # Consultation state, SOAP note, API types
│   ├── api/
│   │   └── fi-client.ts        # FIClient class + factory
│   └── index.ts                # Barrel exports
├── package.json
├── tsconfig.json
└── README.md
```

## Event Types

All domain events extend `DomainEvent`:

```typescript
interface DomainEvent {
  event_type: string;
  timestamp: string; // ISO 8601
  consultation_id: string;
  metadata?: Record<string, unknown>;
}
```

**Available events:**

1. `CONSULTATION_STARTED`
2. `MESSAGE_RECEIVED`
3. `EXTRACTION_STARTED`
4. `EXTRACTION_COMPLETED`
5. `DEMOGRAPHICS_UPDATED`
6. `SYMPTOMS_UPDATED`
7. `URGENCY_CLASSIFIED`
8. `SOAP_GENERATION_STARTED`
9. `SOAP_SECTION_COMPLETED`
10. `SOAP_GENERATION_COMPLETED`
11. `CRITICAL_PATTERN_DETECTED`
12. `CONSULTATION_COMMITTED`

## Models

### ConsultationState

Full consultation state (reconstructed from events):

```typescript
interface ConsultationState {
  consultation_id: string;
  patient_id: string;
  user_id: string;
  started_at: string;
  messages: Message[];
  demographics?: Demographics;
  symptoms: Symptom[];
  urgency_assessment?: UrgencyAssessment;
  soap_note?: SOAPNote;
  committed: boolean;
  audit_hash?: string;
}
```

### SOAPNote

NOM-004-SSA3-2012 compliant SOAP note:

```typescript
interface SOAPNote {
  subjective: string;
  objective: string;
  assessment: string;
  plan: string;
  generated_at: string;
  version: number;
}
```

## API Client

### FIClient

TypeScript client for FI Consult Service:

```typescript
class FIClient {
  startConsultation(request: StartConsultationRequest): Promise<StartConsultationResponse>;
  appendEvent(consultationId: string, request: AppendEventRequest): Promise<AppendEventResponse>;
  getConsultation(consultationId: string): Promise<GetConsultationResponse>;
  getSOAP(consultationId: string): Promise<GetSOAPResponse>;
  getEvents(consultationId: string): Promise<GetEventsResponse>;
  healthCheck(): Promise<{ status: string; service: string }>;
}
```

### Factory

```typescript
createFIClient(config?: Partial<FIClientConfig>): FIClient
```

Defaults:
- `baseUrl`: `process.env.FI_API_URL` or `http://localhost:7001`
- `timeout`: `30000` ms

## Development

```bash
# Type check
pnpm type-check

# Build
pnpm build

# Lint
pnpm lint
```

## Version

- **0.3.0** - Initial release with consultation types and API client

## License

MIT - Bernard Uriza Orozco
