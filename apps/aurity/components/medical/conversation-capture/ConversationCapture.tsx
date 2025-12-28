'use client';

/**
 * ConversationCapture Component - AURITY Medical Workflow
 *
 * Production-ready audio recording and transcription component.
 * Refactored 2025-12 to use modular hooks for maintainability.
 *
 * File: components/medical/conversation-capture/ConversationCapture.tsx
 */

import { useState, useRef, useEffect } from 'react';
import { AlertCircle } from 'lucide-react';
import { useClipboard } from '@/hooks/useClipboard';
import { useAudioAnalysis } from '@/hooks/useAudioAnalysis';
import { useChunkProcessor } from '@/hooks/useChunkProcessor';
import { useRecorder } from '@aurity-standalone/hooks/useRecorder';
import { useTranscription } from '@aurity-standalone/hooks/useTranscription';
import { useWebSpeech } from '@/hooks/useWebSpeech';
import { useDiarizationPolling } from '@/hooks/useDiarizationPolling';
import { AUDIO_CONFIG } from '@/lib/audio/constants';
import { POLLING_CONFIG } from '@/lib/constants/polling';
import { useWorkflowSession } from '@/hooks/useWorkflowSession';
import { useWorkflowMetrics } from '@/hooks/useWorkflowMetrics';
import { useAudioUpload } from '@/hooks/useAudioUpload';
import { useWorkflowOrchestrator } from '@/hooks/useWorkflowOrchestrator';
import { useCheckpointManager } from '@/hooks/useCheckpointManager';
import { useH5DebugTools } from '@/hooks/useH5DebugTools';

// Local hooks
import { useSessionDataLoader, useChunkHandler, useRecordingHandlers } from './hooks';
import type { ConversationCaptureProps, WorkflowStatus } from './types';

// UI Components
import { DemoButton } from '../DemoButton';
import { DemoConsultationModal } from '../DemoConsultationModal';
import { SessionBadges } from '../SessionBadges';
import { RecordingControls } from '../RecordingControls';
import { AudioLevelVisualizer } from '../AudioLevelVisualizer';
import { AdvancedMetrics } from '../AdvancedMetrics';
import { WorkflowProgress } from '../WorkflowProgress';
import { PatientInfoModal } from '../PatientInfoModal';
import { PausedAudioPreview } from '../PausedAudioPreview';
import { FinalTranscription } from '../FinalTranscription';
import { TranscriptionSources } from '../TranscriptionSources';
import { DiarizationProcessingModal } from '../DiarizationProcessingModal';
import { CheckpointProgress } from '../CheckpointProgress';
import { WebSpeechStatusBadge } from '../WebSpeechStatusBadge';
import { H5DebugModal } from '../../dev/H5DebugModal';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:7001';

export function ConversationCapture({
  onNext,
  onTranscriptionComplete,
  isRecording: externalIsRecording,
  setIsRecording: setExternalIsRecording,
  onSessionCreated,
  sessionId: externalSessionId,
  readOnly = false,
  patient,
  className = ''
}: ConversationCaptureProps) {
  // ========== Core Hooks ==========
  const session = useWorkflowSession(externalSessionId, readOnly, patient, onSessionCreated);
  const metrics = useWorkflowMetrics();
  const audioUpload = useAudioUpload();
  const checkpoint = useCheckpointManager();

  const orchestrator = useWorkflowOrchestrator({
    session,
    audioUpload,
    metrics,
    onRecordingStart: () => setExternalIsRecording?.(true),
    onRecordingStop: () => setExternalIsRecording?.(false),
    onSessionCreated: (sid) => onSessionCreated?.(sid),
    onDiarizationStart: (jobId) => console.log('[Orchestrator] Diarization started:', jobId),
    onSOAPStart: (jobId) => console.log('[Orchestrator] SOAP started:', jobId),
    onWorkflowComplete: () => { console.log('[Orchestrator] Complete'); onNext?.(); },
  });

  // ========== UI State ==========
  const [isProcessing] = useState(false);
  const [jobId] = useState<string | null>(null);
  const [workflowStatus] = useState<WorkflowStatus | null>(null);
  const [isDemoModalOpen, setIsDemoModalOpen] = useState(false);
  const [wpm, setWpm] = useState(0);

  // ========== Refs ==========
  const audioLevelRef = useRef(0);
  const isSilentRef = useRef(true);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const _startTimeRef = useRef(0);

  // ========== Custom Hooks ==========
  const { copiedId, copyToClipboard } = useClipboard();

  const {
    chunkStatuses,
    setChunkStatuses,
    avgLatency: chunkProcessorAvgLatency,
    backendHealth,
    activityLogs: chunkProcessorActivityLogs,
    pollJobStatus,
    resetMetrics: resetChunkProcessorMetrics,
  } = useChunkProcessor({ backendUrl: BACKEND_URL });

  const {
    transcriptionData,
    addChunk: addTranscriptionChunk,
    reset: resetTranscription,
    getText: getTranscriptionText,
    getWordCount,
  } = useTranscription();

  const {
    isListening: isWebSpeechActive,
    interimTranscript: webSpeechInterim,
    isSupported: isWebSpeechSupported,
    startWebSpeech,
    stopWebSpeech,
  } = useWebSpeech({
    onTranscript: (text, isFinal) => {
      if (isFinal) {
        sessionDataLoader.setWebSpeechTranscripts((prev) => [...prev, text]);
      }
    },
    language: 'es-MX',
    continuous: true,
    interimResults: true,
  });

  // Session data loader (read-only mode)
  const sessionDataLoader = useSessionDataLoader({
    readOnly,
    externalSessionId,
    setSessionId: session.setSessionId,
    setIsFinalized: session.setIsFinalized,
    setPausedAudioUrl: session.setPausedAudioUrl,
    setIsPaused: session.setIsPaused,
    setChunkStatuses,
    addTranscriptionChunk,
    addLog: metrics.addLog,
  });

  // Chunk handler
  const { handleChunk } = useChunkHandler({
    sessionIdRef: session.sessionIdRef,
    chunkNumberRef: audioUpload.chunkNumberRef,
    audioLevelRef,
    isSilentRef,
    patientInfo: session.patientInfo,
    setChunkStatuses,
    addLog: metrics.addLog,
    pollJobStatus,
    addTranscriptionChunk,
  });

  // Recording hook
  const {
    isRecording: hookIsRecording,
    recordingTime: hookRecordingTime,
    fullAudioUrl: hookFullAudioUrl,
    currentStream,
    startRecording: hookStartRecording,
    stopRecording: hookStopRecording,
  } = useRecorder({
    onChunk: handleChunk,
    onError: (err) => session.setError(err),
    timeSlice: AUDIO_CONFIG.TIME_SLICE,
    sampleRate: AUDIO_CONFIG.SAMPLE_RATE,
    channels: AUDIO_CONFIG.CHANNELS,
  });

  const isRecording = externalIsRecording ?? hookIsRecording;
  const recordingTime = hookRecordingTime;
  const fullAudioUrl = hookFullAudioUrl;

  // Audio analysis
  const { audioLevel, isSilent } = useAudioAnalysis(currentStream, { isActive: isRecording });

  // Recording handlers
  const recordingHandlers = useRecordingHandlers({
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
    setWebSpeechTranscripts: sessionDataLoader.setWebSpeechTranscripts,
    setLoadedChunkMetrics: sessionDataLoader.setLoadedChunkMetrics,
    webSpeechTranscripts: sessionDataLoader.webSpeechTranscripts,
    onTranscriptionComplete,
  });

  // Diarization polling
  const {
    status: diarizationStatus,
    isPolling,
    currentInterval,
    totalPolls,
  } = useDiarizationPolling({
    sessionId: session.diarizationJobId || '',
    jobId: session.diarizationJobId || '',
    enabled: session.showDiarizationModal && !!session.diarizationJobId,
    pollInterval: POLLING_CONFIG.INITIAL_INTERVAL,
    maxInterval: POLLING_CONFIG.MAX_INTERVAL,
    onComplete: async () => {
      console.log('[Diarization] ✅ Completed');
      metrics.addLog('✅ Diarización completada');
      session.setIsFinalized(true);

      setTimeout(async () => {
        session.setShowDiarizationModal(false);
        session.setDiarizationJobId(null);

        const currentSessionId = session.sessionIdRef.current;
        if (currentSessionId) {
          try {
            metrics.addLog('📋 Generando notas SOAP...');
            await orchestrator.startSOAPGeneration();
            metrics.addLog('✅ Generación SOAP iniciada');
          } catch (error) {
            console.error('[SOAP] ❌ Failed:', error);
            metrics.addLog('⚠️ Error al generar SOAP');
          }
        }

        metrics.addLog('✅ Sesión completada');
        orchestrator.finalizeWorkflow();
      }, 2000);
    },
    onError: (error) => {
      console.error('[Diarization] ❌ Error:', error);
      session.setShowDiarizationModal(false);
      session.setDiarizationJobId(null);
      session.sessionIdRef.current = '';
      session.setSessionId('');
      metrics.addLog(`❌ Error en diarización: ${error}`);
    },
  });

  // H5 Debug Tools
  const h5Debug = useH5DebugTools(session.sessionIdRef.current);

  // ========== Effects ==========

  // Sync audio values to refs
  useEffect(() => {
    audioLevelRef.current = audioLevel;
    isSilentRef.current = isSilent;
  }, [audioLevel, isSilent]);

  // Initialize patient info from parent
  useEffect(() => {
    if (patient && !session.patientInfo) {
      session.setPatientInfo({
        patient_name: patient.name,
        patient_age: patient.age.toString(),
        patient_id: patient.id,
        chief_complaint: '',
      });
    }
  }, [patient, session]);

  // WPM calculation
  useEffect(() => {
    if (isRecording && recordingTime > 0) {
      const words = getWordCount();
      const minutes = recordingTime / 60;
      setWpm(minutes > 0 ? Math.round(words / minutes) : 0);
    }
  }, [isRecording, recordingTime, getWordCount]);

  // Chunk completion monitoring
  useEffect(() => {
    if (!session.shouldFinalize || !session.isWaitingForChunks) return;

    const pendingChunks = chunkStatuses.filter(
      (c) => c.status !== 'completed' && c.status !== 'failed'
    );
    const completedCount = chunkStatuses.filter((c) => c.status === 'completed').length;

    if (pendingChunks.length > 0) {
      metrics.addLog(`⏳ Transcripción: ${completedCount}/${audioUpload.chunkNumberRef.current} chunks`);
    }

    const elapsed = Date.now() - session.finalizationStartTimeRef.current;
    if (elapsed > 30000 && pendingChunks.length > 0) {
      metrics.addLog(`⚠️ Timeout: ${pendingChunks.length} chunks pendientes`);
      session.setIsWaitingForChunks(false);
      session.setShouldFinalize(false);
      return;
    }

    if (pendingChunks.length === 0 && audioUpload.chunkNumberRef.current > 0) {
      session.setIsWaitingForChunks(false);
    }
  }, [chunkStatuses, session, audioUpload.chunkNumberRef, metrics]);

  // Cleanup
  useEffect(() => {
    const intervalId = pollingIntervalRef.current;
    return () => { if (intervalId) clearInterval(intervalId); };
  }, []);

  // ========== Render ==========
  return (
    <div className={`space-y-6 ${className} relative`}>
      <DemoButton
        isDemoPlaying={false}
        isDemoPaused={false}
        isProcessing={isProcessing}
        onToggle={() => setIsDemoModalOpen(true)}
      />

      <DemoConsultationModal
        isOpen={isDemoModalOpen}
        onClose={() => setIsDemoModalOpen(false)}
        onSendChunk={handleChunk}
        isProcessing={isProcessing}
      />

      <SessionBadges
        sessionId={session.sessionIdRef.current}
        jobId={jobId}
        copiedId={copiedId}
        onCopy={copyToClipboard}
      />

      <div className="text-center">
        <h2 className="text-2xl font-bold text-white mb-2">Captura de Conversación</h2>
        <p className="text-slate-400">
          {readOnly ? 'Sesión existente - Solo lectura' : 'Graba la consulta médica para transcripción y análisis'}
        </p>
      </div>

      {readOnly && (
        <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4 flex items-center gap-3">
          <AlertCircle className="h-5 w-5 fi-text-primary flex-shrink-0" />
          <div>
            <p className="text-sm font-medium text-blue-300">Sesión Existente</p>
            <p className="text-xs fi-text-primary/80">
              Esta sesión ya fue grabada. Mostrando audio y transcripción existentes.
            </p>
          </div>
        </div>
      )}

      <RecordingControls
        isRecording={isRecording}
        isPaused={session.isPaused}
        isProcessing={isProcessing}
        isFinalized={session.isFinalized}
        recordingTime={recordingTime}
        onStart={recordingHandlers.handleStartRecording}
        onPause={recordingHandlers.handlePauseRecording}
        onResume={recordingHandlers.handleResumeRecording}
      />

      {(isRecording || session.isPaused) && (
        <div className="space-y-2">
          <AudioLevelVisualizer
            audioLevel={audioLevel}
            recordingTime={recordingTime}
            wordCount={getWordCount()}
            chunkCount={audioUpload.chunkNumberRef.current}
          />
          <WebSpeechStatusBadge
            isSupported={isWebSpeechSupported}
            isActive={isWebSpeechActive}
            interimText={webSpeechInterim}
          />
        </div>
      )}

      <CheckpointProgress
        isCreating={session.checkpointState.isCreating}
        isSuccess={session.checkpointState.isSuccess ?? false}
        isError={session.checkpointState.isError ?? false}
        chunksCount={session.checkpointState.chunksCount}
        audioSizeMB={session.checkpointState.audioSizeMB}
        errorMessage={session.checkpointState.errorMessage}
      />

      {chunkStatuses.length > 0 && (
        <AdvancedMetrics
          chunkStatuses={chunkStatuses}
          avgLatency={chunkProcessorAvgLatency}
          wpm={wpm}
          backendHealth={backendHealth}
          activityLogs={chunkProcessorActivityLogs}
        />
      )}

      {workflowStatus && <WorkflowProgress workflowStatus={workflowStatus} />}

      {(isRecording || session.isPaused || session.isFinalized || audioUpload.chunkNumberRef.current > 0) && (
        <TranscriptionSources
          webSpeechTranscripts={sessionDataLoader.webSpeechTranscripts}
          whisperChunks={
            sessionDataLoader.loadedChunkMetrics.length > 0
              ? sessionDataLoader.loadedChunkMetrics
              : chunkStatuses
                  .filter((c) => c.status === 'completed' && c.transcript)
                  .map((c) => ({
                    chunk_number: c.index,
                    text: c.transcript || '',
                    provider: c.provider,
                    resolution_time_seconds: c.resolution_time_seconds,
                    retry_attempts: c.retry_attempts,
                    polling_attempts: c.polling_attempts,
                    confidence: c.confidence,
                    duration: c.duration,
                  }))
          }
          fullTranscription={transcriptionData?.text || ''}
          sessionId={session.sessionIdRef.current}
          isFinalized={session.isFinalized}
          className="mt-4"
        />
      )}

      {session.isPaused && (
        <PausedAudioPreview
          audioUrl={session.pausedAudioUrl}
          segmentCount={audioUpload.fullAudioBlobsRef.current.length}
          chunkCount={audioUpload.chunkNumberRef.current}
          onEndSession={recordingHandlers.handleEndSession}
          onResume={recordingHandlers.handleResumeRecording}
        />
      )}

      {!isRecording && !session.isPaused && audioUpload.chunkNumberRef.current > 0 && (
        <FinalTranscription
          transcriptionData={transcriptionData}
          fullAudioUrl={fullAudioUrl}
          chunkCount={audioUpload.chunkNumberRef.current}
          onContinue={onNext ? () => onNext() : undefined}
        />
      )}

      {session.error && (
        <div className="fi-card-danger">
          <div className="flex items-center gap-2 fi-text-error">
            <AlertCircle className="h-5 w-5" />
            <p className="font-medium">{session.error}</p>
          </div>
        </div>
      )}

      {h5Debug.isEnabled && (
        <H5DebugModal
          h5Data={h5Debug.h5Data}
          isOpen={h5Debug.isOpen}
          onClose={h5Debug.close}
        />
      )}

      <DiarizationProcessingModal
        isOpen={session.showDiarizationModal}
        status={session.isWaitingForChunks ? 'waiting_for_chunks' : diarizationStatus.status}
        progress={diarizationStatus.progress}
        segmentCount={diarizationStatus.segmentCount}
        error={diarizationStatus.error}
        statusMessage={diarizationStatus.statusMessage}
        completedChunks={chunkStatuses.filter((c) => c.status === 'completed').length}
        totalChunks={audioUpload.chunkNumberRef.current}
        estimatedSecondsRemaining={session.estimatedSecondsRemaining}
        currentInterval={currentInterval}
        totalPolls={totalPolls}
        isPolling={isPolling}
        onCancel={() => {
          session.setShowDiarizationModal(false);
          session.setIsWaitingForChunks(false);
          session.setShouldFinalize(false);
        }}
      />

      <PatientInfoModal
        isOpen={session.showPatientInfoModal}
        onClose={() => session.setShowPatientInfoModal(false)}
        onSubmit={recordingHandlers.handlePatientInfoSubmit}
      />
    </div>
  );
}
