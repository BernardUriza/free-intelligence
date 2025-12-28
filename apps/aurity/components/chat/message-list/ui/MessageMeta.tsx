'use client';

/**
 * MessageMeta - Author name + timestamp
 *
 * Shows persona display name for assistant, user name for user messages.
 * Modern gradient text for assistant personas.
 */

import { memo } from 'react';
import type { BaseMessageProps } from '../core/types';
import { messageStyles } from '../config/styles';
import type { FITone } from '@aurity-standalone/types/assistant';

export interface MessageMetaProps extends BaseMessageProps {
  /** ISO timestamp */
  timestamp: string;
  /** Custom name (default: Tú/AURITY) */
  name?: string;
  /** Persona ID for display name (assistant only) */
  persona?: FITone;
}

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

export const MessageMeta = memo(function MessageMeta({
  isUser,
  timestamp,
  name,
  persona,
}: MessageMetaProps) {
  const { meta } = messageStyles;

  const formattedTime = new Date(timestamp).toLocaleTimeString('es-MX', {
    hour: '2-digit',
    minute: '2-digit',
  });

  // Use persona name for assistant, Auth0 name for user
  const displayName = isUser
    ? (name ?? 'Tú')
    : getPersonaDisplayName(persona);

  return (
    <div className={meta.container}>
      <span className={`${meta.name} ${!isUser ? 'fi-gradient-text-brand font-semibold' : ''}`}>
        {displayName}
      </span>
      <time className={meta.time} dateTime={timestamp}>
        {formattedTime}
      </time>
    </div>
  );
});
