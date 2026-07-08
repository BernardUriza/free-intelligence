// Re-export from apps/aurity/hooks - CONSOLIDATION
// useEmotionalContext is deliberately NOT re-exported here: the package's
// src/index.ts exports its own copy and a star re-export would collide (TS2308).
export {
  useChat,
  useFIConversation,
  metricsToBackendFormat,
} from '../../../hooks/useFIConversation';
export type {
  UseFIConversationOptions,
  UseFIConversationReturn,
} from '../../../hooks/useFIConversation';
