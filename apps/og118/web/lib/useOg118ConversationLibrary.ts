'use client';

/**
 * useOg118ConversationLibrary — cloud-authoritative conversations (CONV-CLOUD-1).
 *
 * Signed-in account (auth0 mode, token ready) → the SERVER store is the source
 * of truth (fi-glass RemoteConversationLibrary over /conversations), so an
 * account's chats follow it across browsers/devices — the same account model as
 * Projects (PROJ-SYNC-1). Unauthenticated / bearer-legacy → the original
 * identity-scoped IndexedDB, unchanged.
 *
 * Handover order matters: the hook keeps returning the LOCAL library until the
 * one-time local→cloud migration settles, THEN flips to remote — so
 * useConversationLibrary re-hydrates from the cloud only after the browser's
 * existing transcripts are up there (no sidebar flash of a half-empty cloud
 * list). Migration is idempotent (copy only what the server lacks, server wins
 * on collision — another device may have written newer); a migration failure
 * (server unreachable) leaves the app on local IndexedDB as the fallback.
 */

import { useEffect, useMemo, useState } from 'react';
import type { ConversationLibrary } from '@free-intelligence/core';
import {
  RemoteConversationLibrary,
  migrateConversationLibrary,
  useIndexedDBConversationLibrary,
} from 'fi-glass/conversation';
import { authHeaders } from './og118Token';

const API = process.env.NEXT_PUBLIC_OG118_API ?? 'http://localhost:8118';

export interface Og118ConversationLibrary {
  library: ConversationLibrary;
  /** True once the SERVER store is the active source of truth (signed in +
   * migration settled) — drives honest storage copy in the UI. */
  cloud: boolean;
}

export function useOg118ConversationLibrary(
  userId: string | null,
  tokenReady: boolean,
): Og118ConversationLibrary {
  const local = useIndexedDBConversationLibrary(userId);
  const remote = useMemo(
    () => new RemoteConversationLibrary({ baseUrl: API, headers: authHeaders }),
    [],
  );
  const [migratedFor, setMigratedFor] = useState<string | null>(null);

  useEffect(() => {
    if (!userId || !tokenReady) return;
    let cancelled = false;
    migrateConversationLibrary(local, remote)
      .then(() => {
        if (!cancelled) setMigratedFor(userId);
      })
      .catch((error) => {
        console.error('og118: conversation cloud migration failed, staying local', error);
      });
    return () => {
      cancelled = true;
    };
  }, [userId, tokenReady, local, remote]);

  const cloud = Boolean(userId && tokenReady && migratedFor === userId);
  return { library: cloud ? remote : local, cloud };
}
