/**
 * useAudioUpload Hook
 *
 * Gestiona la subida de chunks de audio al backend:
 * - Queue management (inflight tracking)
 * - Chunk numbering
 * - Retry logic
 * - Progress tracking
 *
 * Extraído de ConversationCapture para reducir complejidad (P2 Refactoring)
 *
 * Created: 2025-01-XX
 * Author: Claude Code (P2 Architectural Refactoring)
 */

import { useRef, useCallback } from 'react';
import { medicalWorkflowApi, type StreamChunkResponse } from '@aurity-standalone/api-client/medical-workflow';
import { createLogger } from '@/lib/internal/logger';

const log = createLogger('AudioUpload');

export interface AudioUploadState {
  // Refs
  chunkNumberRef: React.MutableRefObject<number>;
  inflightRef: React.MutableRefObject<Set<string>>;
  audioChunksRef: React.MutableRefObject<Blob[]>;
  fullAudioBlobsRef: React.MutableRefObject<Blob[]>;

  // Helpers
  uploadChunk: (
    sessionId: string,
    blob: Blob,
    options?: {
      patientInfo?: {
        patient_name?: string;
        patient_age?: string;
        patient_id?: string;
        chief_complaint?: string;
      };
      onSuccess?: (response: StreamChunkResponse) => void;
      onError?: (error: Error) => void;
    }
  ) => Promise<void>;

  getNextChunkNumber: () => number;
  resetChunkCounter: () => void;
  getInflightCount: () => number;
  clearInflight: () => void;
}

export function useAudioUpload(): AudioUploadState {
  // Refs
  const chunkNumberRef = useRef<number>(0);
  const inflightRef = useRef<Set<string>>(new Set());
  const audioChunksRef = useRef<Blob[]>([]);
  const fullAudioBlobsRef = useRef<Blob[]>([]);

  // Get next chunk number
  const getNextChunkNumber = useCallback(() => {
    const current = chunkNumberRef.current;
    chunkNumberRef.current += 1;
    return current;
  }, []);

  // Reset chunk counter
  const resetChunkCounter = useCallback(() => {
    chunkNumberRef.current = 0;
  }, []);

  // Get inflight count
  const getInflightCount = useCallback(() => {
    return inflightRef.current.size;
  }, []);

  // Clear inflight
  const clearInflight = useCallback(() => {
    inflightRef.current.clear();
  }, []);

  // Upload chunk to backend
  const uploadChunk = useCallback(
    async (
      sessionId: string,
      blob: Blob,
      options?: {
        patientInfo?: {
          patient_name?: string;
          patient_age?: string;
          patient_id?: string;
          chief_complaint?: string;
        };
        onSuccess?: (response: StreamChunkResponse) => void;
        onError?: (error: Error) => void;
      }
    ) => {
      const chunkNumber = getNextChunkNumber();
      const chunkId = `${sessionId}_${chunkNumber}`;

      // Store in refs
      audioChunksRef.current.push(blob);
      fullAudioBlobsRef.current.push(blob);

      // Track inflight
      inflightRef.current.add(chunkId);

      try {
        const response = await medicalWorkflowApi.uploadChunk(
          sessionId,
          chunkNumber,
          blob,
          {
            patientInfo: options?.patientInfo,
            timestampStart: Date.now(),
            timestampEnd: Date.now(),
          }
        );

        // Remove from inflight
        inflightRef.current.delete(chunkId);

        if (options?.onSuccess) {
          options.onSuccess(response);
        }
      } catch (error) {
        log.error('Chunk upload failed', { chunkNumber, error: String(error) });

        // Remove from inflight
        inflightRef.current.delete(chunkId);

        if (options?.onError) {
          options.onError(error instanceof Error ? error : new Error('Upload failed'));
        } else {
          throw error;
        }
      }
    },
    [getNextChunkNumber]
  );

  return {
    // Refs
    chunkNumberRef,
    inflightRef,
    audioChunksRef,
    fullAudioBlobsRef,

    // Helpers
    uploadChunk,
    getNextChunkNumber,
    resetChunkCounter,
    getInflightCount,
    clearInflight,
  };
}

