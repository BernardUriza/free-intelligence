# @aurity-standalone/observability

HIPAA-compliant observability utilities for Aurity healthcare platform. Provides safe logging, telemetry, and monitoring without exposing PHI/PII.

## Installation

```bash
npm install @aurity-standalone/observability
# or
pnpm add @aurity-standalone/observability
# or
yarn add @aurity-standalone/observability
```

## Usage

```typescript
import { 
  sanitizeMessagePreview, 
  hash8, 
  createTelemetryContext,
  type TelemetryIds 
} from '@aurity-standalone/observability';

// Safe logging of user messages
const userMessage = "Patient John Doe has diabetes";
const safe = sanitizeMessagePreview(userMessage, 20);
console.log(safe); // "Patient John Doe has"

// Create short hashes for IDs
const sessionHash = hash8('session_12345');
console.log(sessionHash); // "a4b3c2d1"

// Create telemetry context
const context = createTelemetryContext({
  request_id: 'req_123',
  session_id: 'session_456'
});
```

## HIPAA Compliance

⚠️ **NEVER** log these fields in plaintext:
- Patient names, emails, phone numbers
- Medical records, diagnoses, treatments
- Full session transcripts or conversation history
- Any personally identifiable information (PII)
- Any protected health information (PHI)

✅ **SAFE** to log:
- Hashed identifiers (using `hash8`)
- Truncated previews (using `sanitizeMessagePreview`)
- Session IDs, request IDs (without patient info)
- Performance metrics, error codes
- System state, configuration changes

## API Reference

### Functions

#### `sanitizeMessagePreview(input, max?): string`
Truncate input to prevent logging sensitive data.

#### `hash8(input): string`
Generate 8-character hash for short identifiers.

#### `createTelemetryContext(ids): Record<string, string>`
Create safe telemetry context for distributed tracing.

#### `measureAsync<T>(label, fn): Promise<{ result: T, duration: number }>`
Measure execution time of async operations.

#### `formatBytes(bytes): string`
Format file size for human-readable display.

## License

MIT © Aurity Team
