'use client';

/**
 * ChatMessage - Full-featured chat message variant
 *
 * Layout shell is now fi-glass's <MessageBubble> (Plutonio, element 94). All
 * chat-specific behavior stays here and is injected into the bubble via slots:
 * - header:   MessageAvatar + MessageMeta (auth/persona)
 * - reasoning: ReasoningBlock (AI thinking)
 * - badge:    ModelBadge (LLM indicator)
 * - actions:  MessageActions with TTS/AudioPlayer
 *
 * showThinking is read from ChatConfigContext (override via prop).
 *
 * @see Headless Component Pattern: https://martinfowler.com/articles/headless-component.html
 */

import { memo } from 'react';
import { MessageBubble } from 'fi-glass/messages';
import type { ChatMessageProps } from '../types';
import { useMessage } from '../hooks/useMessage';
import { MessageAvatar } from '../primitives/MessageAvatar';
import { MessageMeta } from '../primitives/MessageMeta';
import { MessageContent } from '../primitives/MessageContent';
import { MessageActions } from '../primitives/MessageActions';
import { ModelBadge } from '../primitives/ModelBadge';
// Chat-specific components (TTS, Reasoning, Config)
import { ReasoningBlock } from '@/components/chat/ReasoningBlock';
import { SpeakButton } from '@/components/chat/MessageActions';
import { AudioPlayer } from '@/components/chat/AudioPlayer';
import { useChatConfig } from '@/components/chat/ChatConfigContext';
// TTS now routed through the VoiceAdapter (Americio): fi-glass useVoice consumes
// aurity's adapter; synthesize() makes the same /tts/synthesize call as before.
import { useVoice } from 'fi-glass/voice';
import { aurityVoiceAdapter } from '@/lib/voice/aurityVoiceAdapter';
import { reportAudioError } from '@/lib/audio/ErrorPolicy';

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

  // TTS state - routed through the VoiceAdapter (was useAudioPlayer).
  const {
    generateAudio,
    audioUrl,
    isLoading,
    voiceName,
    close: onClose,
    changeVoice: onChangeVoice,
  } = useVoice(aurityVoiceAdapter, {
    onError: (e) => {
      void reportAudioError(e, 'ChatMessage:TTS');
    },
  });

  const voice = message.metadata?.voice || 'nova';

  return (
    <MessageBubble
      role={isUser ? 'user' : 'assistant'}
      className={className}
      ariaLabel={isUser ? 'Tu mensaje' : 'Respuesta de AURITY'}
      header={
        <>
          <MessageAvatar isUser={isUser} persona={persona} />
          <MessageMeta
            isUser={isUser}
            timestamp={message.timestamp}
            name={displayName}
            persona={persona}
          />
        </>
      }
      reasoning={
        showThinking && !isUser && message.thinking ? (
          <ReasoningBlock
            thinking={message.thinking}
            messageId={message.id}
            isStreaming={isStreaming}
            persona={persona}
          />
        ) : undefined
      }
      badge={
        !isUser && message.metadata?.model ? (
          <ModelBadge
            model={message.metadata.model}
            voice={message.metadata?.voice ?? null}
          />
        ) : undefined
      }
      actions={
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
      }
    >
      {/* Content */}
      <MessageContent
        isUser={isUser}
        content={message.content}
        isStreaming={isStreaming}
      />
    </MessageBubble>
  );
});
