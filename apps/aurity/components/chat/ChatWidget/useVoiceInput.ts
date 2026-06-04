/**
 * useVoiceInput Hook
 *
 * Wraps useChatVoiceRecorder with message state integration.
 * SOLID: Single Responsibility - only voice input handling.
 */

import { useRef, useMemo, useCallback } from 'react';
import { createLogger } from '@/lib/internal/logger';
import { useChatVoiceRecorder } from '@/hooks/useChatVoiceRecorder';
import type { VoiceRecordingState } from 'fi-glass/shell';

const log = createLogger('VoiceInput');

export interface UseVoiceInputOptions {
  userId: string;
  message: string;
  setMessage: (message: string) => void;
}

export interface UseVoiceInputReturn {
  voiceState: VoiceRecordingState;
  startVoice: () => Promise<void>;
  stopVoice: () => Promise<void>;
  toggleVoice: () => void;
}

export function useVoiceInput({
  userId,
  message,
  setMessage,
}: UseVoiceInputOptions): UseVoiceInputReturn {
  // Capture message before recording (for append behavior)
  const messageBeforeRecordingRef = useRef('');

  const {
    isRecording,
    recordingTime,
    audioLevel,
    isSilent,
    isTranscribing,
    startRecording,
    stopRecording,
  } = useChatVoiceRecorder({
    userId,
    onTranscriptUpdate: (transcript) => {
      // Append to existing message (captured before recording started)
      const combined = messageBeforeRecordingRef.current
        ? `${messageBeforeRecordingRef.current} ${transcript}`.trim()
        : transcript;
      setMessage(combined);
    },
    onError: (error) => {
      log.error('Voice input error', { error: String(error) });
    },
  });

  const voiceState = useMemo<VoiceRecordingState>(() => ({
    isRecording,
    isTranscribing,
    audioLevel,
    isSilent,
    recordingTime,
  }), [isRecording, isTranscribing, audioLevel, isSilent, recordingTime]);

  const startVoice = useCallback(async () => {
    messageBeforeRecordingRef.current = message;
    await startRecording();
  }, [message, startRecording]);

  const stopVoice = useCallback(async () => {
    await stopRecording();
  }, [stopRecording]);

  const toggleVoice = useCallback(() => {
    if (isRecording) {
      stopVoice();
    } else {
      startVoice();
    }
  }, [isRecording, startVoice, stopVoice]);

  return {
    voiceState,
    startVoice,
    stopVoice,
    toggleVoice,
  };
}
