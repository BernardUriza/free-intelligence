'use client';

/**
 * fi-glass · useVoice — TTS orchestration that consumes a VoiceAdapter.
 *
 * Drop-in compatible with aurity's former useAudioPlayer (same return shape),
 * but every synthesis goes through `adapter.synthesize` instead of a hardcoded
 * endpoint. fi-glass stays backend-agnostic; the app's adapter owns the I/O,
 * auth, provider routing and any state-machine/consent logic INSIDE synthesize.
 *
 * Resolves AudioSource transparently: a Blob is object-URL'd, a { url } is used
 * as-is (keeps streaming TTS open).
 */

import { useCallback, useState } from 'react';
import type { VoiceAdapter, AudioSource } from '@free-intelligence/core';

export interface UseVoiceOptions {
  /** Called when synthesis fails (app decides logging/reporting). */
  onError?: (error: unknown, context: string) => void;
}

export interface UseVoiceReturn {
  isOpen: boolean;
  isLoading: boolean;
  audioUrl: string | null;
  voiceName: string;
  isUserMessage: boolean;
  currentVoice: string;
  currentText: string;
  generateAudio: (text: string, voice?: string, isUser?: boolean) => Promise<void>;
  changeVoice: (newVoice: string) => Promise<void>;
  close: () => void;
}

/** Blob -> object URL; { url } -> url. */
function toUrl(src: AudioSource): string {
  return src instanceof Blob ? URL.createObjectURL(src) : src.url;
}

export function useVoice(
  adapter: VoiceAdapter | undefined,
  opts: UseVoiceOptions = {}
): UseVoiceReturn {
  const { onError } = opts;
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [voiceName, setVoiceName] = useState('nova');
  const [isUserMessage, setIsUserMessage] = useState(false);
  const [currentVoice, setCurrentVoice] = useState('nova');
  const [currentText, setCurrentText] = useState('');

  const getVoiceDisplayName = useCallback(
    (voiceId: string): string => {
      const found = adapter?.availableVoices?.find((v) => v.id === voiceId);
      if (found) return found.label.split(' ')[0];
      const match = voiceId.match(/([A-Z][a-z]+)Neural$/);
      return match ? match[1] : voiceId;
    },
    [adapter]
  );

  const generateAudio = useCallback(
    async (text: string, voice: string = 'nova', isUser: boolean = false) => {
      if (!adapter?.synthesize) return;
      setCurrentText(text);
      setCurrentVoice(voice);
      setIsUserMessage(isUser);
      setVoiceName(getVoiceDisplayName(voice));

      setIsOpen(true);
      setIsLoading(true);
      setAudioUrl(null);

      try {
        const src = await adapter.synthesize(text, voice);
        setAudioUrl(toUrl(src));
      } catch (error) {
        onError?.(error, 'useVoice:TTS');
        setIsOpen(false);
      } finally {
        setIsLoading(false);
      }
    },
    [adapter, getVoiceDisplayName, onError]
  );

  const changeVoice = useCallback(
    async (newVoice: string) => {
      if (!currentText || !adapter?.synthesize) return;
      setCurrentVoice(newVoice);
      setVoiceName(getVoiceDisplayName(newVoice));
      setIsLoading(true);

      if (audioUrl) URL.revokeObjectURL(audioUrl);
      setAudioUrl(null);

      try {
        const src = await adapter.synthesize(currentText, newVoice);
        setAudioUrl(toUrl(src));
      } catch (error) {
        onError?.(error, 'useVoice:VoiceChange');
      } finally {
        setIsLoading(false);
      }
    },
    [adapter, audioUrl, currentText, getVoiceDisplayName, onError]
  );

  const close = useCallback(() => {
    setIsOpen(false);
    setAudioUrl(null);
    setIsLoading(false);
    setCurrentText('');
    setIsUserMessage(false);
  }, []);

  return {
    isOpen,
    isLoading,
    audioUrl,
    voiceName,
    isUserMessage,
    currentVoice,
    currentText,
    generateAudio,
    changeVoice,
    close,
  };
}
