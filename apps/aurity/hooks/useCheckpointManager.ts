/**
 * useCheckpointManager Hook
 *
 * Gestiona checkpoints en pause/resume:
 * - Crear checkpoint (concatenar audio)
 * - Tracking de estado (isCreating, progress)
 * - Generar URL de preview
 * - Error handling
 *
 * Extraído de ConversationCapture para reducir complejidad (P2 Refactoring)
 *
 * Created: 2025-01-XX
 * Author: Claude Code (P2 Architectural Refactoring)
 */

import { useState, useCallback } from 'react';
import { medicalWorkflowApi, type CheckpointResponse } from '@aurity-standalone/api-client/medical-workflow';
import { getBackendUrl } from '@/lib/config/deployment';

export interface CheckpointInfo {
  timestamp: string;
  chunksCount: number;
  audioSize: number;
  audioUrl?: string;
}

export interface CheckpointManagerState {
  // State
  isCreating: boolean;
  progress: number;
  lastCheckpoint: CheckpointInfo | null;
  error: string | null;

  // Actions
  createCheckpoint: (sessionId: string, lastChunkIdx?: number) => Promise<CheckpointResponse | null>;
  getPreviewUrl: (sessionId: string) => string;
  reset: () => void;
}

export function useCheckpointManager(): CheckpointManagerState {
  const [isCreating, setIsCreating] = useState(false);
  const [progress, setProgress] = useState(0);
  const [lastCheckpoint, setLastCheckpoint] = useState<CheckpointInfo | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Get preview URL
  const getPreviewUrl = useCallback((sessionId: string): string => {
    const backendUrl = getBackendUrl();
    return `${backendUrl}/api/aurity/medical-ai/sessions/${sessionId}/audio`;
  }, []);

  // Create checkpoint
  const createCheckpoint = useCallback(
    async (sessionId: string, lastChunkIdx?: number): Promise<CheckpointResponse | null> => {
      setIsCreating(true);
      setProgress(0);
      setError(null);

      try {
        console.log(`[Checkpoint] Creating checkpoint for session ${sessionId}...`);

        // Simulate progress
        const progressInterval = setInterval(() => {
          setProgress((prev) => Math.min(prev + 10, 90));
        }, 200);

        const response = await medicalWorkflowApi.createCheckpoint(sessionId, lastChunkIdx);

        clearInterval(progressInterval);
        setProgress(100);

        const checkpointInfo: CheckpointInfo = {
          timestamp: response.checkpoint_at,
          chunksCount: response.chunks_concatenated,
          audioSize: response.full_audio_size,
          audioUrl: getPreviewUrl(sessionId),
        };

        setLastCheckpoint(checkpointInfo);
        setIsCreating(false);

        console.log(`[Checkpoint] Created successfully:`, checkpointInfo);

        return response;
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Error al crear checkpoint';
        setError(errorMessage);
        setIsCreating(false);
        setProgress(0);

        console.error('[Checkpoint] Creation failed:', err);

        return null;
      }
    },
    [getPreviewUrl]
  );

  // Reset state
  const reset = useCallback(() => {
    setIsCreating(false);
    setProgress(0);
    setLastCheckpoint(null);
    setError(null);
  }, []);

  return {
    // State
    isCreating,
    progress,
    lastCheckpoint,
    error,

    // Actions
    createCheckpoint,
    getPreviewUrl,
    reset,
  };
}

