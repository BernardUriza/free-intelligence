import { useCallback, useEffect, useState } from 'react';
import type { ConversationLibrary } from '@free-intelligence/core';
import { migrateConversationLibrary } from './migrateConversationLibrary';

export type CloudSyncStatus = 'local' | 'connecting' | 'cloud' | 'unreachable';

export interface UseCloudConversationLibraryOptions {
  local: ConversationLibrary;
  remote: ConversationLibrary;
  enabled: boolean;
  scopeKey: string | null;
  retryDelaysMs?: readonly number[];
  slowAfterMs?: number;
}

export interface CloudConversationLibraryState {
  library: ConversationLibrary;
  status: CloudSyncStatus;
  slow: boolean;
  retry: () => void;
}

const DEFAULT_RETRY_DELAYS_MS = [5_000, 15_000, 30_000, 60_000] as const;
const DEFAULT_SLOW_AFTER_MS = 4_000;

/**
 * Hands a shell its conversation store while the cloud one is reached: local until the
 * local→cloud migration settles, then remote; an unreachable server retries with backoff.
 *
 * @returns `status` tells the UI the truth about where writes land right now; `slow` flips
 * when connecting outlasts `slowAfterMs` (a scale-to-zero cold start); `retry` reconnects now.
 */
export function useCloudConversationLibrary({
  local,
  remote,
  enabled,
  scopeKey,
  retryDelaysMs = DEFAULT_RETRY_DELAYS_MS,
  slowAfterMs = DEFAULT_SLOW_AFTER_MS,
}: UseCloudConversationLibraryOptions): CloudConversationLibraryState {
  const [settledFor, setSettledFor] = useState<string | null>(null);
  const [failedFor, setFailedFor] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [slow, setSlow] = useState(false);

  const active = enabled && scopeKey !== null;
  const settled = active && settledFor === scopeKey;
  const failed = active && !settled && failedFor === scopeKey;

  useEffect(() => {
    if (!active || settled) return;
    let cancelled = false;
    setSlow(false);
    const slowTimer = setTimeout(() => {
      if (!cancelled) setSlow(true);
    }, slowAfterMs);
    void (async () => {
      try {
        await migrateConversationLibrary(local, remote);
        // A second pass carries whatever was written locally while the first one waited.
        await migrateConversationLibrary(local, remote);
        if (cancelled) return;
        setFailedFor(null);
        setSettledFor(scopeKey);
      } catch (error) {
        if (cancelled) return;
        console.error('fi-glass: cloud conversation store unreachable, staying local', error);
        setFailedFor(scopeKey);
      } finally {
        clearTimeout(slowTimer);
        if (!cancelled) setSlow(false);
      }
    })();
    return () => {
      cancelled = true;
      clearTimeout(slowTimer);
    };
  }, [active, settled, scopeKey, local, remote, attempt, slowAfterMs]);

  const [failures, setFailures] = useState(0);
  useEffect(() => {
    if (!failed) return;
    const delay = retryDelaysMs[Math.min(failures, retryDelaysMs.length - 1)];
    const timer = setTimeout(() => {
      setFailures((n) => n + 1);
      setAttempt((n) => n + 1);
    }, delay);
    return () => clearTimeout(timer);
  }, [failed, failures, retryDelaysMs]);

  useEffect(() => {
    if (settled) setFailures(0);
  }, [settled]);

  const retry = useCallback(() => {
    setFailedFor(null);
    setFailures(0);
    setAttempt((n) => n + 1);
  }, []);

  if (!active) return { library: local, status: 'local', slow: false, retry };
  if (settled) return { library: remote, status: 'cloud', slow: false, retry };
  return { library: local, status: failed ? 'unreachable' : 'connecting', slow, retry };
}
