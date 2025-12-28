/**
 * useChat Hook
 *
 * Main chat hook that composes all sub-hooks following SOLID principles.
 * Renamed from useFIConversation for brevity and clarity.
 *
 * Architecture:
 * - useMessageState: Core state management
 * - useChatSync: Storage + backend + WebSocket sync
 * - useChatActions: send, intro, retry, clear
 * - usePagination: Infinite scroll
 *
 * @example
 * ```tsx
 * const { messages, sendMessage, isTyping } = useChat({
 *   context: { doctor_id: user.sub },
 *   storageKey: `chat_${user.sub}`,
 * });
 * ```
 */

import { useMessageState } from './useMessageState';
import { useChatSync } from './useChatSync';
import { useChatActions } from './useChatActions';
import { usePagination } from './usePagination';
import type { UseChatOptions, UseChatReturn } from './types';

export function useChat(options: UseChatOptions = {}): UseChatReturn {
  const {
    phase,
    context = {},
    storageKey,
    autoIntroduction = false,
    enableThinking = true, // Default: enable thinking (Qwen3 reasoning)
    storage: injectedStorage,
    backendSync: injectedBackendSync,
    realtimeSync: injectedRealtimeSync,
  } = options;

  const doctorId = context?.doctor_id as string | undefined;

  // 1. Core state management
  const state = useMessageState();

  // 2. Pagination state and handlers
  const pagination = usePagination({
    doctorId,
    phase,
    backendSync: injectedBackendSync || (undefined as any), // Will be set by sync
    setMessages: state.setMessages,
    setError: state.setError,
    olderMessagesBufferRef: state.olderMessagesBufferRef,
  });

  // 3. Sync: storage, backend, WebSocket
  const { storage, backendSync } = useChatSync({
    storageKey,
    doctorId,
    phase,
    loadingInitial: state.loadingInitial,
    injectedStorage,
    injectedBackendSync,
    injectedRealtimeSync,
    setMessages: state.setMessages,
    setLoadingInitial: state.setLoadingInitial,
    setIsTyping: state.setIsTyping,
    setHasMoreMessages: pagination.setHasMoreMessages,
    olderMessagesBufferRef: state.olderMessagesBufferRef,
  });

  // Update pagination with actual backendSync
  const paginationWithSync = usePagination({
    doctorId,
    phase,
    backendSync,
    setMessages: state.setMessages,
    setError: state.setError,
    olderMessagesBufferRef: state.olderMessagesBufferRef,
  });

  // 4. Actions: send, intro, retry, clear
  const actions = useChatActions({
    phase,
    context,
    storageKey,
    autoIntroduction,
    enableThinking, // Toggle model thinking/reasoning (Qwen3)
    storage,
    messages: state.messages,
    loadingInitial: state.loadingInitial,
    setMessages: state.setMessages,
    setLoading: state.setLoading,
    setError: state.setError,
    setIsTyping: state.setIsTyping,
    setLastEmotionalAnalysis: state.setLastEmotionalAnalysis,
    setHasMoreMessages: paginationWithSync.setHasMoreMessages,
    setPaginationOffset: paginationWithSync.setPaginationOffset,
    lastMessageRef: state.lastMessageRef,
    lastBehaviorMetricsRef: state.lastBehaviorMetricsRef,
    introductionLoadedRef: state.introductionLoadedRef,
    olderMessagesBufferRef: state.olderMessagesBufferRef,
  });

  return {
    // State
    messages: state.messages,
    loading: state.loading,
    error: state.error,
    isTyping: state.isTyping,
    loadingInitial: state.loadingInitial,
    lastEmotionalAnalysis: state.lastEmotionalAnalysis,

    // Pagination
    hasMoreMessages: paginationWithSync.hasMoreMessages,
    loadingOlder: paginationWithSync.loadingOlder,
    loadOlderMessages: paginationWithSync.loadOlderMessages,

    // Streaming State (2025-2026)
    streaming: actions.streaming,

    // Actions
    sendMessage: actions.sendMessage,
    sendMessageStream: actions.sendMessageStream,
    getIntroduction: actions.getIntroduction,
    clearConversation: actions.clearConversation,
    retry: actions.retry,
    stopStream: actions.stopStream,
  };
}

// Re-exports for convenience
export type { UseChatOptions, UseChatReturn } from './types';
export { metricsToBackendFormat } from './utils';

// Backward compatibility alias
export { useChat as useFIConversation };

// Re-export emotional context
export { useEmotionalContext } from '../useEmotionalContext';
