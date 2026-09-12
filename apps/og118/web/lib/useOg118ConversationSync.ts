'use client';

/**
 * useOg118ConversationSync — pull server-side appends into the open thread.
 *
 * A background worker can append an assistant message to the cloud record
 * while the tab is open; nothing pushes that to the browser. This hook asks
 * the library to re-read the active record (a no-op when `updatedAt` did not
 * move) when the tab comes back (visibility/focus) and every `intervalMs`
 * while it is visible. Only meaningful in cloud mode — IndexedDB has no other
 * writer — and never while a turn is streaming, so the fold is never raced.
 */

import { useEffect, useRef } from 'react';

export const OG118_CONVERSATION_SYNC_MS = 15_000;

export interface Og118ConversationSyncOptions {
  /** Cloud mode only: a single-writer local store has nothing to pull. */
  enabled: boolean;
  /** A streaming turn owns the thread; polling waits for it to settle. */
  streaming: boolean;
  reloadActive: () => Promise<void>;
  intervalMs?: number;
}

export function useOg118ConversationSync({
  enabled,
  streaming,
  reloadActive,
  intervalMs = OG118_CONVERSATION_SYNC_MS,
}: Og118ConversationSyncOptions): void {
  // Read through refs so a new reloadActive identity (it closes over the active
  // record) or a streaming flip never re-arms the interval.
  const reloadRef = useRef(reloadActive);
  reloadRef.current = reloadActive;
  const streamingRef = useRef(streaming);
  streamingRef.current = streaming;

  useEffect(() => {
    if (!enabled || typeof document === 'undefined') return;
    let inFlight = false;
    const pull = () => {
      if (document.hidden || streamingRef.current || inFlight) return;
      inFlight = true;
      reloadRef.current()
        .catch((e) => console.error('[og118] conversation sync failed', e))
        .finally(() => {
          inFlight = false;
        });
    };
    const onVisible = () => {
      if (!document.hidden) pull();
    };
    document.addEventListener('visibilitychange', onVisible);
    window.addEventListener('focus', pull);
    const timer = setInterval(pull, intervalMs);
    return () => {
      document.removeEventListener('visibilitychange', onVisible);
      window.removeEventListener('focus', pull);
      clearInterval(timer);
    };
  }, [enabled, intervalMs]);
}
