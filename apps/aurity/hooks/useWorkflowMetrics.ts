/**
 * useWorkflowMetrics Hook
 *
 * Gestiona métricas y estadísticas del workflow médico:
 * - Words Per Minute (WPM)
 * - Chunk metrics (latency, status)
 * - Backend health
 * - Activity logs
 *
 * Extraído de ConversationCapture para reducir complejidad (P2 Refactoring)
 *
 * Created: 2025-01-XX
 * Author: Claude Code (P2 Architectural Refactoring)
 */

import { useState, useRef, useCallback, useEffect } from 'react';

export interface ChunkMetric {
  chunk_number: number;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  provider?: string;
  latency_ms?: number;
  retry_attempts?: number;
}

export type BackendHealthStatus = 'healthy' | 'degraded' | 'offline';

export interface WorkflowMetricsState {
  // WPM (Words Per Minute)
  wpm: number;
  setWpm: (wpm: number) => void;
  startTimeRef: React.MutableRefObject<number>;

  // Chunk Metrics
  chunkMetrics: ChunkMetric[];
  setChunkMetrics: React.Dispatch<React.SetStateAction<ChunkMetric[]>>;
  updateChunkMetric: (chunkNumber: number, updates: Partial<ChunkMetric>) => void;

  // Backend Health
  backendHealth: BackendHealthStatus;
  setBackendHealth: (status: BackendHealthStatus) => void;

  // Activity Logs
  activityLogs: Array<{ timestamp: number; message: string }>;
  addLog: (message: string) => void;
  clearLogs: () => void;

  // Helpers
  calculateWPM: (transcriptLength: number) => void;
  getAverageLatency: () => number;
  getSuccessRate: () => number;
}

export function useWorkflowMetrics(): WorkflowMetricsState {
  // WPM
  const [wpm, setWpm] = useState<number>(0);
  const startTimeRef = useRef<number>(0);

  // Chunk Metrics
  const [chunkMetrics, setChunkMetrics] = useState<ChunkMetric[]>([]);

  // Backend Health
  const [backendHealth, setBackendHealth] = useState<BackendHealthStatus>('healthy');

  // Activity Logs
  const [activityLogs, setActivityLogs] = useState<Array<{ timestamp: number; message: string }>>([]);

  // Add log entry
  const addLog = useCallback((message: string) => {
    setActivityLogs((prev) => [
      ...prev,
      {
        timestamp: Date.now(),
        message,
      },
    ]);
  }, []);

  // Clear logs
  const clearLogs = useCallback(() => {
    setActivityLogs([]);
  }, []);

  // Update chunk metric
  const updateChunkMetric = useCallback((chunkNumber: number, updates: Partial<ChunkMetric>) => {
    setChunkMetrics((prev) => {
      const existing = prev.find((m) => m.chunk_number === chunkNumber);
      if (existing) {
        return prev.map((m) =>
          m.chunk_number === chunkNumber ? { ...m, ...updates } : m
        );
      } else {
        return [...prev, { chunk_number: chunkNumber, status: 'pending', ...updates }];
      }
    });
  }, []);

  // Calculate WPM from transcript
  const calculateWPM = useCallback((transcriptLength: number) => {
    if (startTimeRef.current === 0) {
      startTimeRef.current = Date.now();
    }

    const elapsedMinutes = (Date.now() - startTimeRef.current) / 1000 / 60;
    if (elapsedMinutes > 0) {
      const wordCount = transcriptLength / 5; // Approximate word count (5 chars per word)
      const calculatedWpm = Math.round(wordCount / elapsedMinutes);
      setWpm(calculatedWpm);
    }
  }, []);

  // Get average latency across all completed chunks
  const getAverageLatency = useCallback(() => {
    const completedChunks = chunkMetrics.filter(
      (m) => m.status === 'completed' && m.latency_ms !== undefined
    );

    if (completedChunks.length === 0) return 0;

    const totalLatency = completedChunks.reduce((sum, m) => sum + (m.latency_ms || 0), 0);
    return Math.round(totalLatency / completedChunks.length);
  }, [chunkMetrics]);

  // Get success rate (completed / total)
  const getSuccessRate = useCallback(() => {
    if (chunkMetrics.length === 0) return 100;

    const completedCount = chunkMetrics.filter((m) => m.status === 'completed').length;
    return Math.round((completedCount / chunkMetrics.length) * 100);
  }, [chunkMetrics]);

  // Update backend health based on chunk metrics
  useEffect(() => {
    if (chunkMetrics.length === 0) {
      setBackendHealth('healthy');
      return;
    }

    const failedCount = chunkMetrics.filter((m) => m.status === 'failed').length;
    const totalCount = chunkMetrics.length;
    const failureRate = totalCount > 0 ? failedCount / totalCount : 0;

    if (failureRate >= 0.5) {
      setBackendHealth('offline');
    } else if (failureRate >= 0.2) {
      setBackendHealth('degraded');
    } else {
      setBackendHealth('healthy');
    }
  }, [chunkMetrics]);

  return {
    // WPM
    wpm,
    setWpm,
    startTimeRef,

    // Chunk Metrics
    chunkMetrics,
    setChunkMetrics,
    updateChunkMetric,

    // Backend Health
    backendHealth,
    setBackendHealth,

    // Activity Logs
    activityLogs,
    addLog,
    clearLogs,

    // Helpers
    calculateWPM,
    getAverageLatency,
    getSuccessRate,
  };
}

