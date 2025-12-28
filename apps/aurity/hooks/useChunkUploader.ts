/**
 * useChunkUploader - Audio chunk upload logic hook
 *
 * Extracts chunk upload, retry, and status tracking from ConversationCapture
 * Handles: chunk queue, parallel uploads, retry logic, status polling
 *
 * Created: 2025-11-15
 * Part of: ConversationCapture decomposition refactoring
 */

import { useState, useRef, useCallback } from 'react';
import { medicalWorkflowApi } from '@aurity-standalone/api-client/medical-workflow';

export interface ChunkStatus {
  chunk_number: number;
  status: 'pending' | 'uploading' | 'completed' | 'failed';
  audio_hash?: string;
  transcript?: string;
  error?: string;
  retries?: number;
}

export interface UseChunkUploaderReturn {
  // State
  chunkStatuses: ChunkStatus[];
  estimatedSecondsRemaining: number;
  isUploading: boolean;

  // Actions
  uploadChunk: (sessionId: string, chunkNumber: number, audioBlob: Blob) => Promise<void>;
  getChunkStatus: (chunkNumber: number) => ChunkStatus | undefined;
  resetChunks: () => void;

  // Stats
  totalChunks: number;
  completedChunks: number;
  failedChunks: number;
  pendingChunks: number;
}

export interface UseChunkUploaderOptions {
  maxRetries?: number;
  retryDelay?: number;
  onUploadComplete?: (chunkNumber: number) => void;
  onUploadError?: (chunkNumber: number, error: string) => void;
}

export function useChunkUploader(
  options: UseChunkUploaderOptions = {}
): UseChunkUploaderReturn {
  const {
    maxRetries = 3,
    retryDelay = 1000,
    onUploadComplete,
    onUploadError,
  } = options;

  // State
  const [chunkStatuses, setChunkStatuses] = useState<ChunkStatus[]>([]);
  const [estimatedSecondsRemaining, setEstimatedSecondsRemaining] = useState(0);
  const [isUploading, setIsUploading] = useState(false);

  // Refs
  const uploadQueueRef = useRef<Set<number>>(new Set());

  // Update chunk status
  const updateChunkStatus = useCallback((chunkNumber: number, updates: Partial<ChunkStatus>) => {
    setChunkStatuses((prev) => {
      const existing = prev.find((c) => c.chunk_number === chunkNumber);

      if (existing) {
        return prev.map((c) =>
          c.chunk_number === chunkNumber ? { ...c, ...updates } : c
        );
      } else {
        return [
          ...prev,
          {
            chunk_number: chunkNumber,
            status: 'pending',
            retries: 0,
            ...updates,
          },
        ];
      }
    });
  }, []);

  // Upload chunk with retry logic
  const uploadChunk = useCallback(
    async (sessionId: string, chunkNumber: number, audioBlob: Blob) => {
      // Prevent duplicate uploads
      if (uploadQueueRef.current.has(chunkNumber)) {
        console.log(`[ChunkUploader] Chunk ${chunkNumber} already in queue, skipping`);
        return;
      }

      uploadQueueRef.current.add(chunkNumber);
      setIsUploading(true);

      // Initialize chunk status
      updateChunkStatus(chunkNumber, { status: 'pending', retries: 0 });

      let attempts = 0;
      let lastError: Error | null = null;

      while (attempts < maxRetries) {
        try {
          updateChunkStatus(chunkNumber, { status: 'uploading' });

          console.log(`[ChunkUploader] Uploading chunk ${chunkNumber} (attempt ${attempts + 1}/${maxRetries})`);

          const result = await medicalWorkflowApi.uploadChunk(
            sessionId,
            chunkNumber,
            audioBlob
          );

          // Success
          updateChunkStatus(chunkNumber, {
            status: 'completed',
            audio_hash: result.audio_hash,
            transcript: result.transcript,
          });

          uploadQueueRef.current.delete(chunkNumber);

          if (onUploadComplete) {
            onUploadComplete(chunkNumber);
          }

          console.log(`[ChunkUploader] ✅ Chunk ${chunkNumber} uploaded successfully`);
          break; // Success, exit retry loop
        } catch (error) {
          lastError = error as Error;
          attempts++;

          console.error(
            `[ChunkUploader] ❌ Chunk ${chunkNumber} failed (attempt ${attempts}/${maxRetries}):`,
            error
          );

          updateChunkStatus(chunkNumber, { retries: attempts });

          if (attempts < maxRetries) {
            // Wait before retry (exponential backoff)
            const delay = retryDelay * Math.pow(2, attempts - 1);
            console.log(`[ChunkUploader] Retrying chunk ${chunkNumber} in ${delay}ms...`);
            await new Promise((resolve) => setTimeout(resolve, delay));
          }
        }
      }

      // Failed after all retries
      if (attempts >= maxRetries && lastError) {
        updateChunkStatus(chunkNumber, {
          status: 'failed',
          error: lastError.message,
        });

        uploadQueueRef.current.delete(chunkNumber);

        if (onUploadError) {
          onUploadError(chunkNumber, lastError.message);
        }

        console.error(`[ChunkUploader] ❌ Chunk ${chunkNumber} failed after ${maxRetries} attempts`);
      }

      // Update uploading state
      setIsUploading(uploadQueueRef.current.size > 0);
    },
    [maxRetries, retryDelay, updateChunkStatus, onUploadComplete, onUploadError]
  );

  // Get chunk status
  const getChunkStatus = useCallback(
    (chunkNumber: number): ChunkStatus | undefined => {
      return chunkStatuses.find((c) => c.chunk_number === chunkNumber);
    },
    [chunkStatuses]
  );

  // Reset chunks
  const resetChunks = useCallback(() => {
    setChunkStatuses([]);
    setEstimatedSecondsRemaining(0);
    setIsUploading(false);
    uploadQueueRef.current.clear();
  }, []);

  // Calculate stats
  const totalChunks = chunkStatuses.length;
  const completedChunks = chunkStatuses.filter((c) => c.status === 'completed').length;
  const failedChunks = chunkStatuses.filter((c) => c.status === 'failed').length;
  const pendingChunks = chunkStatuses.filter(
    (c) => c.status === 'pending' || c.status === 'uploading'
  ).length;

  return {
    chunkStatuses,
    estimatedSecondsRemaining,
    isUploading,
    uploadChunk,
    getChunkStatus,
    resetChunks,
    totalChunks,
    completedChunks,
    failedChunks,
    pendingChunks,
  };
}
