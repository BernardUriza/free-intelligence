/**
 * useWorkflowOrchestrator Hook
 *
 * Orquesta el flujo completo del workflow médico:
 * - Coordinación de start/pause/resume/stop
 * - Trigger de diarization y SOAP generation
 * - Manejo de transiciones de estado
 * - Integración de todos los hooks especializados
 *
 * Extraído de ConversationCapture para reducir complejidad (P2 Refactoring)
 *
 * Created: 2025-01-XX
 * Author: Claude Code (P2 Architectural Refactoring)
 */

import { useCallback } from 'react';
import { medicalWorkflowApi } from '@aurity-standalone/api-client/medical-workflow';
import { getBackendUrl } from '@/lib/config/deployment';
import type { WorkflowSessionState } from './useWorkflowSession';
import type { AudioUploadState } from './useAudioUpload';
import type { WorkflowMetricsState } from './useWorkflowMetrics';

export interface WorkflowOrchestratorOptions {
  session: WorkflowSessionState;
  audioUpload: AudioUploadState;
  metrics: WorkflowMetricsState;
  onRecordingStart?: () => void;
  onRecordingStop?: () => void;
  onPause?: () => void;
  onResume?: () => void;
  onDiarizationStart?: (jobId: string) => void;
  onSOAPStart?: (jobId: string) => void;
  onWorkflowComplete?: () => void;
  onSessionCreated?: (sessionId: string) => void;
}

export interface WorkflowOrchestratorState {
  // Recording Control
  startRecording: (patientInfo?: any) => Promise<void>;
  stopRecording: () => Promise<void>;
  pauseRecording: () => Promise<void>;
  resumeRecording: () => Promise<void>;

  // Workflow Phases
  startDiarization: () => Promise<string | null>;
  startSOAPGeneration: () => Promise<void>;
  finalizeWorkflow: () => Promise<void>;

  // Checkpoint
  createCheckpoint: () => Promise<void>;

  // State Queries
  canStartRecording: () => boolean;
  canPauseRecording: () => boolean;
  canResumeRecording: () => boolean;
  canStopRecording: () => boolean;
  canStartDiarization: () => boolean;
}

export function useWorkflowOrchestrator(
  options: WorkflowOrchestratorOptions
): WorkflowOrchestratorState {
  const { session, audioUpload, metrics, onRecordingStart, onRecordingStop, onPause, onResume, onDiarizationStart, onSOAPStart, onWorkflowComplete, onSessionCreated } = options;

  // Start recording
  const startRecording = useCallback(
    async (patientInfo?: any) => {
      if (session.isFinalized) {
        session.setError('La sesión ya ha sido finalizada. No se puede grabar.');
        metrics.addLog('Sesión completada - recarga la página para nueva consulta');
        return;
      }

      // Initialize session
      const sessionId = session.initializeSession(patientInfo);
      metrics.addLog(`Grabación iniciada - Sesión: ${sessionId}`);

      // Reset counters
      audioUpload.resetChunkCounter();
      audioUpload.clearInflight();

      // Notify parent component (for DialogueFlow to load later)
      if (onSessionCreated) {
        onSessionCreated(sessionId);
      }

      if (onRecordingStart) {
        onRecordingStart();
      }
    },
    [session, audioUpload, metrics, onRecordingStart, onSessionCreated]
  );

  // Stop recording
  const stopRecording = useCallback(async () => {
    metrics.addLog('Deteniendo grabación...');

    // Wait for inflight chunks
    const maxWait = 30; // 30 seconds max
    let waitTime = 0;
    while (audioUpload.getInflightCount() > 0 && waitTime < maxWait) {
      await new Promise((resolve) => setTimeout(resolve, 500));
      waitTime += 0.5;
    }

    if (audioUpload.getInflightCount() > 0) {
      metrics.addLog(`Advertencia: ${audioUpload.getInflightCount()} chunks aún en proceso`);
    }

    metrics.addLog('Grabación detenida');

    if (onRecordingStop) {
      onRecordingStop();
    }
  }, [audioUpload, metrics, onRecordingStop]);

  // Pause recording
  const pauseRecording = useCallback(async () => {
    session.setIsPaused(true);
    metrics.addLog('Grabación pausada');

    if (onPause) {
      onPause();
    }
  }, [session, metrics, onPause]);

  // Resume recording
  const resumeRecording = useCallback(async () => {
    session.setIsPaused(false);
    session.setPausedAudioUrl(null);
    metrics.addLog('Grabación reanudada');

    if (onResume) {
      onResume();
    }
  }, [session, metrics, onResume]);

  // Create checkpoint (concatenate audio on pause)
  const createCheckpoint = useCallback(async () => {
    if (!session.sessionId) {
      session.setError('No hay sesión activa para crear checkpoint');
      return;
    }

    session.setCheckpointState({
      isCreating: true,
      lastCheckpoint: null,
      progress: 0,
    });

    metrics.addLog('Creando checkpoint...');

    try {
      const response = await medicalWorkflowApi.createCheckpoint(
        session.sessionId,
        audioUpload.chunkNumberRef.current - 1
      );

      session.setCheckpointState({
        isCreating: false,
        lastCheckpoint: {
          timestamp: response.checkpoint_at,
          chunksCount: response.chunks_concatenated,
          audioSize: response.full_audio_size,
        },
        progress: 100,
      });

      metrics.addLog(
        `Checkpoint creado: ${response.chunks_concatenated} chunks, ${(response.full_audio_size / 1024 / 1024).toFixed(2)} MB`
      );

      // Generate preview URL
      const audioUrl = `${getBackendUrl()}/api/aurity/medical-ai/sessions/${session.sessionId}/audio`;
      session.setPausedAudioUrl(audioUrl);
    } catch (error) {
      console.error('Checkpoint creation failed:', error);
      session.setCheckpointState({
        isCreating: false,
        lastCheckpoint: null,
        progress: 0,
      });
      session.setError(error instanceof Error ? error.message : 'Error al crear checkpoint');
      metrics.addLog('Error al crear checkpoint');
    }
  }, [session, audioUpload, metrics]);

  // Start diarization (speaker separation)
  const startDiarization = useCallback(async (): Promise<string | null> => {
    if (!session.sessionId) {
      session.setError('No hay sesión para diarizar');
      return null;
    }

    metrics.addLog('Iniciando diarización (separación de hablantes)...');

    try {
      const response = await medicalWorkflowApi.startDiarization(session.sessionId);

      session.setDiarizationJobId(response.job_id);
      session.setShowDiarizationModal(true);

      metrics.addLog(`Diarización iniciada - Job: ${response.job_id}`);

      if (onDiarizationStart) {
        onDiarizationStart(response.job_id);
      }

      return response.job_id;
    } catch (error) {
      console.error('Diarization start failed:', error);
      session.setError(error instanceof Error ? error.message : 'Error al iniciar diarización');
      metrics.addLog('Error al iniciar diarización');
      return null;
    }
  }, [session, metrics, onDiarizationStart]);

  // Start SOAP generation
  const startSOAPGeneration = useCallback(async () => {
    if (!session.sessionId) {
      session.setError('No hay sesión para generar SOAP');
      return;
    }

    metrics.addLog('Iniciando generación de nota SOAP...');

    try {
      const response = await medicalWorkflowApi.startSOAPGeneration(session.sessionId);

      metrics.addLog(`SOAP generation iniciado - Job: ${response.job_id}`);

      if (onSOAPStart) {
        onSOAPStart(response.job_id);
      }
    } catch (error) {
      console.error('SOAP generation start failed:', error);
      session.setError(error instanceof Error ? error.message : 'Error al generar SOAP');
      metrics.addLog('Error al generar SOAP');
    }
  }, [session, metrics, onSOAPStart]);

  // Finalize workflow
  const finalizeWorkflow = useCallback(async () => {
    session.setIsFinalized(true);
    metrics.addLog('Workflow finalizado');

    if (onWorkflowComplete) {
      onWorkflowComplete();
    }
  }, [session, metrics, onWorkflowComplete]);

  // State queries
  const canStartRecording = useCallback(() => {
    return !session.isFinalized;
  }, [session.isFinalized]);

  const canPauseRecording = useCallback(() => {
    return !session.isPaused && !session.isFinalized;
  }, [session.isPaused, session.isFinalized]);

  const canResumeRecording = useCallback(() => {
    return session.isPaused && !session.isFinalized;
  }, [session.isPaused, session.isFinalized]);

  const canStopRecording = useCallback(() => {
    return !session.isFinalized;
  }, [session.isFinalized]);

  const canStartDiarization = useCallback(() => {
    return !!session.sessionId && !session.diarizationJobId && !session.isFinalized;
  }, [session.sessionId, session.diarizationJobId, session.isFinalized]);

  return {
    // Recording Control
    startRecording,
    stopRecording,
    pauseRecording,
    resumeRecording,

    // Workflow Phases
    startDiarization,
    startSOAPGeneration,
    finalizeWorkflow,

    // Checkpoint
    createCheckpoint,

    // State Queries
    canStartRecording,
    canPauseRecording,
    canResumeRecording,
    canStopRecording,
    canStartDiarization,
  };
}

