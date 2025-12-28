# @aurity-standalone/hooks

Custom React hooks for Aurity healthcare platform.

## Installation

```bash
pnpm add @aurity-standalone/hooks
```

## Usage

```typescript
import { useAuth, usePersonas, useChat } from '@aurity-standalone/hooks';

function MyComponent() {
  const { user, isAuthenticated, hasRole } = useAuth();
  const { personas, loading } = usePersonas();
  const { messages, sendMessage } = useChat({ phase: 'welcome' });
  
  // ... your component logic
}
```

## Available Hooks

### Authentication & Authorization
- **useAuth** - Auth0 authentication state and utilities
- **useRBAC** - Role-based access control checks

### Chat & AI
- **useChat** - Main chat hook with FI assistant
- **useFIConversation** - FI conversation management
- **useCheckinConversation** - Check-in chat flow
- **useChatUpload** - File upload in chat
- **useMessageGroups** - Group messages by date/speaker
- **useOptimisticMessages** - Optimistic UI for messages
- **useEmotionalContext** - Emotional tone detection

### Personas & Models
- **usePersonas** - AI persona management
- **useLLMModels** - LLM model configuration

### Medical Workflows
- **useRecorder** - Audio recording for consultations
- **useTranscription** - Real-time transcription
- **useSessionPolling** - Session status polling
- **useSOAPNote** - SOAP note generation

### Other
- **useKeyboardShortcuts** - Keyboard shortcuts management
- **useLocalStorage** - Typed localStorage hook
- **useDebounce** - Debounced values
- **useIntersectionObserver** - Intersection observer hook

## Features

- ✅ Type-safe with TypeScript
- ✅ HIPAA-compliant (no PHI in logs)
- ✅ Optimistic UI updates
- ✅ Automatic error handling
- ✅ SSE (Server-Sent Events) support
- ✅ AbortController for cleanup
- ✅ Zustand for state management

## License

MIT
