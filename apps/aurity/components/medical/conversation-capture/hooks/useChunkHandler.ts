/**
 * useChunkHandler Hook
 *
 * Handles audio chunk upload and transcription processing.
 * Manages deduplication, silence detection, and backend communication.
 */

import { useCallback, useRef } from 'react';
import { medicalWorkflowApi } from '@aurity-standalone/api-client/medical-workflow';
import { AUDIO_CONFIG } from '@/lib/audio/constants';
import { guessExt } from '@/lib/recording/makeRecorder';
import type { PatientInfo } from '../../../medical/PatientInfoModal';

interface UseChunkHandlerProps {
  sessionIdRef: React.MutableRefObject<string>;
  chunkNumberRef: React.MutableRefObject<number>;
  audioLevelRef: React.MutableRefObject<number>;
  isSilentRef: React.MutableRefObject<boolean>;
  patientInfo: PatientInfo | null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  setChunkStatuses: React.Dispatch<React.SetStateAction<any[]>>;
  addLog: (message: string) => void;
  pollJobStatus: (sessionId: string, chunkNumber: number) => Promise<string | null>;
  addTranscriptionChunk: (text: string) => void;
}

interface UseChunkHandlerResult {
  handleChunk: (blob: Blob, localChunkNumber: number) => Promise<void>;
  inflightRef: React.MutableRefObject<Set<string>>;
}

export function useChunkHandler({
  sessionIdRef,
  chunkNumberRef,
  audioLevelRef: _audioLevelRef,
  isSilentRef,
  patientInfo,
  setChunkStatuses,
  addLog,
  pollJobStatus,
  addTranscriptionChunk,
}: UseChunkHandlerProps): UseChunkHandlerResult {
  const inflightRef = useRef<Set<string>>(new Set());

  const handleChunk = useCallback(
    async (blob: Blob, _localChunkNumber: number) => {
      // Use global counter for pause/resume support
      const chunkNumber = chunkNumberRef.current;

      // Silence detection
      const currentIsSilent = isSilentRef.current;

      if (currentIsSilent) {
        console.log(`[CHUNK ${chunkNumber}] ⏭️ Skipped (silence)`);
        return;
      }

      // Increment only for non-silent chunks
      chunkNumberRef.current++;

      // Deduplication
      const key = `${sessionIdRef.current}:${chunkNumber}`;
      if (inflightRef.current.has(key)) {
        console.warn(`[CHUNK ${chunkNumber}] ⚠️ Already processing, skipping duplicate`);
        return;
      }
      inflightRef.current.add(key);

      try {
        const timeSlice = AUDIO_CONFIG.TIME_SLICE;
        const timestampStart = chunkNumber * (timeSlice / 1000);
        const timestampEnd = timestampStart + timeSlice / 1000;

        console.log(`[CHUNK ${chunkNumber}] 📤 Uploading ${(blob.size / 1024).toFixed(1)}KB`);

        // Track chunk as uploading
        setChunkStatuses((prev) => [
          ...prev,
          {
            index: chunkNumber,
            status: 'uploading' as const,
            startTime: Date.now(),
          },
        ]);
        addLog(`📤 Enviando chunk ${chunkNumber} (${(blob.size / 1024).toFixed(1)}KB)`);

        const result = await medicalWorkflowApi.uploadChunk(
          sessionIdRef.current,
          chunkNumber,
          blob,
          {
            timestampStart,
            timestampEnd,
            filename: `${chunkNumber}${guessExt(blob.type)}`,
            ...(chunkNumber === 0 && patientInfo ? { patientInfo } : {}),
          }
        );

        // Direct transcription
        if (result.transcript) {
          addTranscriptionChunk(result.transcript);
        }
        // Worker polling
        else if ((result.status === 'pending' || result.status === 'in_progress') && result.session_id) {
          const transcript = await pollJobStatus(sessionIdRef.current, chunkNumber);
          if (transcript) {
            addTranscriptionChunk(transcript);
          }
        } else {
          console.warn(`[CHUNK ${chunkNumber}] ⚠️ Unexpected response format:`, result);
        }
      } catch (err) {
        console.error(`[CHUNK ${chunkNumber}] ❌ Processing failed:`, err);
      } finally {
        inflightRef.current.delete(key);
      }
    },
    [
      sessionIdRef,
      chunkNumberRef,
      isSilentRef,
      patientInfo,
      setChunkStatuses,
      addLog,
      pollJobStatus,
      addTranscriptionChunk,
    ]
  );

  return {
    handleChunk,
    inflightRef,
  };
}
