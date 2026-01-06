'use client';

/**
 * TypingIndicator - Shows when assistant is typing
 *
 * Shows persona avatar, name, and animated dots
 */

import { memo } from 'react';
import { messageStyles } from '../config/styles';
import { MessageAvatar } from '@/components/ui/message/primitives';
import type { FITone } from '@aurity-standalone/types/assistant';

/**
 * Persona display names mapping
 */
const PERSONA_DISPLAY_NAMES: Record<string, string> = {
  general_assistant: 'Asistente General',
  soap_editor: 'Editor SOAP',
  clinical_advisor: 'Asesor Clínico',
  onboarding_guide: 'Guía de Onboarding',
  pattern_weaver: 'Tejedor de Patrones',
  sovereignty_guide: 'Guía de Soberanía',
  growth_mirror: 'Espejo de Crecimiento',
  honest_limiter: 'Limitador Honesto',
};

/**
 * Get persona display name
 */
function getPersonaDisplayName(persona?: FITone): string {
  if (!persona) return 'AURITY';
  return PERSONA_DISPLAY_NAMES[persona] || 'AURITY';
}

export interface TypingIndicatorProps {
  /** Persona for avatar and name */
  persona?: FITone;
}

export const TypingIndicator = memo(function TypingIndicator({ persona }: TypingIndicatorProps) {
  const { typing } = messageStyles;
  const personaName = getPersonaDisplayName(persona);

  return (
    <div className={typing.container} role="status" aria-label={`${personaName} está escribiendo`}>
      <MessageAvatar isUser={false} persona={persona} />
      <div className="fi-flex-gap">
        {/* Persona name */}
        <span className="text-sm fi-gradient-text-brand font-semibold">
          {personaName}
        </span>
        {/* Animated dots */}
        <div className="fi-flex-gap-sm">
          <span className={`${typing.dot} ${typing.animation}`} style={{ animationDelay: '0ms' }} />
          <span className={`${typing.dot} ${typing.animation}`} style={{ animationDelay: '150ms' }} />
          <span className={`${typing.dot} ${typing.animation}`} style={{ animationDelay: '300ms' }} />
        </div>
      </div>
    </div>
  );
});
