/**
 * Diarization Polling Hook (Adaptive Polling Pattern)
 *
 * Uses Exponential Backoff with Reset-on-Change strategy:
 * - Starts with fast polling (1s) when job is active
 * - Backs off exponentially during idle periods (max 8s)
 * - Resets to fast polling when progress changes detected
 * - Pauses when browser tab is hidden (visibility-aware)
 *
 * Author: Bernard Uriza Orozco
 * Created: 2025-11-14
 * Updated: 2025-11-15 (Adaptive polling pattern)
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { POLLING_CONFIG, BACKOFF_MULTIPLIER } from '@/lib/constants/polling';
import { getBackendUrl } from '@/lib/config/deployment';

interface DiarizationStatus {
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  progress: number;
  segmentCount?: number;
  error?: string;
  hasTripleVision?: boolean; // All 3 sources present in HDF5
  statusMessage?: string; // Detailed message from polling
}

interface UseDiarizationPollingOptions {
  sessionId: string;
  jobId: string;
  enabled: boolean;
  pollInterval?: number; // Initial fast interval (default 1s)
  maxInterval?: number; // Max backoff interval (default 8s)
  maxAttempts?: number;
  onComplete?: () => void;
  onError?: (error: string) => void;
}

interface UseDiarizationPollingReturn {
  status: DiarizationStatus;
  isPolling: boolean;
  cancel: () => void;
  currentInterval: number; // Current adaptive interval (ms)
  totalPolls: number; // Total polls attempted
}

const BACKEND_URL = getBackendUrl();

export function useDiarizationPolling(
  options: UseDiarizationPollingOptions
): UseDiarizationPollingReturn {
  const {
    sessionId,
    jobId,
    enabled,
    pollInterval = POLLING_CONFIG.INITIAL_INTERVAL,
    maxInterval = POLLING_CONFIG.MAX_INTERVAL,
    maxAttempts = POLLING_CONFIG.MAX_ATTEMPTS,
    onComplete,
    onError,
  } = options;

  const [status, setStatus] = useState<DiarizationStatus>({
    status: 'pending',
    progress: 0,
    hasTripleVision: false,
    statusMessage: 'Esperando en cola...',
  });
  const [isPolling, setIsPolling] = useState(false);
  const attemptRef = useRef(0);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null); // Changed from interval to timeout
  const isCancelledRef = useRef(false);
  const currentIntervalRef = useRef(pollInterval); // Track current adaptive interval
  const lastProgressRef = useRef(0); // Track progress changes for reset-on-change

  const checkDiarizationStatus = useCallback(async (): Promise<DiarizationStatus | null> => {
    if (!sessionId || !jobId) {
      return null;
    }

    try {
      const monitorUrl = `${BACKEND_URL}/api/aurity/medical-ai/sessions/${sessionId}/monitor`;

      // AbortController with timeout to prevent hanging requests
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), POLLING_CONFIG.REQUEST_TIMEOUT);

      const response = await fetch(monitorUrl, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
        },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();

      // Use diarization.status directly (backend doesn't return transcription_sources anymore)
      const diarizationStatus = data.diarization?.status || data.status;
      const diarizationProgress = data.diarization?.progress || data.progress || 0;

      // Build detailed status message
      let statusMessage = '';
      if (diarizationStatus === 'pending') {
        statusMessage = 'Esperando en cola...';
      } else if (diarizationStatus === 'in_progress') {
        if (data.segment_count > 0) {
          statusMessage = `Analizando audio... ${data.segment_count} segmentos identificados`;
        } else {
          statusMessage = 'Iniciando análisis...';
        }
      } else if (diarizationStatus === 'completed') {
        statusMessage = `Análisis completo: ${data.segment_count || 0} segmentos clasificados`;
      } else if (diarizationStatus === 'failed') {
        statusMessage = `Error: ${data.error || 'Desconocido'}`;
      }

      return {
        status: diarizationStatus,
        progress: diarizationProgress,
        segmentCount: data.segment_count,
        hasTripleVision: diarizationStatus === 'completed', // Completed = success
        statusMessage,
      };
    } catch (error) {
      // Silently ignore AbortError (timeout) to reduce console spam
      if (error instanceof Error && error.name === 'AbortError') {
        return null;
      }
      console.warn('[Polling] Request failed:', error);
      return null;
    }
  }, [sessionId, jobId]);

  const startPolling = useCallback(() => {
    if (isCancelledRef.current) return;

    setIsPolling(true);
    attemptRef.current = 0;
    currentIntervalRef.current = pollInterval;
    lastProgressRef.current = 0;

    const poll = async () => {
      // Visibility-aware: Pause when tab hidden
      if (typeof document !== 'undefined' && document.hidden) {
        timeoutRef.current = setTimeout(poll, POLLING_CONFIG.HIDDEN_TAB_INTERVAL);
        return;
      }

      if (isCancelledRef.current) {
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
          timeoutRef.current = null;
        }
        setIsPolling(false);
        return;
      }

      attemptRef.current++;

      // Timeout check
      if (attemptRef.current > maxAttempts) {
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
          timeoutRef.current = null;
        }
        setStatus({
          status: 'failed',
          progress: 0,
          error: 'Timeout waiting for diarization',
          hasTripleVision: false,
        });
        setIsPolling(false);
        onError?.('Timeout waiting for diarization');
        return;
      }

      const result = await checkDiarizationStatus();

      if (result) {
        setStatus(result);

        // Reset-on-Change: Detect progress change
        const progressChanged = result.progress > lastProgressRef.current;
        if (progressChanged) {
          currentIntervalRef.current = pollInterval;
          lastProgressRef.current = result.progress;
        } else if (result.status === 'pending' || result.status === 'in_progress') {
          // Exponential Backoff: No change detected, increase interval
          const newInterval = Math.min(currentIntervalRef.current * BACKOFF_MULTIPLIER, maxInterval);
          currentIntervalRef.current = newInterval;
        }

        // Terminal states
        if (result.status === 'completed' && result.hasTripleVision) {
          if (timeoutRef.current) {
            clearTimeout(timeoutRef.current);
            timeoutRef.current = null;
          }
          setIsPolling(false);
          onComplete?.();
          return;
        } else if (result.status === 'failed') {
          if (timeoutRef.current) {
            clearTimeout(timeoutRef.current);
            timeoutRef.current = null;
          }
          setIsPolling(false);
          onError?.(result.error || 'Diarization failed');
          return;
        }

        // Schedule next poll with adaptive interval
        timeoutRef.current = setTimeout(poll, currentIntervalRef.current);
      } else {
        // Fallback: retry with hidden tab interval if request failed
        timeoutRef.current = setTimeout(poll, POLLING_CONFIG.HIDDEN_TAB_INTERVAL);
      }
    };

    // Start immediately
    poll();
  }, [checkDiarizationStatus, maxAttempts, pollInterval, maxInterval, onComplete, onError, sessionId, jobId]);

  const cancel = useCallback(() => {
    isCancelledRef.current = true;
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    setIsPolling(false);
  }, []);

  useEffect(() => {
    // Guard: prevent multiple polling instances
    if (!enabled || !sessionId || !jobId) {
      return;
    }

    // Guard: already polling
    if (isPolling) {
      return;
    }

    isCancelledRef.current = false;
    startPolling();

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
    };
    
  }, [enabled, sessionId, jobId]);

  return {
    status,
    isPolling,
    cancel,
    currentInterval: currentIntervalRef.current,
    totalPolls: attemptRef.current,
  };
}
