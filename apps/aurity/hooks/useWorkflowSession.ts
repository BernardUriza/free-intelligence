/**
 * useWorkflowSession Hook
 *
 * Gestiona el estado completo de una sesión de workflow médico:
 * - Session ID generation
 * - Patient info
 * - Workflow state (recording, paused, processing, finalized)
 * - Checkpoint management
 * - Diarization status
 *
 * Extraído de ConversationCapture para reducir complejidad (P2 Refactoring)
 *
 * Created: 2025-01-XX
 * Author: Claude Code (P2 Architectural Refactoring)
 */

import { useState, useRef, useCallback, useEffect } from 'react';

export interface PatientInfo {
  patient_name: string;
  patient_age?: string;
  patient_id?: string;
  chief_complaint?: string;
}

export interface CheckpointState {
  isCreating: boolean;
  lastCheckpoint: {
    timestamp: string;
    chunksCount: number;
    audioSize: number;
  } | null;
  progress: number;
  // Extended state for UI feedback
  isSuccess?: boolean;
  isError?: boolean;
  chunksCount?: number;
  audioSizeMB?: number;
  errorMessage?: string;
}

export interface WorkflowSessionState {
  // Session Identity
  sessionId: string;
  setSessionId: (id: string) => void;
  sessionIdRef: React.MutableRefObject<string>;

  // Patient
  patientInfo: PatientInfo | null;
  setPatientInfo: (info: PatientInfo | null) => void;
  showPatientInfoModal: boolean;
  setShowPatientInfoModal: (show: boolean) => void;

  // Workflow State
  isPaused: boolean;
  setIsPaused: (paused: boolean) => void;
  isFinalized: boolean;
  setIsFinalized: (finalized: boolean) => void;
  isWaitingForChunks: boolean;
  setIsWaitingForChunks: (waiting: boolean) => void;
  shouldFinalize: boolean;
  setShouldFinalize: (should: boolean) => void;

  // Checkpoint
  checkpointState: CheckpointState;
  setCheckpointState: React.Dispatch<React.SetStateAction<CheckpointState>>;

  // Diarization
  diarizationJobId: string | null;
  setDiarizationJobId: (id: string | null) => void;
  showDiarizationModal: boolean;
  setShowDiarizationModal: (show: boolean) => void;

  // Audio
  pausedAudioUrl: string | null;
  setPausedAudioUrl: (url: string | null) => void;

  // Refs
  finalizationStartTimeRef: React.MutableRefObject<number>;
  estimatedSecondsRemaining: number;
  setEstimatedSecondsRemaining: (seconds: number) => void;

  // Errors
  error: string | null;
  setError: (error: string | null) => void;

  // Helpers
  generateSessionId: () => string;
  initializeSession: (patientInfoArg?: PatientInfo) => string;
  resetSession: () => void;
}

export function useWorkflowSession(
  externalSessionId?: string,
  readOnly = false,
  patient?: { id: string; name: string; age: number },
  onSessionCreated?: (sessionId: string) => void
): WorkflowSessionState {
  // Session Identity
  const [sessionId, setSessionId] = useState<string>(externalSessionId || '');
  const sessionIdRef = useRef<string>('');

  // Patient
  const [patientInfo, setPatientInfo] = useState<PatientInfo | null>(
    patient
      ? {
          patient_name: patient.name,
          patient_age: patient.age.toString(),
          patient_id: patient.id,
          chief_complaint: '',
        }
      : null
  );
  const [showPatientInfoModal, setShowPatientInfoModal] = useState(false);

  // Workflow State
  const [isPaused, setIsPaused] = useState(false);
  const [isFinalized, setIsFinalized] = useState(false);
  const [isWaitingForChunks, setIsWaitingForChunks] = useState(false);
  const [shouldFinalize, setShouldFinalize] = useState(false);

  // Checkpoint
  const [checkpointState, setCheckpointState] = useState<CheckpointState>({
    isCreating: false,
    lastCheckpoint: null,
    progress: 0,
  });

  // Diarization
  const [diarizationJobId, setDiarizationJobId] = useState<string | null>(null);
  const [showDiarizationModal, setShowDiarizationModal] = useState(false);

  // Audio
  const [pausedAudioUrl, setPausedAudioUrl] = useState<string | null>(null);

  // Refs
  const finalizationStartTimeRef = useRef<number>(0);
  const [estimatedSecondsRemaining, setEstimatedSecondsRemaining] = useState<number>(0);

  // Errors
  const [error, setError] = useState<string | null>(null);

  // Helpers
  const generateSessionId = useCallback(() => {
    const timestamp = Date.now();
    const randomSuffix = Math.random().toString(36).substring(2, 7);
    return `session_${timestamp}_${randomSuffix}`;
  }, []);

  const initializeSession = useCallback(
    (patientInfoArg?: PatientInfo) => {
      if (readOnly || externalSessionId) {
        const id = externalSessionId || sessionIdRef.current;
        setSessionId(id);
        sessionIdRef.current = id;
        return id;
      }

      const newSessionId = generateSessionId();
      setSessionId(newSessionId);
      sessionIdRef.current = newSessionId;

      if (patientInfoArg) {
        setPatientInfo(patientInfoArg);
      }

      if (onSessionCreated) {
        onSessionCreated(newSessionId);
      }

      return newSessionId;
    },
    [readOnly, externalSessionId, generateSessionId, onSessionCreated]
  );

  const resetSession = useCallback(() => {
    setIsPaused(false);
    setIsFinalized(false);
    setIsWaitingForChunks(false);
    setShouldFinalize(false);
    setCheckpointState({
      isCreating: false,
      lastCheckpoint: null,
      progress: 0,
    });
    setDiarizationJobId(null);
    setShowDiarizationModal(false);
    setPausedAudioUrl(null);
    setError(null);
    setEstimatedSecondsRemaining(0);
    finalizationStartTimeRef.current = 0;
  }, []);

  // Sync external sessionId
  useEffect(() => {
    if (externalSessionId && externalSessionId !== sessionId) {
      setSessionId(externalSessionId);
      sessionIdRef.current = externalSessionId;
    }
  }, [externalSessionId, sessionId]);

  return {
    // Session Identity
    sessionId,
    setSessionId,
    sessionIdRef,

    // Patient
    patientInfo,
    setPatientInfo,
    showPatientInfoModal,
    setShowPatientInfoModal,

    // Workflow State
    isPaused,
    setIsPaused,
    isFinalized,
    setIsFinalized,
    isWaitingForChunks,
    setIsWaitingForChunks,
    shouldFinalize,
    setShouldFinalize,

    // Checkpoint
    checkpointState,
    setCheckpointState,

    // Diarization
    diarizationJobId,
    setDiarizationJobId,
    showDiarizationModal,
    setShowDiarizationModal,

    // Audio
    pausedAudioUrl,
    setPausedAudioUrl,

    // Refs
    finalizationStartTimeRef,
    estimatedSecondsRemaining,
    setEstimatedSecondsRemaining,

    // Errors
    error,
    setError,

    // Helpers
    generateSessionId,
    initializeSession,
    resetSession,
  };
}

