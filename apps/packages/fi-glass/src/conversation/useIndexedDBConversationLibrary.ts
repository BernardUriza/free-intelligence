'use client';

/**
 * useIndexedDBConversationLibrary — an identity-scoped conversation store.
 *
 * Returns an `IndexedDBConversationLibrary` whose database is partitioned by the
 * authenticated identity (the auth principal's `sub`), memoized so the instance
 * is stable per identity. When the identity changes (a different account signs in
 * on the same browser), a NEW instance with a different database name is returned,
 * which makes `useConversationLibrary` re-hydrate from THAT account's transcripts
 * instead of leaking the previous account's. A null identity (no auth / legacy
 * single-tenant) keeps the original shared database, so existing data survives.
 *
 * This is the framework answer to the og118 shared-device leak (the canary):
 * every shell that signs users in gets per-identity transcript isolation for free.
 */

import { useMemo } from 'react';

import { scopedStoreName } from '../identity/scopedStore';
import {
  IndexedDBConversationLibrary,
  type IndexedDBConversationLibraryOptions,
} from './IndexedDBConversationLibrary';

const BASE_DB_NAME = 'free-intelligence-conversations';

export function useIndexedDBConversationLibrary(
  identityKey: string | null | undefined,
  options: Omit<IndexedDBConversationLibraryOptions, 'dbName'> = {},
): IndexedDBConversationLibrary {
  const { storeName } = options;
  return useMemo(
    () =>
      new IndexedDBConversationLibrary({
        dbName: scopedStoreName(BASE_DB_NAME, identityKey),
        storeName,
      }),
    [identityKey, storeName],
  );
}
