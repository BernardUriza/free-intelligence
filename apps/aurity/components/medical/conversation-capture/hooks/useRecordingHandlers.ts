/**
 * useRecordingHandlers Hook
 *
 * Consolidates all recording control handlers:
 * - Start, Pause, Resume, End session
 * - Finalization flow with diarization
 */

import { useCallback, useEffect } from 'react';
import { medicalWorkflowApi } from '@aurity-standalone/api-client/medical-workflow';
import { concatenateAudioBlobs, revokeAudioUrl } from '@/lib/audio/concatenation';
import type { PatientInfo } from '../../../medical/PatientInfoModal';
import type { TranscriptionData } from '@aurity-standalone/hooks/useTranscription';
import type { WorkflowSessionState } from '@/hooks/useWorkflowSession';
import type { ChunkMetric } from '../types';

interface RecordingHandlersDeps {
  // Session state - use the actual hook return type
  session: WorkflowSessionState;

  // Audio upload refs
  audioUpload: {
    chunkNumberRef: React.MutableRefObject<number>;
    fullAudioBlobsRef: React.MutableRefObject<Blob[]>;
  };

  // Orchestrator
  orchestrator: {
    startRecording: (patientInfo: PatientInfo) => Promise<void>;
    pauseRecording: () => Promise<void>;
    resumeRecording: () => Promise<void>;
    startDiarization: () => Promise<string | null>;
    finalizeWorkflow: () => void;
  };

  // Checkpoint manager
  checkpoint: {
    createCheckpoint: (sessionId: string, lastChunk: number) => Promise<{
      chunks_concatenated: number;
      full_audio_size: number;
    } | null>;
  };

  // Metrics
  metrics: {
    addLog: (message: string) => void;
  };

  // Recording hook functions
  hookStartRecording: () => Promise<void>;
  hookStopRecording: () => Promise<Blob | null>;

  // Transcription
  resetTranscription: () => void;
  getTranscriptionText: () => string;
  resetChunkProcessorMetrics: () => void;

  // WebSpeech
  isWebSpeechSupported: boolean;
  isWebSpeechActive: boolean;
  startWebSpeech: () => void;
  stopWebSpeech: () => void;

  // External state sync
  setExternalIsRecording?: (recording: boolean) => void;
  setWpm: (wpm: number) => void;
  setWebSpeechTranscripts: React.Dispatch<React.SetStateAction<string[]>>;
  setLoadedChunkMetrics: React.Dispatch<React.SetStateAction<ChunkMetric[]>>;
  webSpeechTranscripts: string[];

  // Callbacks
  onTranscriptionComplete?: (data: TranscriptionData) => void;
}

interface RecordingHandlersResult {
  handleStartRecording: () => Promise<void>;
  handlePatientInfoSubmit: (info: PatientInfo) => void;
  handlePauseRecording: () => Promise<void>;
  handleResumeRecording: () => Promise<void>;
  handleEndSession: () => void;
  performFinalization: () => Promise<void>;
}

export function useRecordingHandlers(deps: RecordingHandlersDeps): RecordingHandlersResult {
  const {
    session,
    audioUpload,
    orchestrator,
    checkpoint,
    metrics,
    hookStartRecording,
    hookStopRecording,
    resetTranscription,
    getTranscriptionText,
    resetChunkProcessorMetrics,
    isWebSpeechSupported,
    isWebSpeechActive,
    startWebSpeech,
    stopWebSpeech,
    setExternalIsRecording,
    setWpm,
    setWebSpeechTranscripts,
    setLoadedChunkMetrics,
    webSpeechTranscripts,
    onTranscriptionComplete,
  } = deps;

  // Start recording
  const handleStartRecording = useCallback(async () => {
    if (!session.patientInfo) {
      console.log('[Recording] Patient info required - showing modal');
      session.setShowPatientInfoModal(true);
      return;
    }

    try {
      await orchestrator.startRecording(session.patientInfo);

      resetTranscription();
      setWebSpeechTranscripts([]);
      setLoadedChunkMetrics([]);

      resetChunkProcessorMetrics();
      setWpm(0);

      await hookStartRecording();

      if (isWebSpeechSupported) {
        startWebSpeech();
        console.log('[WebSpeech] Started instant preview');
      }
    } catch (err) {
      console.error('Error starting recording:', err);
      session.setError('No se pudo acceder al micrófono. Por favor, verifica los permisos.');
    }
  }, [
    session,
    orchestrator,
    resetTranscription,
    setWebSpeechTranscripts,
    setLoadedChunkMetrics,
    resetChunkProcessorMetrics,
    setWpm,
    hookStartRecording,
    isWebSpeechSupported,
    startWebSpeech,
  ]);

  // Handle patient info submission
  const handlePatientInfoSubmit = useCallback((info: PatientInfo) => {
    console.log('[PatientInfo] Received patient info:', info);
    session.setPatientInfo(info);
    session.setShowPatientInfoModal(false);

    setTimeout(() => {
      handleStartRecording();
    }, 100);
  }, [handleStartRecording, session]);

  // Pause recording
  const handlePauseRecording = useCallback(async () => {
    try {
      const capturedBlob = await hookStopRecording();
      if (capturedBlob) {
        audioUpload.fullAudioBlobsRef.current.push(capturedBlob);
        console.log(`[Pause] Stored segment ${audioUpload.fullAudioBlobsRef.current.length}: ${(capturedBlob.size / 1024).toFixed(1)}KB`);
      }

      await orchestrator.pauseRecording();

      if (isWebSpeechActive) {
        stopWebSpeech();
      }

      if (audioUpload.fullAudioBlobsRef.current.length > 0) {
        const mimeType = audioUpload.fullAudioBlobsRef.current[0].type || 'audio/webm';
        const concatenatedBlob = new Blob(audioUpload.fullAudioBlobsRef.current, { type: mimeType });
        const audioUrl = URL.createObjectURL(concatenatedBlob);
        session.setPausedAudioUrl(audioUrl);
      }

      if (session.sessionIdRef.current && audioUpload.chunkNumberRef.current > 0) {
        checkpoint.createCheckpoint(
          session.sessionIdRef.current,
          audioUpload.chunkNumberRef.current - 1
        ).then((response) => {
          if (response) {
            session.setCheckpointState(prev => ({
              ...prev,
              isCreating: false,
              isSuccess: true,
              isError: false,
              chunksCount: response.chunks_concatenated,
              audioSizeMB: response.full_audio_size / 1024 / 1024,
            }));

            setTimeout(() => {
              session.setCheckpointState(prev => ({
                ...prev,
                isCreating: false,
                isSuccess: false,
                isError: false,
              }));
            }, 3000);
          }
        }).catch((err) => {
          console.error('[Pause] Checkpoint error:', err);
          session.setCheckpointState(prev => ({
            ...prev,
            isCreating: false,
            isSuccess: false,
            isError: true,
          }));
        });
      }
    } catch (err) {
      console.error('[Recorder] Pause error:', err);
    }
  }, [hookStopRecording, audioUpload, session, checkpoint, orchestrator, isWebSpeechActive, stopWebSpeech]);

  // Resume recording
  const handleResumeRecording = useCallback(async () => {
    try {
      if (session.pausedAudioUrl) {
        URL.revokeObjectURL(session.pausedAudioUrl);
        session.setPausedAudioUrl(null);
      }

      await orchestrator.resumeRecording();
      await hookStartRecording();

      if (isWebSpeechSupported) {
        startWebSpeech();
      }

      if (setExternalIsRecording) {
        setExternalIsRecording(true);
      }
    } catch (err) {
      console.error('[Recorder] Resume error:', err);
    }
  }, [session, orchestrator, hookStartRecording, isWebSpeechSupported, startWebSpeech, setExternalIsRecording]);

  // Perform finalization
  const performFinalization = useCallback(async () => {
    try {
      console.log('[Session End] [START] Finalization process');

      session.setShowDiarizationModal(false);

      revokeAudioUrl(session.pausedAudioUrl);
      session.setPausedAudioUrl(null);

      const concatenated = concatenateAudioBlobs(audioUpload.fullAudioBlobsRef.current);
      const finalAudioBlob = concatenated?.blob ?? null;

      const finalText = getTranscriptionText();

      if (finalAudioBlob && session.sessionIdRef.current) {
        console.log(
          `[Session End] Preparing full audio blob: ${(finalAudioBlob.size / 1024 / 1024).toFixed(2)} MB`
        );

        try {
          const result = await medicalWorkflowApi.endSession(
            session.sessionIdRef.current,
            finalAudioBlob,
            webSpeechTranscripts
          );
          console.log('[Session End] [OK] Full audio + webspeech saved:', result);
          console.log('[Session End] [INFO] WebSpeech transcripts sent:', webSpeechTranscripts.length);

          try {
            const diarizationJobId = await orchestrator.startDiarization();

            if (diarizationJobId) {
              console.log('[DIARIZATION] [START] Diarization job:', diarizationJobId);
              session.setIsWaitingForChunks(false);
              session.setShowDiarizationModal(true);
              metrics.addLog(`Iniciando diarización (Job: ${diarizationJobId.slice(0, 8)}...)`);
            }
          } catch (diarizationErr) {
            console.error('[Session End] [ERROR] Diarization error:', diarizationErr);
            metrics.addLog(`Error de diarización: ${diarizationErr}`);
            session.setShowDiarizationModal(false);
          }
        } catch (err) {
          console.warn('[Session End] [WARN] Upload skipped (streaming mode):', err);
        }
      }

      audioUpload.fullAudioBlobsRef.current = [];

      if (onTranscriptionComplete && finalText) {
        onTranscriptionComplete({ text: finalText });
      }

      session.setIsPaused(false);
      audioUpload.chunkNumberRef.current = 0;
    } catch (err) {
      console.error('[Session] End error:', err);
    }
  }, [
    session,
    audioUpload,
    metrics,
    orchestrator,
    getTranscriptionText,
    onTranscriptionComplete,
    webSpeechTranscripts,
  ]);

  // End session handler
  const handleEndSession = useCallback(() => {
    session.setShowDiarizationModal(true);
    session.setIsWaitingForChunks(true);
    session.setShouldFinalize(true);
    session.finalizationStartTimeRef.current = Date.now();

    metrics.addLog('Finalizando sesión - esperando chunks pendientes...');
  }, [session, metrics]);

  // Effect: Trigger finalization when chunks are ready
  useEffect(() => {
    if (session.shouldFinalize && !session.isWaitingForChunks) {
      performFinalization();
      session.setShouldFinalize(false);
    }
  }, [session.shouldFinalize, session.isWaitingForChunks, performFinalization, session]);

  return {
    handleStartRecording,
    handlePatientInfoSubmit,
    handlePauseRecording,
    handleResumeRecording,
    handleEndSession,
    performFinalization,
  };
}
