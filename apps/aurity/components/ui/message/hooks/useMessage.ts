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

  // Consolidated persona lookup (single useMemo for all persona-derived values)
  // This avoids re-memoizing on every render when personas array updates
  const personaInfo = useMemo(() => {
    const style = getPersonaStyle(persona);
    const data = personas?.find((p) => p.id === persona);
    const label = generatePersonaLabel(data?.name, persona);

    return {
      style,
      data,
      label,
      voice: message.metadata?.voice || data?.voice,
      model: data?.model,
    };
  }, [personas, persona, message.metadata?.voice]);

  // Destructure for cleaner return
  const personaStyle = personaInfo.style;
  const personaLabel = personaInfo.label;
  const personaVoice = personaInfo.voice;
  const personaModel = personaInfo.model;

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
 * Lightweight hook for TV/broadcast displays
 *
 * Use when:
 * - WaitingRoomHost, ContentRenderer (no personalization needed)
 * - Static displays without user context
 *
 * Skips:
 * - Auth/user profile fetching
 * - Backend personas lookup
 * - Voice/model metadata
 *
 * Use `useMessage` when you need full persona context (ChatMessage, OnboardingMessage).
 */
export function useMessageTV(options: UseMessageOptions) {
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

/**
 * @deprecated Use `useMessageTV` instead. Renamed for clarity.
 */
export const useMessageSimple = useMessageTV;
