---
applyTo: "apps/**/*.ts,apps/**/*.tsx"
---

# TypeScript Frontend Instructions - AURITY

## Architecture

### Three-Layer Compliance
```typescript
// ✅ CORRECT - Only call PUBLIC endpoints
const response = await fetch('/api/workflows/aurity/sessions', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(data)
});

// ❌ FORBIDDEN - Never call INTERNAL endpoints
const response = await fetch('/api/internal/sessions', { // BUG!
  method: 'POST'
});
```

### Environment Configuration
```typescript
// Use environment variables
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:7001';

// Build URLs properly
const endpoint = `${BACKEND_URL}/api/workflows/aurity/sessions`;
```

## Import Style

### Absolute Imports Only
```typescript
// ✅ CORRECT - Absolute imports
import { SessionService } from '@/services/session';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/hooks/useAuth';

// ❌ WRONG - Relative imports
import { SessionService } from '../../../services/session';
import { Button } from '../../components/ui/button';
```

## API Communication

### Proper Error Handling
```typescript
async function createSession(data: SessionData): Promise<SessionResponse> {
  try {
    const response = await fetch('/api/workflows/aurity/sessions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${getToken()}`
      },
      body: JSON.stringify(data)
    });

    // Check HTTP status
    if (!response.ok) {
      const error = await response.json();
      throw new Error(`HTTP ${response.status}: ${error.detail || 'Unknown error'}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Session creation failed', error);
    // Re-throw for caller to handle
    throw error;
  }
}
```

### AbortController for Cleanup
```typescript
import { useEffect, useState } from 'react';

function useSession(sessionId: string) {
  const [session, setSession] = useState(null);

  useEffect(() => {
    const controller = new AbortController();

    async function fetchSession() {
      try {
        const response = await fetch(
          `/api/workflows/aurity/sessions/${sessionId}`,
          { signal: controller.signal }
        );
        const data = await response.json();
        setSession(data);
      } catch (error) {
        if (error.name !== 'AbortError') {
          console.error('Failed to fetch session', error);
        }
      }
    }

    fetchSession();

    // Cleanup on unmount
    return () => controller.abort();
  }, [sessionId]);

  return session;
}
```

## React Patterns

### Proper Hook Usage
```typescript
// ✅ CORRECT - Cleanup and dependencies
useEffect(() => {
  const subscription = subscribeToUpdates(sessionId);

  return () => {
    subscription.unsubscribe();
  };
}, [sessionId]);

// ❌ WRONG - Missing cleanup
useEffect(() => {
  subscribeToUpdates(sessionId);
  // Memory leak - no cleanup
}, [sessionId]);

// ❌ WRONG - Missing dependencies
useEffect(() => {
  fetchData(sessionId);
}, []); // Should include sessionId
```

### State Management
```typescript
import { useState, useCallback } from 'react';

function SessionManager() {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const createSession = useCallback(async (data: SessionData) => {
    setLoading(true);
    setError(null);

    try {
      const result = await SessionAPI.create(data);
      setSession(result);
      return result;
    } catch (err) {
      setError(err as Error);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return { session, loading, error, createSession };
}
```

## Type Safety

### Strict Types
```typescript
// ✅ CORRECT - Explicit types
interface SessionRequest {
  session_id: string;
  user_id: string;
  metadata?: Record<string, unknown>;
}

interface SessionResponse {
  session_id: string;
  status: 'active' | 'completed' | 'error';
  created_at: string;
}

// ❌ WRONG - Any types
function createSession(data: any): any {
  // No type safety
}
```

### Null Safety
```typescript
// ✅ CORRECT - Handle null/undefined
function displayPatient(patient: Patient | null) {
  if (!patient) {
    return <div>No patient data</div>;
  }

  return <div>{patient.nombre}</div>;
}

// ❌ WRONG - Potential runtime error
function displayPatient(patient: Patient | null) {
  return <div>{patient.nombre}</div>; // Crash if null
}
```

## Security

### Auth Token Handling
```typescript
// ✅ CORRECT - Secure token storage (self-hosted JWT)
import { useAuth } from '@/hooks/useAuth';

function useAuthenticatedFetch() {
  const { getAccessToken } = useAuth();

  return async (url: string, options?: RequestInit) => {
    const token = getAccessToken();

    return fetch(url, {
      ...options,
      headers: {
        ...options?.headers,
        'Authorization': `Bearer ${token}`
      }
    });
  };
}

// ❌ WRONG - Hardcoded token
const token = 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...';
```

### Sanitize User Input
```typescript
// ✅ CORRECT - Validate and sanitize
function SearchInput() {
  const [query, setQuery] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // Sanitize input
    const sanitized = query.trim().slice(0, 100);

    if (sanitized.length < 3) {
      alert('Query too short');
      return;
    }

    performSearch(sanitized);
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        maxLength={100}
      />
    </form>
  );
}
```

## Performance

### Memoization
```typescript
import { useMemo, useCallback } from 'react';

function SessionList({ sessions }: { sessions: Session[] }) {
  // Expensive computation - memoize
  const sortedSessions = useMemo(() => {
    return sessions.sort((a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );
  }, [sessions]);

  // Callback stability
  const handleSelect = useCallback((id: string) => {
    console.log('Selected', id);
  }, []);

  return (
    <ul>
      {sortedSessions.map(session => (
        <li key={session.id} onClick={() => handleSelect(session.id)}>
          {session.name}
        </li>
      ))}
    </ul>
  );
}
```

## Error Boundaries

```typescript
import { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Error boundary caught:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div>Something went wrong. Please refresh the page.</div>
      );
    }

    return this.props.children;
  }
}
```

## Anti-Patterns

1. ❌ Calling `/api/internal/*` endpoints
2. ❌ Using relative imports (`../../../`)
3. ❌ Missing cleanup in `useEffect`
4. ❌ Hardcoded API URLs or tokens
5. ❌ Using `any` type
6. ❌ Not handling loading/error states
7. ❌ Missing `key` prop in lists
8. ❌ Blocking the main thread

## Success Checklist

- [ ] Only calls `/api/workflows/aurity/*` endpoints
- [ ] Uses absolute imports (`@/`)
- [ ] Proper error handling with try/catch
- [ ] Cleanup functions in useEffect
- [ ] Type safety (no `any`)
- [ ] Loading and error states
- [ ] Auth tokens via useAuth hook
- [ ] AbortController for fetch cancellation
