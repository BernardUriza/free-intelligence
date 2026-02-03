/**
 * useSessionDataLoader Hook
 *
 * Handles loading existing session data in read-only mode.
 * Extracts Triple Vision sources (WebSpeech, Whisper chunks, full transcription).
 */

import { useEffect, useState } from 'react';
import { medicalWorkflowApi } from '@aurity-standalone/api-client/medical-workflow';
import type { ChunkMetric } from '../types';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:7001';

// Generic chunk status for compatibility with useChunkProcessor
interface LoadedChunkStatus {
  index: number;
  status: 'completed';
  startTime: number;
  latency: number;
  transcript: string;
}

interface UseSessionDataLoaderProps {
  readOnly: boolean;
  externalSessionId?: string;
  setSessionId: (id: string) => void;
  setIsFinalized: (finalized: boolean) => void;
  setPausedAudioUrl: (url: string | null) => void;
  setIsPaused: (paused: boolean) => void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  setChunkStatuses: React.Dispatch<React.SetStateAction<any[]>>;
  addTranscriptionChunk: (text: string) => void;
  addLog: (message: string) => void;
}

interface SessionDataLoaderResult {
  webSpeechTranscripts: string[];
  setWebSpeechTranscripts: React.Dispatch<React.SetStateAction<string[]>>;
  loadedChunkMetrics: ChunkMetric[];
  setLoadedChunkMetrics: React.Dispatch<React.SetStateAction<ChunkMetric[]>>;
}

export function useSessionDataLoader({
  readOnly,
  externalSessionId,
  setSessionId,
  setIsFinalized,
  setPausedAudioUrl,
  setIsPaused,
  setChunkStatuses,
  addTranscriptionChunk,
  addLog,
}: UseSessionDataLoaderProps): SessionDataLoaderResult {
  const [webSpeechTranscripts, setWebSpeechTranscripts] = useState<string[]>([]);
  const [loadedChunkMetrics, setLoadedChunkMetrics] = useState<ChunkMetric[]>([]);

  useEffect(() => {
    if (!readOnly || !externalSessionId) return;

    console.log('[SessionDataLoader] Read-only mode - loading session:', externalSessionId);
    setSessionId(externalSessionId);
    setIsFinalized(true);

    const loadExistingData = async () => {
      try {
        addLog('Cargando sesión existente...');

        // Load all 3 transcription sources (Triple Vision)
        const sources = await medicalWorkflowApi.getTranscriptionSources(externalSessionId);

        console.log('[SessionDataLoader] Loaded transcription sources:', {
          webspeech_count: sources.webspeech_final.length,
          chunks_count: sources.transcription_per_chunks.length,
          full_length: sources.full_transcription.length,
        });

        // 1. Populate WebSpeech transcripts
        if (sources.webspeech_final.length > 0) {
          setWebSpeechTranscripts(sources.webspeech_final);
          console.log('[SessionDataLoader] [OK] WebSpeech loaded:', sources.webspeech_final.length);
        }

        // 2. Populate chunk transcripts (Whisper/Deepgram)
        if (sources.transcription_per_chunks.length > 0) {
          const loadedStatuses: LoadedChunkStatus[] = sources.transcription_per_chunks.map((chunk) => ({
            index: chunk.chunk_number,
            status: 'completed' as const,
            startTime: Date.now(),
            latency: 0,
            transcript: chunk.transcript,
          }));
          setChunkStatuses(loadedStatuses);

          const chunkMetrics: ChunkMetric[] = sources.transcription_per_chunks.map((chunk) => ({
            chunk_number: chunk.chunk_number,
            text: chunk.transcript,
            provider: chunk.provider,
            polling_attempts: chunk.polling_attempts,
            resolution_time_seconds: chunk.resolution_time_seconds,
            retry_attempts: chunk.retry_attempts,
            confidence: chunk.confidence,
            duration: chunk.duration,
          }));
          setLoadedChunkMetrics(chunkMetrics);

          sources.transcription_per_chunks.forEach((chunk) => {
            if (chunk.transcript) {
              addTranscriptionChunk(chunk.transcript);
            }
          });

          console.log('[SessionDataLoader] [OK] Chunks loaded:', sources.transcription_per_chunks.length);
        }

        // Load audio file
        const audioUrl = `${BACKEND_URL}/api/aurity/medical-ai/sessions/${externalSessionId}/audio`;
        setPausedAudioUrl(audioUrl);
        setIsPaused(true);

        const totalDuration = sources.transcription_per_chunks.reduce(
          (sum, chunk) => sum + chunk.duration,
          0
        );

        addLog(
          `Sesión cargada: ${sources.transcription_per_chunks.length} chunks, ${totalDuration.toFixed(1)}s` +
          (sources.webspeech_final.length > 0 ? `, ${sources.webspeech_final.length} webspeech` : '')
        );
      } catch (err) {
        console.error('[SessionDataLoader] Failed to load session:', err);
        addLog(`Error cargando sesión: ${err}`);
      }
    };

    loadExistingData();
  }, [
    readOnly,
    externalSessionId,
    setSessionId,
    setIsFinalized,
    setPausedAudioUrl,
    setIsPaused,
    setChunkStatuses,
    addTranscriptionChunk,
    addLog,
  ]);

  return {
    webSpeechTranscripts,
    setWebSpeechTranscripts,
    loadedChunkMetrics,
    setLoadedChunkMetrics,
  };
}
