/**
 * useChatSync Hook
 *
 * Handles storage loading, backend sync, and WebSocket real-time sync.
 * SOLID: Single Responsibility - only synchronization logic.
 */

import { useEffect, useMemo } from 'react';
import { mergeMessages, areMessagesEqual } from '@/lib/chat/sync';
import { createMessageStorage } from '@/lib/chat/storage';
import { BackendSyncStrategy, WebSocketSyncStrategy } from '@/lib/chat/sync-strategy';
import type { FIMessage, OnboardingPhase } from '@aurity-standalone/types/assistant';
import type { IMessageStorage } from '@/lib/chat/storage';
import type { IBackendSync, IRealtimeSync } from '@/lib/chat/sync-strategy';
import { INITIAL_MESSAGES_LIMIT, isConnectionError } from './utils';
import { createLogger } from '@/lib/internal/logger';

const log = createLogger('ChatSync');

export interface UseChatSyncOptions {
  storageKey?: string;
  doctorId?: string;
  phase?: OnboardingPhase;
  loadingInitial: boolean;

  // Dependency injection
  injectedStorage?: IMessageStorage;
  injectedBackendSync?: IBackendSync;
  injectedRealtimeSync?: IRealtimeSync;

  // State setters
  setMessages: React.Dispatch<React.SetStateAction<FIMessage[]>>;
  setLoadingInitial: React.Dispatch<React.SetStateAction<boolean>>;
  setIsTyping: React.Dispatch<React.SetStateAction<boolean>>;
  setHasMoreMessages: React.Dispatch<React.SetStateAction<boolean>>;
  olderMessagesBufferRef: React.MutableRefObject<FIMessage[]>;
}

export interface UseChatSyncReturn {
  storage: IMessageStorage;
  backendSync: IBackendSync;
  realtimeSync: IRealtimeSync;
}

export function useChatSync({
  storageKey,
  doctorId,
  phase,
  loadingInitial,
  injectedStorage,
  injectedBackendSync,
  injectedRealtimeSync,
  setMessages,
  setLoadingInitial,
  setIsTyping,
  setHasMoreMessages,
  olderMessagesBufferRef,
}: UseChatSyncOptions): UseChatSyncReturn {
  // Memoize strategies (SOLID: Dependency Inversion)
  const storage = useMemo(
    () => injectedStorage || createMessageStorage(!!storageKey),
    [injectedStorage, storageKey]
  );

  const backendSync = useMemo(
    () => injectedBackendSync || new BackendSyncStrategy(),
    [injectedBackendSync]
  );

  const realtimeSync = useMemo(
    () => injectedRealtimeSync || new WebSocketSyncStrategy(),
    [injectedRealtimeSync]
  );

  // ========================================================================
  // LocalStorage Load
  // ========================================================================
  useEffect(() => {
    if (storageKey) {
      const loaded = storage.load(storageKey);
      if (loaded.length > 0) {
        const deduped = mergeMessages(loaded, []);
        log.debug('Storage loaded', { loaded: loaded.length, deduped: deduped.length });

        if (deduped.length > INITIAL_MESSAGES_LIMIT) {
          const visibleMessages = deduped.slice(-INITIAL_MESSAGES_LIMIT);
          const olderMessages = deduped.slice(0, -INITIAL_MESSAGES_LIMIT);

          olderMessagesBufferRef.current = olderMessages;
          setMessages(visibleMessages);
          setHasMoreMessages(true);
        } else {
          olderMessagesBufferRef.current = [];
          setMessages(deduped);
          setHasMoreMessages(false);
        }

        if (deduped.length !== loaded.length) {
          storage.save(storageKey, deduped);
        }
      }
    }

    setLoadingInitial(false);
    setIsTyping(false);
  }, [storageKey, storage, setMessages, setLoadingInitial, setIsTyping, setHasMoreMessages, olderMessagesBufferRef]);

  // ========================================================================
  // Backend Sync (periodic)
  // ========================================================================
  useEffect(() => {
    if (!doctorId || !storageKey) return;

    const syncWithBackend = async () => {
      try {
        const backendMessages = await backendSync.sync(doctorId, phase, 50);
        if (backendMessages.length === 0) return;

        setMessages(prevMessages => {
          const allLocalMessages = [...olderMessagesBufferRef.current, ...prevMessages];
          const merged = mergeMessages(allLocalMessages, backendMessages);

          if (areMessagesEqual(allLocalMessages, merged)) {
            return prevMessages;
          }

          if (storageKey) {
            storage.save(storageKey, merged);
          }

          if (merged.length > INITIAL_MESSAGES_LIMIT) {
            const visibleMessages = merged.slice(-INITIAL_MESSAGES_LIMIT);
            const olderMessages = merged.slice(0, -INITIAL_MESSAGES_LIMIT);
            olderMessagesBufferRef.current = olderMessages;
            setHasMoreMessages(true);
            return visibleMessages;
          }

          olderMessagesBufferRef.current = [];
          return merged;
        });
      } catch (err) {
        if (!isConnectionError(err)) {
          log.error('Backend sync failed', { error: String(err) });
        }
      }
    };

    const initialTimeoutId = setTimeout(syncWithBackend, 100);
    const periodicIntervalId = setInterval(syncWithBackend, 30000);

    return () => {
      clearTimeout(initialTimeoutId);
      clearInterval(periodicIntervalId);
    };
  }, [doctorId, storageKey, phase, backendSync, storage, setMessages, setHasMoreMessages, olderMessagesBufferRef]);

  // ========================================================================
  // WebSocket Real-time Sync
  // ========================================================================
  useEffect(() => {
    const enabled = !!doctorId && !!storageKey;
    if (!enabled || loadingInitial) return;

    log.debug('WebSocket connecting');

    realtimeSync.connect(doctorId, (message) => {

      setMessages(prev => {
        const exists = prev.some(m => {
          if (message.metadata?.id && m.metadata?.id) {
            return m.metadata.id === message.metadata.id;
          }
          return m.role === message.role && m.content.trim() === message.content.trim();
        });

        if (exists) return prev;
        return [...prev, message];
      });
    });

    return () => {
      realtimeSync.disconnect();
    };
  }, [doctorId, storageKey, realtimeSync, loadingInitial, setMessages]);

  return { storage, backendSync, realtimeSync };
}
