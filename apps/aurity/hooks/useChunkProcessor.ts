/**
 * useChunkProcessor Hook
 *
 * Maneja el procesamiento de chunks de audio con backend integration:
 * - Job polling con timeout y retry logic
 * - Status tracking por chunk (pending → processing → completed/failed)
 * - Métricas en tiempo real (latencia promedio, backend health)
 * - Activity logs
 *
 * Extraído de ConversationCapture durante refactoring incremental.
 *
 * @example
 * const { chunkStatuses, pollJobStatus, avgLatency, backendHealth, addLog } =
 *   useChunkProcessor({
 *     backendUrl: 'http://localhost:7001'
 *   });
 *
 * // Upload chunk and poll for result
 * const transcript = await pollJobStatus(jobId, chunkNumber);
 */

import { useState, useCallback } from 'react';

interface ChunkStatus {
  index: number;
  status: 'uploading' | 'pending' | 'processing' | 'completed' | 'failed' | 'unresolved';
  startTime?: number;
  endTime?: number;
  latency?: number;
  transcript?: string | null;
  error?: string;
  // NEW: Backend metrics for adaptive load balancing
  provider?: string; // deepgram (primary), azure_whisper (deprecated)
  resolution_time_seconds?: number; // Backend resolution time
  retry_attempts?: number; // Fallback attempts
  polling_attempts?: number; // Frontend polling attempts
  confidence?: number; // Transcription confidence
  duration?: number; // Audio duration
}

// Backend chunk response type
interface BackendChunk {
  chunk_number: number;
  transcript?: string;
  status?: string;
  provider?: string;
  resolution_time_seconds?: number;
  retry_attempts?: number;
  confidence?: number;
  duration?: number;
  error_message?: string;
}

interface UseChunkProcessorConfig {
  backendUrl?: string;
  maxAttempts?: number;
  pollInterval?: number;
}

interface UseChunkProcessorReturn {
  chunkStatuses: ChunkStatus[];
  setChunkStatuses: React.Dispatch<React.SetStateAction<ChunkStatus[]>>;
  avgLatency: number;
  backendHealth: 'healthy' | 'degraded' | 'down';
  activityLogs: string[];
  pollJobStatus: (jobId: string, chunkNumber: number) => Promise<string | null>;
  addLog: (message: string) => void;
  resetMetrics: () => void;
}

export function useChunkProcessor(
  config: UseChunkProcessorConfig = {}
): UseChunkProcessorReturn {
  const {
    backendUrl = 'http://localhost:7001',
    maxAttempts = 60, // 60 attempts * 1000ms = 60s timeout (OpenAI Whisper takes ~5s/chunk)
    pollInterval = 1000, // 1000ms (1s) between polls - reduced load on HDF5 SWMR
  } = config;

  // State
  const [chunkStatuses, setChunkStatuses] = useState<ChunkStatus[]>([]);
  const [avgLatency, setAvgLatency] = useState<number>(0);
  const [backendHealth, setBackendHealth] = useState<'healthy' | 'degraded' | 'down'>('healthy');
  const [activityLogs, setActivityLogs] = useState<string[]>([]);

  // Add log entry (keep last 10)
  const addLog = useCallback((message: string) => {
    const timestamp = new Date().toLocaleTimeString();
    setActivityLogs((prev) => [`[${timestamp}] ${message}`, ...prev].slice(0, 10));
  }, []);

  // Poll job status with retry logic
  const pollJobStatus = useCallback(
    async (jobId: string, chunkNumber: number): Promise<string | null> => {
      const startTime = Date.now();

      // Update chunk status to pending
      setChunkStatuses((prev) => {
        const existing = prev.find((c) => c.index === chunkNumber);
        if (existing) {
          return prev.map((c) =>
            c.index === chunkNumber ? { ...c, status: 'pending' as const } : c
          );
        }
        return [...prev, { index: chunkNumber, status: 'pending' as const, startTime }];
      });

      for (let attempt = 0; attempt < maxAttempts; attempt++) {
        try {
          // Use PUBLIC workflow endpoint (AUR-PROMPT-4.2 compliance)
          // P1 FIX: Use API client instead of hardcoded fetch
          const { api } = await import('@/lib/api/client');
          const jobStatus = await api.get<{
            status: string;
            progress?: number;
            transcript?: string;
            error?: string;
            chunks?: BackendChunk[];
          }>(`/api/aurity/jobs/${jobId}`);

          if (jobStatus.error) {
            console.error(`[CHUNK ${chunkNumber}] Poll failed: ${jobStatus.error}`);
            setBackendHealth('degraded');
            return null;
          }

          // Backend returns: {session_id, status, total_chunks, processed_chunks, chunks: [...]}
          // Find the specific chunk we're polling for
          const targetChunk = jobStatus.chunks?.find((c) => c.chunk_number === chunkNumber);

          if (!targetChunk) {
            // Chunk not yet in job metadata
            if (attempt % 5 === 0 || attempt >= maxAttempts - 2) {
              console.log(
                `[CHUNK ${chunkNumber}] [WAIT] Chunk not found in job yet (attempt ${attempt + 1}/${maxAttempts})`
              );
            }
            await new Promise((resolve) => setTimeout(resolve, pollInterval));
            continue;
          }

          // Update chunk status based on backend response
          if (targetChunk.status === 'processing' || jobStatus.status === 'in_progress') {
            setChunkStatuses((prev) =>
              prev.map((c) =>
                c.index === chunkNumber ? { ...c, status: 'processing' as const } : c
              )
            );
          }

          // Check if THIS chunk is completed
          if (targetChunk.status === 'completed') {
            const endTime = Date.now();
            const latency = endTime - startTime;

            console.log(
              `[CHUNK ${chunkNumber}] [OK] Poll completed (${latency}ms)`,
              targetChunk
            );
            addLog(`Chunk ${chunkNumber} transcrito en ${(latency / 1000).toFixed(1)}s`);

            // Extract transcript from chunk
            const transcript = targetChunk.transcript;

            // Calculate frontend polling attempts (how many loops we did)
            const pollingAttempts = attempt + 1;

            // Update chunk status to completed with backend metrics
            setChunkStatuses((prev) =>
              prev.map((c) =>
                c.index === chunkNumber
                  ? {
                      ...c,
                      status: 'completed' as const,
                      endTime,
                      latency,
                      transcript: transcript || '',
                      // NEW: Include backend metrics for display
                      provider: targetChunk.provider,
                      resolution_time_seconds: targetChunk.resolution_time_seconds,
                      retry_attempts: targetChunk.retry_attempts,
                      polling_attempts: pollingAttempts,
                      confidence: targetChunk.confidence,
                      duration: targetChunk.duration,
                    }
                  : c
              )
            );

            // Update average latency
            setChunkStatuses((current) => {
              const completed = current.filter((c) => c.status === 'completed' && c.latency);
              if (completed.length > 0) {
                const avg =
                  completed.reduce((sum, c) => sum + (c.latency || 0), 0) / completed.length;
                setAvgLatency(avg);
              }
              return current;
            });

            setBackendHealth('healthy');

            if (transcript) {
              return transcript;
            } else {
              console.warn(
                `[CHUNK ${chunkNumber}] Chunk completed but no transcript.`,
                targetChunk
              );
              return null;
            }
          } else if (targetChunk.status === 'failed') {
            console.error(
              `[CHUNK ${chunkNumber}] Chunk failed: ${targetChunk.error_message || 'Unknown error'}`
            );
            addLog(`[ERROR] Chunk ${chunkNumber} falló: ${targetChunk.error_message || 'Unknown'}`);

            setChunkStatuses((prev) =>
              prev.map((c) =>
                c.index === chunkNumber
                  ? {
                      ...c,
                      status: 'failed' as const,
                      endTime: Date.now(),
                      error: targetChunk.error_message,
                    }
                  : c
              )
            );
            setBackendHealth('degraded');
            return null;
          } else if (targetChunk.status === 'pending' || targetChunk.status === 'processing') {
            // Still processing, wait and continue polling
            if (attempt % 5 === 0 || attempt >= maxAttempts - 2) {
              // Log every 5 attempts OR when close to timeout
              console.log(
                `[CHUNK ${chunkNumber}] [WAIT] Polling... (${targetChunk.status}, attempt ${attempt + 1}/${maxAttempts})`
              );
            }
            await new Promise((resolve) => setTimeout(resolve, pollInterval));
            continue;
          } else {
            console.warn(
              `[CHUNK ${chunkNumber}] Unknown chunk status: ${targetChunk.status}`,
              targetChunk
            );
            return null;
          }
        } catch {
          // Silently handle poll errors - backend may be slow or unavailable
          setBackendHealth('down');
          return null;
        }
      }

      // Timeout after maxAttempts - chunk will be marked as unresolved
      console.warn(
        `[CHUNK ${chunkNumber}] [WARN] Timeout after ${maxAttempts} attempts (${(maxAttempts * pollInterval) / 1000}s). Backend may be overloaded or STT service unavailable.`
      );
      addLog(`[WARN] Chunk ${chunkNumber} timeout después de ${maxAttempts} intentos - transcripción incompleta`);

      setChunkStatuses((prev) =>
        prev.map((c) =>
          c.index === chunkNumber
            ? { ...c, status: 'unresolved' as const, transcript: null, error: 'Timeout - backend no respondió' }
            : c
        )
      );
      setBackendHealth('degraded');
      return null;
    },
    [backendUrl, maxAttempts, pollInterval, addLog]
  );

  // Reset metrics
  const resetMetrics = useCallback(() => {
    setChunkStatuses([]);
    setAvgLatency(0);
    setBackendHealth('healthy');
    setActivityLogs([]);
  }, []);

  return {
    chunkStatuses,
    setChunkStatuses,
    avgLatency,
    backendHealth,
    activityLogs,
    pollJobStatus,
    addLog,
    resetMetrics,
  };
}
