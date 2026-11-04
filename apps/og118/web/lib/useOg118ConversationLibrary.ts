'use client';

/**
 * useOg118ConversationLibrary — cloud-authoritative conversations (CONV-CLOUD-1).
 *
 * Signed-in account (auth0 mode, token ready) → the SERVER store is the source
 * of truth (fi-glass RemoteConversationLibrary over /conversations); bearer /
 * unauthenticated stays on the identity-scoped IndexedDB. The handover itself —
 * migration, the connecting/unreachable states, retry with backoff — is fi-glass's
 * `useCloudConversationLibrary`; og118 only supplies its endpoint and auth headers.
 */

import { useMemo } from 'react';
import {
  RemoteConversationLibrary,
  useCloudConversationLibrary,
  useIndexedDBConversationLibrary,
  type CloudConversationLibraryState,
} from 'fi-glass/conversation';
import { authHeaders } from './og118Token';

const API = process.env.NEXT_PUBLIC_OG118_API ?? 'http://localhost:8118';

export type Og118ConversationLibrary = CloudConversationLibraryState;

export function useOg118ConversationLibrary(
  userId: string | null,
  tokenReady: boolean,
): Og118ConversationLibrary {
  const local = useIndexedDBConversationLibrary(userId);
  const remote = useMemo(
    () => new RemoteConversationLibrary({ baseUrl: API, headers: authHeaders }),
    [],
  );
  return useCloudConversationLibrary({
    local,
    remote,
    enabled: tokenReady,
    scopeKey: userId,
  });
}
