'use client';

/**
 * ChatMessage - Full-featured chat message variant
 *
 * Uses unified message primitives with chat-specific features:
 * - ReasoningBlock: AI thinking/reasoning display
 * - ModelBadge: LLM model indicator
 * - Auth0 integration for user names
 *
 * @see Headless Component Pattern: https://martinfowler.com/articles/headless-component.html
 */

import { memo } from 'react';
import type { ChatMessageProps } from '../types';
import { useMessage } from '../hooks/useMessage';
import { messageStyles } from '../styles/message-styles';
import { MessageAvatar } from '../primitives/MessageAvatar';
import { MessageMeta } from '../primitives/MessageMeta';
import { MessageContent } from '../primitives/MessageContent';
import { MessageActions } from '../primitives/MessageActions';
// Chat-specific components
import { ReasoningBlock } from '@/components/chat/ReasoningBlock';
import { ModelBadge } from '@/components/chat/message-list/ui/ModelBadge';

export const ChatMessage = memo(function ChatMessage({
  message,
  isStreaming = false,
  showThinking = true,
  className,
}: ChatMessageProps) {
  const { isUser, displayName, persona } = useMessage({ message });
  const { message: styles } = messageStyles;

  return (
    <article
      className={`
        ${styles.base}
        ${styles.borderRadius}
        ${isUser ? styles.user : styles.assistant}
        ${className || ''}
      `}
      role="article"
      aria-label={isUser ? 'Tu mensaje' : 'Respuesta de AURITY'}
    >
      {/* Header: Avatar + Meta */}
      <div className="flex items-center gap-2 mb-1">
        <MessageAvatar isUser={isUser} persona={persona} />
        <MessageMeta
          isUser={isUser}
          timestamp={message.timestamp}
          name={displayName}
          persona={persona}
        />
      </div>

      {/* Thinking/Reasoning Block (assistant only) */}
      {showThinking && !isUser && message.thinking && (
        <div className="mt-3 mb-3">
          <ReasoningBlock
            thinking={message.thinking}
            messageId={message.id}
            isStreaming={isStreaming}
            persona={persona}
          />
        </div>
      )}

      {/* Content */}
      <MessageContent
        isUser={isUser}
        content={message.content}
        isStreaming={isStreaming}
      />

      {/* Model Badge (assistant only) */}
      {!isUser && message.metadata?.model && (
        <div className="mt-2">
          <ModelBadge
            model={message.metadata.model}
            voice={message.metadata?.voice ?? null}
          />
        </div>
      )}

      {/* Hover Actions */}
      <MessageActions
        isUser={isUser}
        content={message.content}
        voice={message.metadata?.voice}
      />
    </article>
  );
});
