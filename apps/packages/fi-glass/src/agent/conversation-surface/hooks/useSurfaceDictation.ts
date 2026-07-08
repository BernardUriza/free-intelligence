'use client';

/**
 * fi-glass · conversation-surface/useSurfaceDictation — the surface's dictation
 * (STT) wiring. Only live when the adapter can transcribe. The composer text
 * typed before recording is captured as a prefix so dictation appends to it
 * instead of clobbering it. useDictation is a no-op without `transcribe`, so
 * calling it unconditionally (hooks rule) is safe.
 */

import { useRef } from 'react';
import type { VoiceAdapter } from '@free-intelligence/core';
import { useDictation, type UseDictationReturn } from '../../../voice';

export interface SurfaceDictation {
  /** True when the adapter exposes `transcribe` — gates every mic affordance. */
  micAvailable: boolean;
  isRecording: boolean;
  isTranscribing: boolean;
  /** Live, normalized (0..1) frequency bands — feed AudioVisualizer `levels`. */
  bands: number[];
  startDictation: () => void;
  stopDictation: () => void;
}

export function useSurfaceDictation(options: {
  voiceAdapter: VoiceAdapter | undefined;
  input: string;
  setInput: (value: string) => void;
  onVoiceError?: (message: string) => void;
}): SurfaceDictation {
  const { voiceAdapter, input, setInput, onVoiceError } = options;
  const micAvailable = typeof voiceAdapter?.transcribe === 'function';
  const baseInputRef = useRef('');
  const dictation: UseDictationReturn = useDictation(voiceAdapter, {
    onTranscriptUpdate: (full) => {
      const base = baseInputRef.current;
      setInput(base ? `${base} ${full}` : full);
    },
    onError: onVoiceError,
  });
  return {
    micAvailable,
    isRecording: dictation.isRecording,
    isTranscribing: dictation.isTranscribing,
    bands: dictation.bands,
    startDictation: () => {
      baseInputRef.current = input;
      void dictation.startRecording();
    },
    stopDictation: () => void dictation.stopRecording(),
  };
}
