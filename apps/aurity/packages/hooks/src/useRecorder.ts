/**
 * useRecorder Hook
 *
 * Maneja la grabación de audio con arquitectura dual recorder:
 * - Chunked recorder: Para transcripción en tiempo real (chunks de 3s)
 * - Continuous recorder: Para audio completo sin chunks (playback final)
 *
 * Extraído de ConversationCapture durante refactoring incremental.
 *
 * @example
 * const { isRecording, recordingTime, startRecording, stopRecording, fullAudioBlob, currentStream } =
 *   useRecorder({
 *     onChunk: async (blob, chunkNumber) => {
 *       // Process chunk (upload, transcribe, etc.)
 *     },
 *     onError: (error) => console.error(error)
 *   });
 */

import { useState, useRef, useCallback } from 'react';
import { makeRecorder } from '@/lib/recording/makeRecorder';
import { createLogger } from '@/lib/internal/logger';

const log = createLogger('Recorder');

interface UseRecorderConfig {
  onChunk: (blob: Blob, chunkNumber: number) => Promise<void> | void;
  onError?: (error: string) => void;
  timeSlice?: number;
  sampleRate?: number;
  channels?: number;
  /** Optional external MediaStream (e.g., from demo audio) instead of microphone */
  externalStream?: MediaStream | null;
}

interface UseRecorderReturn {
  isRecording: boolean;
  recordingTime: number;
  currentStream: MediaStream | null;
  fullAudioBlob: Blob | null;
  fullAudioUrl: string | null;
  startRecording: () => Promise<void>;
  stopRecording: () => Promise<Blob | null>;
}

export function useRecorder(config: UseRecorderConfig): UseRecorderReturn {
  const {
    onChunk,
    onError,
    timeSlice = 3000,
    sampleRate = 16000,
    channels = 1,
    externalStream = null,
  } = config;

  // State
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [fullAudioBlob, setFullAudioBlob] = useState<Blob | null>(null);
  const [fullAudioUrl, setFullAudioUrl] = useState<string | null>(null);
  const [currentStream, setCurrentStream] = useState<MediaStream | null>(null);

  // Refs
  const recorderRef = useRef<any>(null); // Chunked recorder
  const continuousRecorderRef = useRef<any>(null); // Continuous recorder
  const currentStreamRef = useRef<MediaStream | null>(null);
  const recordingTimerRef = useRef<NodeJS.Timeout | null>(null);
  const fullAudioUrlRef = useRef<string | null>(null);
  const chunkNumberRef = useRef<number>(0);

  // Start recording with dual recorders
  const startRecording = useCallback(async () => {
    try {
      // Reset state
      chunkNumberRef.current = 0;
      setRecordingTime(0);
      setFullAudioBlob(null);

      // Clean up previous audio URL
      if (fullAudioUrlRef.current) {
        URL.revokeObjectURL(fullAudioUrlRef.current);
        fullAudioUrlRef.current = null;
        setFullAudioUrl(null);
      }

      // Use external stream (demo mode) OR request microphone access
      let stream: MediaStream;
      if (externalStream) {
        log.debug('Using external stream (demo mode)');
        stream = externalStream;
      } else {
        log.debug('Requesting microphone access');

        try {
          // Add timeout - getUserMedia can hang forever if user ignores prompt or macOS blocks
          const timeoutMs = 15000;
          const timeoutPromise = new Promise<never>((_, reject) => {
            setTimeout(() => {
              reject(new Error(
                'Microphone permission timeout (15s). Check browser microphone permissions and restart browser after granting.'
              ));
            }, timeoutMs);
          });

          stream = await Promise.race([
            navigator.mediaDevices.getUserMedia({ audio: true }),
            timeoutPromise
          ]);
          log.debug('Microphone access granted');
        } catch (micError) {
          log.error('Microphone access failed', { error: String(micError) });
          throw micError;
        }
      }
      currentStreamRef.current = stream;
      setCurrentStream(stream);

      // ========================================================================
      // CHUNKED RECORDER: For real-time transcription (3s chunks)
      // ========================================================================
      const chunkedRecorder = await makeRecorder(
        stream,
        async (blob: Blob) => {
          const chunkNumber = chunkNumberRef.current++;
          log.debug('Chunk received', { chunk: chunkNumber, bytes: blob.size });
          await onChunk(blob, chunkNumber);
        },
        {
          timeSlice,
          sampleRate,
          channels,
        }
      );

      recorderRef.current = chunkedRecorder;
      log.debug('Chunked recorder ready', { kind: chunkedRecorder.kind });
      chunkedRecorder.start();

      // ========================================================================
      // CONTINUOUS RECORDER: For full audio without chunks
      // ========================================================================
      // NOTE: Without timeSlice, the callback is NOT called during recording.
      // The blob is returned by .stop() Promise instead.
      const continuousRecorder = await makeRecorder(
        stream,
        () => {}, // Empty callback - blob comes from .stop() return value
        {
          // NO timeSlice = records continuously until stop()
          sampleRate,
          channels,
        }
      );

      continuousRecorderRef.current = continuousRecorder;
      continuousRecorder.start();
      log.debug('Continuous recorder started');

      // Update state
      setIsRecording(true);

      // Start timer
      recordingTimerRef.current = setInterval(() => {
        setRecordingTime((prev) => prev + 1);
      }, 1000);
    } catch (err) {
      const errorMessage =
        err instanceof Error
          ? err.message
          : 'No se pudo acceder al micrófono. Por favor, verifica los permisos.';
      log.error('Start failed', { error: String(err) });
      if (onError) {
        onError(errorMessage);
      }
    }
  }, [onChunk, onError, timeSlice, sampleRate, channels, externalStream]);

  // Stop recording and capture full audio blob
  // CRITICAL: Stops microphone IMMEDIATELY, then processes in background
  const stopRecording = useCallback(async () => {
    try {
      // ========================================================================
      // STEP 1: IMMEDIATE CLEANUP (no awaits - synchronous)
      // ========================================================================

      // Stop timer immediately
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
        recordingTimerRef.current = null;
      }

      // Update UI state IMMEDIATELY (user sees recording stopped)
      setIsRecording(false);

      // ========================================================================
      // STEP 2: STOP MICROPHONE STREAM IMMEDIATELY (CRITICAL for browser indicator)
      // ========================================================================
      // This MUST happen before any await to release the microphone icon in browser
      if (currentStreamRef.current) {
        currentStreamRef.current.getTracks().forEach((track) => track.stop());
        currentStreamRef.current = null;
        setCurrentStream(null);
      }

      // ========================================================================
      // STEP 3: STOP RECORDERS (can be async, microphone already released)
      // ========================================================================
      let fullBlob: Blob | null = null;

      // Stop continuous recorder (for full audio blob)
      if (continuousRecorderRef.current) {
        try {
          fullBlob = await continuousRecorderRef.current.stop();

          if (fullBlob && fullBlob.size > 0) {
            // Create local URL for immediate playback
            if (fullAudioUrlRef.current) {
              URL.revokeObjectURL(fullAudioUrlRef.current);
            }
            const audioUrl = URL.createObjectURL(fullBlob);
            fullAudioUrlRef.current = audioUrl;
            setFullAudioUrl(audioUrl);
            setFullAudioBlob(fullBlob);
          }
        } catch (err) {
          log.warn('Continuous recorder stop error (non-critical)', { error: String(err) });
        }
        continuousRecorderRef.current = null;
      }

      // Stop chunked recorder
      if (recorderRef.current) {
        try {
          const lastChunk = await recorderRef.current.stop();

          // Process final chunk in BACKGROUND (fire-and-forget)
          // Don't await - user already sees recording as stopped
          if (lastChunk && lastChunk.size > 0) {
            const finalChunkNumber = chunkNumberRef.current++;
            log.debug('Processing final chunk', { chunk: finalChunkNumber });
            try {
              const result = onChunk(lastChunk, finalChunkNumber);
              if (result instanceof Promise) {
                result.catch((err: Error) => {
                  log.error('Final chunk processing failed', { error: String(err) });
                });
              }
            } catch (err) {
              log.error('Final chunk processing failed', { error: String(err) });
            }
          }
        } catch (err) {
          log.warn('Chunked recorder stop error (non-critical)', { error: String(err) });
        }
        recorderRef.current = null;
      }

      return fullBlob;
    } catch (err) {
      log.error('Stop failed', { error: String(err) });

      // Even on error, ensure microphone is released
      if (currentStreamRef.current) {
        currentStreamRef.current.getTracks().forEach((track) => track.stop());
        currentStreamRef.current = null;
        setCurrentStream(null);
      }
      setIsRecording(false);

      if (onError) {
        onError(err instanceof Error ? err.message : 'Error al detener grabación');
      }
      return null;
    }
  }, [onChunk, onError]);

  return {
    isRecording,
    recordingTime,
    currentStream,
    fullAudioBlob,
    fullAudioUrl,
    startRecording,
    stopRecording,
  };
}
