/**
 * useChatPreferences Hook
 *
 * Manages user preferences: response mode, persona, persisted to localStorage.
 * SOLID: Single Responsibility - only preference management.
 */

import { useState, useEffect, useCallback } from 'react';
import type { ResponseMode, PersonaType } from '../ChatToolbar';
import { usePersonas } from '@aurity-standalone/hooks/usePersonas';

const STORAGE_KEYS = {
  RESPONSE_MODE: 'fi_response_mode',
  PERSONA: 'fi_persona',
  SHOW_THINKING: 'fi_show_thinking',
  AUDIO_INPUT_DEVICE: 'fi_audio_input_device',
} as const;

export interface UseChatPreferencesReturn {
  responseMode: ResponseMode;
  selectedPersona: PersonaType | null;
  showThinking: boolean;
  personasLoading: boolean;
  audioInputDevice: string | null;
  toggleResponseMode: () => void;
  setPersona: (persona: PersonaType) => void;
  toggleShowThinking: () => void;
  setAudioInputDevice: (deviceId: string | null) => void;
}

export function useChatPreferences(): UseChatPreferencesReturn {
  const { personas, loading: personasLoading } = usePersonas();
  const [responseMode, setResponseMode] = useState<ResponseMode>('explanatory');
  const [selectedPersona, setSelectedPersona] = useState<PersonaType | null>(null);
  const [showThinking, setShowThinking] = useState<boolean>(true);
  const [audioInputDevice, setAudioInputDeviceState] = useState<string | null>(null);

  // Load preferences on mount
  useEffect(() => {
    const savedMode = localStorage.getItem(STORAGE_KEYS.RESPONSE_MODE) as ResponseMode | null;
    if (savedMode) {
      setResponseMode(savedMode);
    }

    const savedShowThinking = localStorage.getItem(STORAGE_KEYS.SHOW_THINKING);
    if (savedShowThinking !== null) {
      setShowThinking(savedShowThinking === 'true');
    }

    const savedAudioDevice = localStorage.getItem(STORAGE_KEYS.AUDIO_INPUT_DEVICE);
    if (savedAudioDevice) {
      setAudioInputDeviceState(savedAudioDevice);
    }
  }, []);

  // Initialize selectedPersona when personas are loaded
  useEffect(() => {
    // Wait for personas to load
    if (personasLoading || personas.length === 0) return;

    // Try to load from localStorage
    const savedPersona = localStorage.getItem(STORAGE_KEYS.PERSONA) as PersonaType | null;

    // Validate that persona exists in backend
    const personaExists = personas.some(p => p.id === savedPersona);

    if (savedPersona && personaExists) {
      setSelectedPersona(savedPersona);
    } else {
      // Fallback: general_assistant if exists, otherwise first persona
      const defaultExists = personas.some(p => p.id === 'general_assistant');
      setSelectedPersona(defaultExists ? 'general_assistant' : personas[0]?.id || null);
    }
  }, [personasLoading, personas]);

  const toggleResponseMode = useCallback(() => {
    const newMode: ResponseMode = responseMode === 'explanatory' ? 'concise' : 'explanatory';
    setResponseMode(newMode);
    localStorage.setItem(STORAGE_KEYS.RESPONSE_MODE, newMode);
  }, [responseMode]);

  const setPersona = useCallback((newPersona: PersonaType) => {
    if (newPersona === selectedPersona) return;

    setSelectedPersona(newPersona);
    localStorage.setItem(STORAGE_KEYS.PERSONA, newPersona);
  }, [selectedPersona]);

  const toggleShowThinking = useCallback(() => {
    const newValue = !showThinking;
    setShowThinking(newValue);
    localStorage.setItem(STORAGE_KEYS.SHOW_THINKING, String(newValue));
  }, [showThinking]);

  const setAudioInputDevice = useCallback((deviceId: string | null) => {
    setAudioInputDeviceState(deviceId);
    if (deviceId === null) {
      localStorage.removeItem(STORAGE_KEYS.AUDIO_INPUT_DEVICE);
    } else {
      localStorage.setItem(STORAGE_KEYS.AUDIO_INPUT_DEVICE, deviceId);
    }
  }, [audioInputDevice]);

  return {
    responseMode,
    selectedPersona,
    showThinking,
    personasLoading,
    audioInputDevice,
    toggleResponseMode,
    setPersona,
    toggleShowThinking,
    setAudioInputDevice,
  };
}
