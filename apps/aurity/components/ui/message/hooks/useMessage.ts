/**
 * useMessage - Headless hook for message logic
 * Separates state/logic from presentation (Headless Component Pattern)
 *
 * @see https://martinfowler.com/articles/headless-component.html
 */

import { useCallback, useMemo } from 'react';
import { usePersonas } from '@aurity-standalone/hooks/usePersonas';
import { useAuth } from '@aurity-standalone/hooks/useAuth';
import type { UseMessageOptions, UseMessageReturn } from '../types';
import {
  getPersonaStyle,
  generatePersonaLabel,
  FALLBACK_STYLE,
} from '../styles/persona-styles';

/**
 * Headless hook that provides message logic without UI
 *
 * @example
 * ```tsx
 * const { isUser, personaStyle, copyToClipboard } = useMessage({
 *   message,
 *   persona: 'waiting_room_host'
 * });
 * ```
 */
export function useMessage(options: UseMessageOptions): UseMessageReturn {
  const { message, persona: explicitPersona } = options;

  // Get auth user for display name
  const { user } = useAuth();

  // Fetch personas from backend
  const { personas } = usePersonas();

  // Derive persona from explicit prop or message metadata
  const persona = explicitPersona || message.metadata?.tone || 'general_assistant';

  // Derive if user message
  const isUser = message.role === 'user';

  // Get display name
  const displayName = useMemo(() => {
    if (isUser) {
      return user?.name || 'Tú';
    }
    return 'AURITY';
  }, [isUser, user?.name]);

  // Get persona style
  const personaStyle = useMemo(() => {
    return getPersonaStyle(persona);
  }, [persona]);

  // Get persona data from backend
  const personaData = useMemo(() => {
    return personas.find((p) => p.id === persona);
  }, [personas, persona]);

  // Get persona label from backend data
  const personaLabel = useMemo(() => {
    return generatePersonaLabel(personaData?.name, persona);
  }, [personaData?.name, persona]);

  // Get voice and model from persona or message metadata
  const personaVoice = message.metadata?.voice || personaData?.voice;
  const personaModel = personaData?.model;

  // Copy to clipboard action
  const copyToClipboard = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(message.content);
    } catch (error) {
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = message.content;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
    }
  }, [message.content]);

  return {
    isUser,
    displayName,
    personaStyle,
    personaLabel,
    persona,
    personaVoice,
    personaModel,
    copyToClipboard,
  };
}

/**
 * Simplified hook for TV display (no auth/personas fetch needed)
 */
export function useMessageSimple(options: UseMessageOptions) {
  const { message, persona: explicitPersona } = options;

  const persona = explicitPersona || message.metadata?.tone || 'waiting_room_host';
  const isUser = message.role === 'user';
  const personaStyle = getPersonaStyle(persona);

  return {
    isUser,
    persona,
    personaStyle,
    displayName: isUser ? 'Usuario' : 'FREE-INTELLIGENCE',
    personaLabel: 'FREE-INTELLIGENCE',
  };
}
