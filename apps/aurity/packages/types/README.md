# @aurity-standalone/types

TypeScript type definitions for Aurity healthcare platform.

## Installation

```bash
pnpm add @aurity-standalone/types
```

## Usage

Import specific type modules:

```typescript
import type { Appointment, CheckinSession } from '@aurity-standalone/types/checkin';
import type { LLMModel, LLMProvider } from '@aurity-standalone/types/llm';
import type { Patient, Encounter } from '@aurity-standalone/types/medical';
import type { Persona } from '@aurity-standalone/types/persona';
```

Or use the main entry point:

```typescript
import type { Appointment, Patient, LLMModel } from '@aurity-standalone/types';
```

## Available Type Modules

- **assistant** - FI assistant types (tone, onboarding, chat context)
- **audit** - Audit log and event types
- **chat** - Chat hook interface and message types
- **checkin** - Patient check-in, appointments, waiting room
- **knowledge** - Knowledge base and documentation types
- **llm** - LLM model configuration and provider types
- **medical** - Patient, encounters, clinical notes, orders
- **patient** - Patient demographics and medical history
- **persona** - AI persona configuration and management
- **session** - Recording session metadata and transcription
- **voices** - TTS voice configuration

## Type Safety

All types follow strict TypeScript guidelines:
- No `any` types
- Comprehensive union types for status fields
- ISO 8601 date strings
- Optional fields clearly marked with `?`

## HIPAA Compliance

These types support HIPAA-compliant data handling:
- No PHI/PII in log-safe types
- Separate types for sanitized vs full patient data
- Audit trail metadata types

## Development

```bash
# Type check
pnpm tsc --noEmit

# Build (if needed for npm publishing)
pnpm tsc
```

## License

MIT
