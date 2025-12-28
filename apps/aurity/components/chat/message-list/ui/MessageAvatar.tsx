'use client';

/**
 * MessageAvatar - User/assistant avatar
 *
 * Renders persona-specific icons for assistant messages using Lucide icons.
 * Shows User icon for user messages.
 * Circular, compact, with gradient background for assistant.
 */

import { memo } from 'react';
import { User } from 'lucide-react';
import type { BaseMessageProps } from '../core/types';
import { messageStyles } from '../config/styles';
import { getPersonaIcon } from '@/types/select-configs';
import type { FITone } from '@aurity-standalone/types/assistant';

export interface MessageAvatarProps extends BaseMessageProps {
  /** Persona ID for icon selection (assistant only) */
  persona?: FITone;
}

export const MessageAvatar = memo(function MessageAvatar({
  isUser,
  persona
}: MessageAvatarProps) {
  const { avatar } = messageStyles;

  // Get persona-specific icon for assistant messages
  const PersonaIcon = isUser ? User : getPersonaIcon(persona);

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
      <PersonaIcon className={`w-4 h-4 ${isUser ? 'fi-text-primary' : 'fi-text-success'}`} />
    </div>
  );
});
