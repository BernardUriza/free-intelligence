'use client';

/**
 * MessageActions - Hover action toolbar primitive
 *
 * Shows on hover: copy, TTS, more options
 */

import { memo, useState, useCallback } from 'react';
import { Copy, Check, MoreHorizontal } from 'lucide-react';
import { messageStyles } from '../styles/message-styles';
import { SpeakButton } from '@/components/chat/MessageActions';
import { useAudioPlayer, AudioPlayer } from '@/components/chat/AudioPlayer';

export interface MessageActionsProps {
  /** Is this a user message */
  isUser: boolean;
  /** Message content for copy/TTS */
  content: string;
  /** Voice for TTS (voice ID) */
  voice?: string;
}

export const MessageActions = memo(function MessageActions({
  isUser,
  content,
  voice = 'nova',
}: MessageActionsProps) {
  const [copied, setCopied] = useState(false);
  const {
    generateAudio,
    audioUrl,
    isLoading,
    voiceName,
    close: onClose,
    changeVoice: onChangeVoice,
  } = useAudioPlayer();

  const { actions } = messageStyles;

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('[MessageActions] Copy failed:', err);
    }
  }, [content]);

  return (
    <>
      <div className={actions.container}>
        {/* Copy */}
        <button
          onClick={handleCopy}
          className={`${actions.button.base} ${copied ? actions.button.active : actions.button.idle}`}
          title={copied ? 'Copiado' : 'Copiar'}
          aria-label={copied ? 'Copiado' : 'Copiar mensaje'}
        >
          {copied ? (
            <Check className={actions.icon} />
          ) : (
            <Copy className={actions.icon} />
          )}
        </button>

        {/* TTS - for both user and assistant messages */}
        <SpeakButton
          content={content}
          size="sm"
          voice={voice}
          isUserMessage={isUser}
          onOpenPlayer={generateAudio}
        />

        {/* More options */}
        <button
          onClick={() => {
            /* TODO: dropdown menu */
          }}
          className={`${actions.button.base} ${actions.button.idle}`}
          title="Más opciones"
          aria-label="Más opciones"
        >
          <MoreHorizontal className={actions.icon} />
        </button>
      </div>

      {/* Audio Player - Visible when audio is being synthesized or loaded */}
      {(isLoading || audioUrl) && (
        <AudioPlayer
          audioUrl={audioUrl}
          isLoading={isLoading}
          voiceName={voiceName || 'Nova'}
          isUserMessage={isUser}
          currentVoice={voice}
          onClose={onClose}
          onChangeVoice={onChangeVoice}
        />
      )}
    </>
  );
});
