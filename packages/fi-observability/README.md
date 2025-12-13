# @aurity/fi-observability

PHI-safe telemetry helpers for AURITY MVP.

## Helpers
- `sanitizeMessagePreview(input, max)` — truncates to `max` chars; avoids logging raw PHI.
- `hash8(input)` — compact hash for diagnostics (lengths/hashes, no raw content).

## Usage
```ts
import { sanitizeMessagePreview, hash8 } from '@aurity/fi-observability';

const preview = sanitizeMessagePreview(userInput, 60);
console.log('telemetry', { message_len: userInput.length, preview_hash8: hash8(preview) });

// Streamed updates
onContent?.(sanitizeMessagePreview(delta, 10_000));
```

Guidelines:
- Log lengths and `hash8`, never raw content.
- Cap previews reasonably (e.g., 60 chars for meta, 10k for UI buffers).
- Do not store `thinking` content in logs/analytics.