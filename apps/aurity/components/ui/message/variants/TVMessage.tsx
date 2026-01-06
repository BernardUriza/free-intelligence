'use client';

/**
 * TVMessage - Message variant optimized for TV displays
 *
 * Features:
 * - Large, responsive text with CSS clamp()
 * - No markdown parsing (plain text)
 * - No actions (copy, speak)
 * - Persona styling via shared styles
 *
 * Used by: WaitingRoomHost
 */

import { memo } from 'react';
import type { TVMessageProps } from '../types';
import { useMessageTV } from '../hooks/useMessage';
import { tvStyles, getTVFontSize } from '../styles/message-styles';

export const TVMessage = memo(function TVMessage({
  message,
  fontSize,
  className = '',
}: TVMessageProps) {
  const { personaStyle } = useMessageTV({ message });

  // Calculate font size based on content length
  const computedFontSize = fontSize || getTVFontSize(message.content.length);

  return (
    <div
      className={`
        transform transition-all duration-500 ease-in-out
        ${tvStyles.message.base}
        ${personaStyle.border.replace('/60', '/30')}
        ${personaStyle.bg.replace('/20', '/40')}
        ${className}
      `}
    >
      {/* Header */}
      <div className={tvStyles.header.container}>
        <div className={tvStyles.header.badge}>
          <span
            className={`${tvStyles.header.label} ${personaStyle.labelColor}`}
            style={{ fontSize: 'clamp(0.75rem, 1.2vw, 1.25rem)' }}
          >
            FREE-INTELLIGENCE
          </span>
        </div>
        <div className="fi-flex-gap">
          <personaStyle.Icon
            className={personaStyle.labelColor}
            style={{
              width: 'clamp(1rem, 1.5vw, 1.5rem)',
              height: 'clamp(1rem, 1.5vw, 1.5rem)',
            }}
          />
        </div>
      </div>

      {/* Content - Full Screen Centered with Smart Scaling */}
      <div className={tvStyles.content.base}>
        <p
          className={tvStyles.content.text}
          style={{ fontSize: computedFontSize }}
        >
          {message.content}
        </p>
      </div>
    </div>
  );
});
