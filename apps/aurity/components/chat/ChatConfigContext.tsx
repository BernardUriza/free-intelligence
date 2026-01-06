'use client';

/**
 * ChatConfigContext - Eliminates props drilling for chat configuration
 *
 * Instead of drilling showThinking through 4 layers:
 *   ChatWidget → ChatContent → ChatMessageList → ChatMessage
 *
 * Components can now access config directly:
 *   const { showThinking } = useChatConfig();
 *
 * @see Props Drilling Anti-pattern: https://kentcdodds.com/blog/prop-drilling
 */

import { createContext, useContext, type ReactNode } from 'react';

// ============================================================================
// Types
// ============================================================================

export interface ChatConfigContextValue {
  /** Show AI reasoning/thinking blocks */
  showThinking: boolean;
  /** Response mode (explanatory vs concise) */
  responseMode?: 'explanatory' | 'concise';
}

// ============================================================================
// Context
// ============================================================================

const ChatConfigContext = createContext<ChatConfigContextValue | null>(null);

// ============================================================================
// Hook
// ============================================================================

/**
 * Access chat configuration from any component in the tree
 *
 * @throws Error if used outside ChatConfigProvider
 *
 * @example
 * ```tsx
 * function ChatMessage() {
 *   const { showThinking } = useChatConfig();
 *   return showThinking && <ReasoningBlock ... />;
 * }
 * ```
 */
export function useChatConfig(): ChatConfigContextValue {
  const context = useContext(ChatConfigContext);

  if (!context) {
    // Fallback to defaults if no provider (backwards compatibility)
    return {
      showThinking: true,
      responseMode: 'explanatory',
    };
  }

  return context;
}

// ============================================================================
// Provider
// ============================================================================

export interface ChatConfigProviderProps {
  children: ReactNode;
  showThinking: boolean;
  responseMode?: 'explanatory' | 'concise';
}

export function ChatConfigProvider({
  children,
  showThinking,
  responseMode = 'explanatory',
}: ChatConfigProviderProps) {
  return (
    <ChatConfigContext.Provider value={{ showThinking, responseMode }}>
      {children}
    </ChatConfigContext.Provider>
  );
}
