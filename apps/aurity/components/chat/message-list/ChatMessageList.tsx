'use client';

/**
 * ChatMessageList - Dense Style (Claude.ai / ChatGPT inspired)
 *
 * Modern, minimal, content-first
 *
 * Architecture:
 * - config/styles.ts: All styling configuration
 * - core/types.ts: Shared interfaces
 * - ui/*: Atomic components (Avatar, Meta, Content, Actions, etc.)
 * - hooks/*: Business logic (useMessageGroups)
 *
 * Design principles:
 * - No bubbles - text is protagonist
 * - Minimal spacing between messages
 * - Subtle avatars (24px, muted colors)
 * - Dark grey base (#121212 equivalent)
 * - Hover actions only
 */

import { memo } from 'react';
import type { FIMessage, FITone } from '@aurity-standalone/types/assistant';
import type { ChatConfig } from '@/config/chat.config';
import { messageStyles } from './config/styles';
import { useMessageGroups } from './hooks/useMessageGroups';
import { DateDivider, TypingIndicator } from './ui';
import { ChatMessage } from '@/components/ui/message';

// ============================================================================
// Props
// ============================================================================

export interface ChatMessageListProps {
  /** Messages to render */
  messages: FIMessage[];
  /** Is assistant typing */
  isTyping: boolean;
  /** Chat config (for theme) */
  config: ChatConfig;
  /** Currently selected persona (from selector) */
  selectedPersona?: FITone;
  /** Streaming state */
  streaming?: {
    status: 'idle' | 'streaming' | 'complete' | 'error';
    content: string;
    thinking: string;
    isStreaming: boolean;
  };
}

// ============================================================================
// Component
// ============================================================================

export const ChatMessageList = memo(function ChatMessageList({
  messages,
  isTyping,
  config,
  selectedPersona,
  streaming,
}: ChatMessageListProps) {
  // Group messages by date
  const messageGroups = useMessageGroups(messages);
  const { container } = messageStyles;

  // Use selectedPersona from selector, fallback to most recent assistant message
  const lastMessagePersona = messages
    .slice()
    .reverse()
    .find(msg => msg.role === 'assistant')?.metadata?.tone;

  // Priority: selectedPersona > last message persona
  const currentPersona = selectedPersona || lastMessagePersona;

  // Debug log removed - was causing console spam on every keystroke
  // Enable for debugging: console.log('[ChatMessageList] Render:', { messagesCount: messages.length });

  return (
    <div className={`${container.base} ${container.padding}`}>
      {messageGroups.map((group) => (
        <div key={group.date}>
          {/* Date separator */}
          <DateDivider date={group.date} />

          {/* Messages in group */}
          <div className="space-y-0.5">
            {group.messages.map((message, idx) => (
              <ChatMessage
                key={message.id || `${message.timestamp}-${idx}`}
                message={message}
                isStreaming={false}
                showThinking={config.behavior.showThinking}
              />
            ))}
          </div>
        </div>
      ))}

      {/* Streaming message - shows content as it arrives */}
      {streaming?.isStreaming && (streaming.content || streaming.thinking) && (
        <>
          <ChatMessage
            message={{
              id: 'streaming-temp',
              role: 'assistant',
              content: streaming.content,
              thinking: streaming.thinking || undefined,  // FIX: at root level (was in metadata)
              timestamp: new Date().toISOString(),
              metadata: {
                tone: currentPersona,
              },
            }}
            isStreaming={true}
            showThinking={config.behavior.showThinking}
          />
        </>
      )}

      {/* Typing indicator */}
      {isTyping && <TypingIndicator persona={currentPersona} />}

      {/* Ghost spacer - prevents content from being hidden behind floating input */}
      <div
        className="h-28 w-full pointer-events-none select-none"
        aria-hidden="true"
        data-ghost-spacer
      />
    </div>
  );
});
