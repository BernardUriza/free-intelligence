/**
 * usePagination Hook
 *
 * Handles infinite scroll pagination for loading older messages.
 * SOLID: Single Responsibility - only pagination logic.
 */

import { useState, useCallback } from 'react';
import type { FIMessage, OnboardingPhase } from '@aurity-standalone/types/assistant';
import type { IBackendSync } from '@/lib/chat/sync-strategy';
import { INITIAL_MESSAGES_LIMIT, deduplicateMessages } from './utils';
import { createLogger } from '@/lib/internal/logger';

const log = createLogger('Chat:Pagination');

export interface UsePaginationOptions {
  doctorId?: string;
  phase?: OnboardingPhase;
  backendSync: IBackendSync;

  // State setters
  setMessages: React.Dispatch<React.SetStateAction<FIMessage[]>>;
  setError: React.Dispatch<React.SetStateAction<string | null>>;
  olderMessagesBufferRef: React.MutableRefObject<FIMessage[]>;
}

export interface UsePaginationReturn {
  loadingOlder: boolean;
  hasMoreMessages: boolean;
  setHasMoreMessages: React.Dispatch<React.SetStateAction<boolean>>;
  paginationOffset: number;
  setPaginationOffset: React.Dispatch<React.SetStateAction<number>>;
  loadOlderMessages: () => Promise<void>;
}

export function usePagination({
  doctorId,
  phase,
  backendSync,
  setMessages,
  setError,
  olderMessagesBufferRef,
}: UsePaginationOptions): UsePaginationReturn {
  const [loadingOlder, setLoadingOlder] = useState(false);
  const [hasMoreMessages, setHasMoreMessages] = useState(true);
  const [paginationOffset, setPaginationOffset] = useState(0);

  const loadOlderMessages = useCallback(async (): Promise<void> => {
    if (loadingOlder || !hasMoreMessages) return;

    setLoadingOlder(true);

    try {
      // STEP 1: Check local buffer first
      if (olderMessagesBufferRef.current.length > 0) {
        const bufferChunk = olderMessagesBufferRef.current.slice(-INITIAL_MESSAGES_LIMIT);
        const remaining = olderMessagesBufferRef.current.slice(0, -INITIAL_MESSAGES_LIMIT);

        setMessages(prev => {
          const newMessages = deduplicateMessages(prev, bufferChunk);
          return [...newMessages, ...prev];
        });

        olderMessagesBufferRef.current = remaining;
        log.debug('From buffer', { loaded: bufferChunk.length, remaining: remaining.length });

        if (remaining.length === 0 && doctorId) {
          setHasMoreMessages(true); // May have more on backend
        } else if (remaining.length === 0) {
          setHasMoreMessages(false);
        }

        return;
      }

      // STEP 2: Buffer exhausted, load from backend
      if (!doctorId) {
        setHasMoreMessages(false);
        return;
      }

      const result = await backendSync.loadOlder(doctorId, phase, paginationOffset, 50);

      setMessages(prev => {
        const newMessages = deduplicateMessages(prev, result.messages);
        log.debug('Backend returned', { fetched: result.messages.length, new: newMessages.length });

        if (newMessages.length === 0) {
          setHasMoreMessages(false);
          return prev;
        }

        return [...newMessages, ...prev];
      });

      setPaginationOffset(prev => prev + result.messages.length);
      setHasMoreMessages(result.hasMore);
    } catch (err) {
      log.error('Failed to load older messages', { error: String(err) });
      setError(err instanceof Error ? err.message : 'Failed to load history');
    } finally {
      setLoadingOlder(false);
    }
  }, [loadingOlder, hasMoreMessages, doctorId, paginationOffset, phase, backendSync, setMessages, setError, olderMessagesBufferRef]);

  return {
    loadingOlder,
    hasMoreMessages,
    setHasMoreMessages,
    paginationOffset,
    setPaginationOffset,
    loadOlderMessages,
  };
}
