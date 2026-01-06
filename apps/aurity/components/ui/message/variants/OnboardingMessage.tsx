'use client';

/**
 * OnboardingMessage - Rich message variant for onboarding flows
 *
 * Features:
 * - Rich markdown rendering
 * - Persona-based glassmorphism styling
 * - Timestamps and phase indicators
 * - Entrance animations
 * - TTS with persona voice
 *
 * Refactored (2025-01-06): Now uses unified primitives instead of FIMessageBubble wrapper
 *
 * @see Headless Component Pattern: https://martinfowler.com/articles/headless-component.html
 */

import { memo } from 'react';
import type { OnboardingMessageProps } from '../types';
import { useMessage } from '../hooks/useMessage';
import { MessageContent } from '../primitives/MessageContent';
import { MessageActions } from '../primitives/MessageActions';
import { ModelBadge } from '../primitives/ModelBadge';
import { MessageTimestamp } from '@/components/chat/MessageTimestamp';

/**
 * OnboardingMessage - Glassmorphism styled message for onboarding
 *
 * @example
 * ```tsx
 * <OnboardingMessage
 *   message={{
 *     role: 'assistant',
 *     content: 'Bienvenido a Free-Intelligence...',
 *     timestamp: '2025-01-06T12:00:00Z',
 *     metadata: { tone: 'onboarding_guide', phase: 'welcome' }
 *   }}
 *   showTimestamp
 *   animate
 * />
 * ```
 */
export const OnboardingMessage = memo(function OnboardingMessage({
  message,
  showTimestamp = true,
  showSenderName = true,
  animate = true,
  className = '',
  borderRadiusOverride,
}: OnboardingMessageProps) {
  // Use headless hook for shared logic (already calls usePersonas internally)
  const { isUser, personaStyle, personaLabel, personaVoice, personaModel } = useMessage({ message });

  // Border radius (default or override)
  const borderRadius = borderRadiusOverride || 'rounded-2xl rounded-tl-sm';

  return (
    <div
      className={`
        ${animate ? 'animate-fade-in-up' : ''}
        ${className}
      `}
      role="article"
      aria-label="Free-Intelligence message"
    >
      {/* Message Bubble - Glassmorphism design */}
      <div
        className={`
          relative group flex-1 max-w-[72ch]
          px-3 py-1.5 ${borderRadius}
          border ${personaStyle.border.replace('/60', '/[0.12]')}
          ${personaStyle.bg.replace('/20', '/[0.06]')}
          backdrop-blur-2xl backdrop-saturate-150
          shadow-sm shadow-black/5
          transition-all duration-300 ease-out
          hover:shadow-md
        `}
      >
        {/* Content - Using MessageContent primitive */}
        <MessageContent
          isUser={isUser}
          content={message.content}
          isStreaming={false}
        />

        {/* Metadata footer */}
        <div className="mt-1 flex items-center gap-2 justify-between text-[10px] text-slate-500">
          <div className="flex items-center gap-1.5">
            {/* Persona label */}
            {showSenderName && personaLabel && (
              <>
                <span className={`font-medium ${personaStyle.labelColor}`}>
                  {personaLabel}
                </span>
                <span className="text-slate-600">•</span>
              </>
            )}

            {/* Timestamp */}
            {showTimestamp && message.timestamp && (
              <MessageTimestamp
                timestamp={message.timestamp}
                position="inline"
                size="xs"
              />
            )}

            {/* Phase indicator */}
            {message.metadata?.phase && (
              <>
                <span className="text-slate-600">•</span>
                <span className="text-slate-500">{message.metadata.phase}</span>
              </>
            )}
          </div>

          {/* Action buttons + ModelBadge (hover) */}
          <div className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-2">
            <MessageActions
              isUser={isUser}
              content={message.content}
              voice={personaVoice}
            />
            {personaVoice && (
              <ModelBadge
                model={personaModel || 'free-intelligence'}
                className="ml-1"
                voice={personaVoice}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
});

/**
 * Re-export props type for convenience
 */
export type { OnboardingMessageProps };
