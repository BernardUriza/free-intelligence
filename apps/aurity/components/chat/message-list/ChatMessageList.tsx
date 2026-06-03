'use client';

/**
 * ChatMessageList - Dense Style (Claude.ai / ChatGPT inspired)
 *
 * Structure is now fi-glass's <MessageList> (Plutonio, element 94). aurity keeps
 * all data logic and injects it via slots:
 * - groups:        useMessageGroups (date grouping)
 * - renderDivider: DateDivider
 * - renderItem:    ChatMessage
 * - footer:        streaming row + TypingIndicator + ghost spacer
 * - ChatConfigProvider wraps the list (showThinking via context)
 *
 * Design principles: no bubbles, minimal spacing, subtle avatars, hover actions.
 */

import { memo } from 'react';
import { MessageList } from 'fi-glass/messages';
import type { FIMessage, FITone } from '@aurity-standalone/types/assistant';
import type { ChatConfig } from '@/config/chat.config';
import { messageStyles } from './config/styles';
import { useMessageGroups } from './hooks/useMessageGroups';
import { DateDivider, TypingIndicator } from './ui';
import { ChatMessage } from '@/components/ui/message';
import { ChatConfigProvider } from '@/components/chat/ChatConfigContext';

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
  // Group messages by date, then adapt to fi-glass MessageList's group shape
  const messageGroups = useMessageGroups(messages);
  const groups = messageGroups.map((group) => ({
    key: group.date,
    items: group.messages,
  }));
  const { container } = messageStyles;

  // Use selectedPersona from selector, fallback to most recent assistant message
  const lastMessagePersona = messages
    .slice()
    .reverse()
    .find((msg) => msg.role === 'assistant')?.metadata?.tone;

  // Priority: selectedPersona > last message persona
  const currentPersona = selectedPersona || lastMessagePersona;

  return (
    <ChatConfigProvider showThinking={config.behavior.showThinking}>
      <MessageList<FIMessage>
        containerClassName={`${container.base} ${container.padding}`}
        groupClassName="space-y-0.5"
        groups={groups}
        renderDivider={(date) => <DateDivider date={date} />}
        renderItem={(message, idx) => (
          <ChatMessage
            key={message.id || `${message.timestamp}-${idx}`}
            message={message}
            isStreaming={false}
            // showThinking now comes from ChatConfigContext
          />
        )}
        footer={
          <>
            {/* Streaming message - shows content as it arrives */}
            {streaming?.isStreaming &&
              (streaming.content || streaming.thinking) && (
                <ChatMessage
                  message={{
                    id: 'streaming-temp',
                    role: 'assistant',
                    content: streaming.content,
                    thinking: streaming.thinking || undefined,
                    timestamp: new Date().toISOString(),
                    metadata: {
                      tone: currentPersona,
                    },
                  }}
                  isStreaming={true}
                  // showThinking now comes from ChatConfigContext
                />
              )}

            {/* Typing indicator */}
            {isTyping && <TypingIndicator persona={currentPersona} />}

            {/* Ghost spacer - prevents content from being hidden behind floating input */}
            <div
              className="h-28 w-full pointer-events-none select-none"
              aria-hidden="true"
              data-ghost-spacer
            />
          </>
        }
      />
    </ChatConfigProvider>
  );
});
