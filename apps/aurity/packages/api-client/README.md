# @aurity-standalone/api-client

Type-safe HTTP client for Aurity backend API.

## Installation

```bash
pnpm add @aurity-standalone/api-client
```

## Usage

```typescript
import { chatWithAssistant, getPersonas, fetchLLMModels } from '@aurity-standalone/api-client';

// Chat with AI assistant
const response = await chatWithAssistant({
  message: '¿Cómo puedo ayudarte?',
  sessionId: 'session-123',
  context: { phase: 'welcome' }
});

// Fetch personas
const personas = await getPersonas();

// Get LLM models
const models = await fetchLLMModels();
```

## Specific Imports

```typescript
import { chatWithAssistant } from '@aurity-standalone/api-client/assistant';
import { getPersonas } from '@aurity-standalone/api-client/personas';
import { fetchLLMModels } from '@aurity-standalone/api-client/llm-models';
```

## API Base URL

Set via environment variable:

```bash
NEXT_PUBLIC_BACKEND_URL=https://api.aurity.io
```

Defaults to `http://localhost:7001` in development.

## Features

- ✅ Type-safe requests and responses
- ✅ Automatic error handling
- ✅ SSE (Server-Sent Events) support for streaming
- ✅ Mock backend for offline development
- ✅ AbortController support for cancellation
- ✅ HIPAA-compliant (no PHI in logs)

## Available Modules

- **assistant** - Chat with AI assistant
- **personas** - AI persona management
- **llm-models** - LLM model configuration
- **knowledge** - Knowledge base documents
- **checkin** - Patient check-in & appointments
- **chat-history** - Conversation history
- **timeline** - Patient timeline events
- **kpis** - Dashboard KPIs
- **medical-workflow** - SOAP notes & medical AI
- **exports** - Evidence pack exports
- **backend-health** - Health check endpoints

## License

MIT
