'use client';

/**
 * MessageActions - Hover action toolbar primitive
 *
 * Pure UI primitive with NO chat-layer dependencies.
 * TTS functionality is injected via children prop (Dependency Inversion).
 *
 * @example
 * // Basic (copy only)
 * <MessageActions isUser={false} content="Hello" />
 *
 * // With TTS injected
 * <MessageActions isUser={false} content="Hello">
 *   <SpeakButton content="Hello" voice="nova" onOpenPlayer={generateAudio} />
 * </MessageActions>
 */

import { memo, useState, useCallback, type ReactNode } from 'react';
import { Copy, Check } from 'lucide-react';
import { messageStyles } from '../styles/message-styles';

export interface MessageActionsProps {
  /** Is this a user message */
  isUser: boolean;
  /** Message content for copy */
  content: string;
  /** Optional TTS controls (injected by consumer) */
  children?: ReactNode;
  /** Optional audio player slot (rendered below actions) */
  audioPlayer?: ReactNode;
}

export const MessageActions = memo(function MessageActions({
  isUser,
  content,
  children,
  audioPlayer,
}: MessageActionsProps) {
  const [copied, setCopied] = useState(false);
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
        {/* Copy - always available */}
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

        {/* TTS - injected by consumer (ChatMessage, etc.) */}
        {children}


      </div>

      {/* Audio Player slot - injected by consumer */}
      {audioPlayer}
    </>
  );
});
