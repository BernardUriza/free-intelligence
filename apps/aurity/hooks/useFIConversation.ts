/**
 * useFIConversation Hook (DEPRECATED)
 *
 * This file is kept for backward compatibility.
 * Use `useChat` from '@aurity-standalone/hooks/useChat' instead.
 *
 * @deprecated Use `useChat` instead
 */

// Re-export everything from the new modular implementation
export {
  useChat,
  useChat as useFIConversation,
  metricsToBackendFormat,
  useEmotionalContext,
} from './useChat';

export type {
  UseChatOptions as UseFIConversationOptions,
  UseChatReturn as UseFIConversationReturn,
} from './useChat';
