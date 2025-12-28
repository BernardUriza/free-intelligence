/**
 * useChat Types
 *
 * Type definitions for the chat hook.
 * SOLID: Interface Segregation - focused, minimal interfaces.
 */

import type {
  FIMessage,
  FIChatContext,
  OnboardingPhase,
  BehaviorMetrics,
  EmotionalAnalysis,
} from '@aurity-standalone/types/assistant';
import type { ChatResponse } from '@aurity-standalone/api-client/assistant';
import type { IMessageStorage } from '@/lib/chat/storage';
import type { IBackendSync, IRealtimeSync } from '@/lib/chat/sync-strategy';

// Use ChatResponse as FIChatResponse for simplicity
export type FIChatResponse = ChatResponse;

// ============================================================================
// Hook Options (Dependency Injection)
// ============================================================================

export interface UseChatOptions {
  /** Current onboarding phase */
  phase?: OnboardingPhase;

  /** Additional context for personalization */
  context?: Omit<FIChatContext, 'phase'>;

  /** LocalStorage key for persistence */
  storageKey?: string;

  /** Auto-load introduction on mount */
  autoIntroduction?: boolean;

  /** Enable model thinking/reasoning (Qwen3). Default true. Set false to save compute. */
  enableThinking?: boolean;

  // Dependency Injection (SOLID: Dependency Inversion)
  storage?: IMessageStorage;
  backendSync?: IBackendSync;
  realtimeSync?: IRealtimeSync;
}

// ============================================================================
// Streaming Types (2025-2026 Best Practices)
// ============================================================================

export type StreamStatus =
  | 'idle'
  | 'connecting'
  | 'streaming'
  | 'thinking'
  | 'complete'
  | 'error'
  | 'aborted';

export interface StreamingState {
  /** Current stream status */
  status: StreamStatus;
  /** Streaming message content */
  content: string;
  /** Thinking/reasoning content */
  thinking: string;
  /** Whether currently streaming */
  isStreaming: boolean;
}

// ============================================================================
// Hook Return Value
// ============================================================================

export interface UseChatReturn {
  // State
  messages: FIMessage[];
  loading: boolean;
  error: string | null;
  isTyping: boolean;
  loadingInitial: boolean;
  lastEmotionalAnalysis: EmotionalAnalysis | null;

  // Streaming State (2025-2026)
  streaming: StreamingState;

  // Pagination
  hasMoreMessages: boolean;
  loadingOlder: boolean;
  loadOlderMessages: () => Promise<void>;

  // Actions
  sendMessage: (message: string, behaviorMetrics?: BehaviorMetrics) => Promise<FIChatResponse | null>;
  sendMessageStream: (message: string, behaviorMetrics?: BehaviorMetrics) => Promise<FIChatResponse | null>;
  getIntroduction: () => Promise<FIChatResponse | null>;
  clearConversation: () => void;
  retry: () => Promise<void>;
  stopStream: () => void;

  // Optional (for ChatHook compatibility)
  streamingMessage?: string;
  customEmptyState?: React.ReactNode;
  customQuickReplies?: React.ReactNode;
}

// ============================================================================
// Internal State Types
// ============================================================================

export interface ChatState {
  messages: FIMessage[];
  loading: boolean;
  error: string | null;
  isTyping: boolean;
  loadingInitial: boolean;
  lastEmotionalAnalysis: EmotionalAnalysis | null;
}

export interface PaginationState {
  loadingOlder: boolean;
  hasMoreMessages: boolean;
  paginationOffset: number;
}

// ============================================================================
// Re-exports
// ============================================================================

export type {
  FIMessage,
  FIChatContext,
  OnboardingPhase,
  BehaviorMetrics,
  EmotionalAnalysis,
};
