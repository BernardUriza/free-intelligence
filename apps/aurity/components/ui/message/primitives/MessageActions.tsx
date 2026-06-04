'use client';

/**
 * MessageActions - Hover action toolbar primitive
 *
 * The copy button is now fi-glass's <CopyButton> (Plutonio, element 94); this
 * component keeps aurity's toolbar container + injected TTS (children) + audio
 * player slot. Copy failures still route through aurity's logger via onError, so
 * behavior is unchanged.
 *
 * @example
 * <MessageActions isUser={false} content="Hello">
 *   <SpeakButton content="Hello" voice="nova" onOpenPlayer={generateAudio} />
 * </MessageActions>
 */

import { memo, type ReactNode } from 'react';
import { CopyButton } from 'fi-glass/messages';
import { createLogger } from '@/lib/internal/logger';
import { messageStyles } from '../styles/message-styles';

const log = createLogger('MessageActions');

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
  const { actions } = messageStyles;

  return (
    <>
      <div className={actions.container}>
        {/* Copy - always available (fi-glass primitive) */}
        <CopyButton
          content={content}
          onError={(err) => log.error('Copy failed', { error: String(err) })}
        />

        {/* TTS - injected by consumer (ChatMessage, etc.) */}
        {children}
      </div>

      {/* Audio Player slot - injected by consumer */}
      {audioPlayer}
    </>
  );
});
