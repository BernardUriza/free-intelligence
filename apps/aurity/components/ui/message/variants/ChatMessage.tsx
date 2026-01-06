'use client';

/**
 * ChatMessage - Full-featured chat message variant
 *
 * Uses unified message primitives with chat-specific features:
 * - ReasoningBlock: AI thinking/reasoning display
 * - ModelBadge: LLM model indicator
 * - Auth0 integration for user names
 * - TTS via AudioPlayer (injected into MessageActions)
 *
 * showThinking is read from ChatConfigContext (eliminates props drilling)
 * but can be overridden via prop for special cases.
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
import { ModelBadge } from '../primitives/ModelBadge';
// Chat-specific components (TTS, Reasoning, Config)
import { ReasoningBlock } from '@/components/chat/ReasoningBlock';
import { SpeakButton } from '@/components/chat/MessageActions';
import { useAudioPlayer, AudioPlayer } from '@/components/chat/AudioPlayer';
import { useChatConfig } from '@/components/chat/ChatConfigContext';

export const ChatMessage = memo(function ChatMessage({
  message,
  isStreaming = false,
  showThinking: showThinkingProp,
  className,
}: ChatMessageProps) {
  // Read from context, allow prop override
  const config = useChatConfig();
  const showThinking = showThinkingProp ?? config.showThinking;
  const { isUser, displayName, persona } = useMessage({ message });
  const { message: styles } = messageStyles;

  // TTS state - lives here, injected into primitive
  const {
    generateAudio,
    audioUrl,
    isLoading,
    voiceName,
    close: onClose,
    changeVoice: onChangeVoice,
  } = useAudioPlayer();

  const voice = message.metadata?.voice || 'nova';

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

      {/* Hover Actions - TTS injected as children */}
      <MessageActions
        isUser={isUser}
        content={message.content}
        audioPlayer={
          (isLoading || audioUrl) && (
            <AudioPlayer
              audioUrl={audioUrl}
              isLoading={isLoading}
              voiceName={voiceName || 'Nova'}
              isUserMessage={isUser}
              currentVoice={voice}
              onClose={onClose}
              onChangeVoice={onChangeVoice}
            />
          )
        }
      >
        <SpeakButton
          content={message.content}
          size="sm"
          voice={voice}
          isUserMessage={isUser}
          onOpenPlayer={generateAudio}
        />
      </MessageActions>
    </article>
  );
});
