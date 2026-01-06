'use client';

/**
 * MessageAvatar - User/assistant avatar primitive
 *
 * Renders persona-specific icons for assistant messages using Lucide icons.
 * Shows User icon for user messages.
 */

import { memo } from 'react';
import { User } from 'lucide-react';
import { messageStyles } from '../styles/message-styles';
import { getPersonaStyle } from '../styles/persona-styles';

export interface MessageAvatarProps {
  /** Is this a user message */
  isUser: boolean;
  /** Persona ID for icon selection (assistant only) */
  persona?: string;
}

export const MessageAvatar = memo(function MessageAvatar({
  isUser,
  persona,
}: MessageAvatarProps) {
  const { avatar } = messageStyles;

  // Get persona-specific icon for assistant messages
  const personaStyle = getPersonaStyle(persona);
  const IconComponent = isUser ? User : personaStyle.Icon;

  return (
    <div
      className={`
        ${avatar.size}
        ${avatar.base}
        ${isUser ? avatar.user : avatar.assistant}
        ${!isUser ? 'bg-gradient-to-br from-emerald-500/20 to-blue-500/20 border-emerald-500/30' : ''}
      `}
      aria-hidden="true"
    >
      <IconComponent
        className={`w-4 h-4 ${isUser ? 'fi-text-primary' : 'fi-text-success'}`}
      />
    </div>
  );
});
