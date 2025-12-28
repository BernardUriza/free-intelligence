'use client';

/**
 * ChatMessage - Single message composition
 *
 * Composes: Avatar + Meta + Content + Actions + ReasoningBlock
 * Dense layout: minimal vertical space
 *
 * Updated: 2025-12-12 - Added thinking/reasoning support for Qwen3
 */

import { memo } from 'react';
import type { FIMessage } from '@aurity-standalone/types/assistant';
import { messageStyles } from '../config/styles';
import { MessageAvatar } from './MessageAvatar';
import { MessageMeta } from './MessageMeta';
import { MessageContent } from './MessageContent';
import { MessageActions } from './MessageActions';
import { ReasoningBlock } from '../../ReasoningBlock';
import { ModelBadge } from './ModelBadge';
import { useAuth } from '@aurity-standalone/hooks/useAuth';

export interface ChatMessageProps {
  /** The message */
  message: FIMessage;
  /** Is streaming */
  isStreaming?: boolean;
  /** Show thinking/reasoning block (default true) */
  showThinking?: boolean;
}

export const ChatMessage = memo(function ChatMessage({
  message,
  isStreaming = false,
  showThinking = true,
}: ChatMessageProps) {
  const isUser = message.role === 'user';
  const { message: styles } = messageStyles;
  const { user } = useAuth();

  // Get user display name (Auth0 user for 'user' messages, AURITY for assistant)
  const displayName = isUser ? (user?.name || 'Tú') : 'AURITY';

  // DEBUG: Log assistant message metadata + thinking
  if (!isUser) {
    console.log('[ChatMessage] 🎯 Assistant message:', {
      hasThinking: Boolean(message.thinking),
      thinkingPreview: message.thinking?.substring(0, 50),
      showThinking,
      willRenderReasoningBlock: Boolean(showThinking && message.thinking),
      hasMetadata: Boolean(message.metadata),
      model: message.metadata?.model,
    });
  }

  // Get persona from metadata
  const persona = message.metadata?.tone;

  return (
    <article
      className={`
        ${styles.base}
        ${styles.borderRadius}
        ${isUser ? styles.user : styles.assistant}
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

      {/* Thinking/Reasoning Block (assistant only, when available and showThinking=true) */}
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

      {/* Model Badge (assistant only, when model is available) */}
      {!isUser && message.metadata?.model && (
        <div className="mt-2">
          <ModelBadge model={message.metadata.model} voice={message.metadata?.voice ?? null} />
        </div>
      )}

      {/* Hover Actions */}
      <MessageActions isUser={isUser} content={message.content} />
    </article>
  );
});
