'use client';

/**
 * useAudioQueueStore — an identity-scoped durable audio queue.
 *
 * Returns an `AudioQueueStore` whose IndexedDB database is partitioned by the
 * authenticated identity (the auth principal's `sub`), memoized so the instance is
 * stable per identity. A different account signing in on the same browser gets a
 * different database — so one user's recorded audio drafts never surface in
 * another user's queue. A null identity keeps the original shared database.
 *
 * The audio-queue twin of `useIndexedDBConversationLibrary`: both close the
 * og118 shared-device leak by scoping the local store to the signed-in account.
 */

import { useMemo } from 'react';

import { scopedStoreName } from '../identity/scopedStore';
import { AudioQueueStore, type AudioQueueStoreOptions } from './AudioQueueStore';

const BASE_DB_NAME = 'free-intelligence-audio-queue';

export function useAudioQueueStore(
  identityKey: string | null | undefined,
  options: Omit<AudioQueueStoreOptions, 'dbName'> = {},
): AudioQueueStore {
  const { storeName } = options;
  return useMemo(
    () =>
      new AudioQueueStore({
        dbName: scopedStoreName(BASE_DB_NAME, identityKey),
        storeName,
      }),
    [identityKey, storeName],
  );
}
