/**
 * types/chat.ts
 *
 * Defines the shared interfaces for chat-related components and hooks.
 * This promotes consistency and enables dependency inversion for the ChatWidget.
 */

import type { FIMessage } from '@/types/assistant';
import type { ReactNode } from 'react';

/**
 * Defines the common interface for any chat conversation hook.
 * This allows the ChatWidget to be decoupled from a specific implementation
 * (e.g., useFIConversation, useCheckinConversation).
 */
export interface ChatHook {
  // State
  messages: FIMessage[];
  loading: boolean;
  isTyping: boolean;
  loadingInitial?: boolean;
  hasMoreMessages?: boolean;
  loadingOlder?: boolean;
  streamingMessage?: string;

  // Core Actions
  sendMessage: (message: string, metadata?: object) => Promise<void>;
  loadOlderMessages?: () => Promise<void>;

  // Optional Actions
  clearConversation?: () => void;
  getIntroduction?: () => void;
  startConversation?: () => Promise<void>;
  sendQuickReply?: (reply: string) => Promise<void>;

  // Optional State
  conversationState?: {
    quickReplies?: string[];
    actions?: Array<{ type: string; data: unknown }>;
    metadata?: Record<string, unknown>;
  };

  // Custom UI elements
  customEmptyState?: ReactNode;
  customQuickReplies?: ReactNode;
}
