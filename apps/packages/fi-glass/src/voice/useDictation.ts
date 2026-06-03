'use client';

/**
 * fi-glass · useDictation — STT orchestration that consumes a VoiceAdapter.
 *
 * Drives the recording engine (useRecorder + useAudioAnalysis), feeds each
 * chunk to `adapter.transcribe`, and accumulates the running transcript. fi-glass
 * never touches endpoints/auth/sessions — the adapter owns all of that. An app
 * with no `transcribe` capability (or no adapter) simply gets no dictation.
 *
 * Chunking is the consumer's call (`timeSliceMs`): a streaming backend uses the
 * 0-based `index`; a one-shot backend (single big chunk on stop) ignores it.
 */

import { useCallback, useState } from 'react';
import type { VoiceAdapter } from '@free-intelligence/core';
import { useRecorder } from './useRecorder';
import { useAudioAnalysis } from './useAudioAnalysis';

export interface UseDictationOptions {
  /** Chunk interval in ms handed to the recorder (default 30s). */
  timeSliceMs?: number;
  /** Specific audio input device id. */
  deviceId?: string | null;
  /** Called with the full accumulated transcript on each chunk. */
  onTranscriptUpdate?: (full: string) => void;
  /** Called on recording/transcription failure. */
  onError?: (message: string) => void;
}

export interface UseDictationReturn {
  isRecording: boolean;
  recordingTime: number;
  audioLevel: number;
  isSilent: boolean;
  liveTranscript: string;
  isTranscribing: boolean;
  startRecording: () => Promise<void>;
  stopRecording: () => Promise<void>;
}

export function useDictation(
  adapter: VoiceAdapter | undefined,
  opts: UseDictationOptions = {}
): UseDictationReturn {
  const { timeSliceMs = 30000, deviceId = null, onTranscriptUpdate, onError } = opts;
  const [liveTranscript, setLiveTranscript] = useState('');
  const [isTranscribing, setIsTranscribing] = useState(false);

  const handleChunk = useCallback(
    async (blob: Blob, chunkNumber: number) => {
      if (!adapter?.transcribe) return;
      setIsTranscribing(true);
      try {
        const { text } = await adapter.transcribe(blob, { index: chunkNumber });
        if (text) {
          setLiveTranscript((prev) => {
            const updated = prev ? `${prev} ${text}` : text;
            onTranscriptUpdate?.(updated);
            return updated;
          });
        }
      } catch (err) {
        onError?.(err instanceof Error ? err.message : 'transcription failed');
      } finally {
        setIsTranscribing(false);
      }
    },
    [adapter, onTranscriptUpdate, onError]
  );

  const { isRecording, recordingTime, currentStream, startRecording, stopRecording } =
    useRecorder({
      onChunk: handleChunk,
      onError,
      timeSlice: timeSliceMs,
      deviceId,
    });

  const { audioLevel, isSilent } = useAudioAnalysis(currentStream, {
    isActive: isRecording,
  });

  const start = useCallback(async () => {
    setLiveTranscript('');
    await startRecording();
  }, [startRecording]);

  const stop = useCallback(async () => {
    await stopRecording();
  }, [stopRecording]);

  return {
    isRecording,
    recordingTime,
    audioLevel,
    isSilent,
    liveTranscript,
    isTranscribing,
    startRecording: start,
    stopRecording: stop,
  };
}
