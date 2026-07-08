// Re-export from apps/aurity/hooks - CONSOLIDATION
// useEmotionalContext is deliberately NOT re-exported here: the package's
// src/index.ts exports its own copy and a star re-export would collide (TS2308).
export {
  useChat,
  useChat as useFIConversation,
  metricsToBackendFormat,
} from '../../../../hooks/useChat/index';
export type { UseChatOptions, UseChatReturn } from '../../../../hooks/useChat/index';
