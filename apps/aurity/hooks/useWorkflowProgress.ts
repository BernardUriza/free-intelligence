/**
 * useWorkflowProgress - Medical workflow phase tracking hook
 *
 * Extracts workflow state management from ConversationCapture
 * Tracks: Phase 1-5 (Upload, Checkpoint, Diarization, SOAP, Finalize)
 *
 * Created: 2025-11-15
 * Part of: ConversationCapture decomposition refactoring
 */

import { useState, useCallback } from 'react';

export enum WorkflowPhase {
  IDLE = 'idle',
  UPLOADING = 'uploading',
  CHECKPOINT = 'checkpoint',
  DIARIZING = 'diarizing',
  SOAP_GENERATION = 'soap_generation',
  FINALIZING = 'finalizing',
  COMPLETED = 'completed',
  ERROR = 'error',
}

export interface WorkflowPhaseInfo {
  phase: WorkflowPhase;
  label: string;
  description: string;
  progress: number; // 0-100
}

export interface UseWorkflowProgressReturn {
  // Current state
  currentPhase: WorkflowPhase;
  phaseInfo: WorkflowPhaseInfo;
  overallProgress: number; // 0-100 (across all phases)

  // Actions
  setPhase: (phase: WorkflowPhase, progress?: number) => void;
  setProgress: (progress: number) => void;
  nextPhase: () => void;
  reset: () => void;

  // Helpers
  isActive: (phase: WorkflowPhase) => boolean;
  isCompleted: (phase: WorkflowPhase) => boolean;
}

const PHASE_METADATA: Record<WorkflowPhase, { label: string; description: string; weight: number }> = {
  [WorkflowPhase.IDLE]: {
    label: 'Esperando',
    description: 'Listo para iniciar grabación',
    weight: 0,
  },
  [WorkflowPhase.UPLOADING]: {
    label: 'Subiendo chunks',
    description: 'Transcribiendo audio en tiempo real',
    weight: 40, // 40% of workflow
  },
  [WorkflowPhase.CHECKPOINT]: {
    label: 'Checkpoint',
    description: 'Concatenando audio',
    weight: 10, // 10% of workflow
  },
  [WorkflowPhase.DIARIZING]: {
    label: 'Diarización',
    description: 'Separando voces (médico/paciente)',
    weight: 30, // 30% of workflow
  },
  [WorkflowPhase.SOAP_GENERATION]: {
    label: 'Generando SOAP',
    description: 'Extrayendo nota clínica',
    weight: 15, // 15% of workflow
  },
  [WorkflowPhase.FINALIZING]: {
    label: 'Finalizando',
    description: 'Encriptando y almacenando',
    weight: 5, // 5% of workflow
  },
  [WorkflowPhase.COMPLETED]: {
    label: 'Completado',
    description: 'Workflow finalizado exitosamente',
    weight: 0,
  },
  [WorkflowPhase.ERROR]: {
    label: 'Error',
    description: 'Ocurrió un error en el workflow',
    weight: 0,
  },
};

const PHASE_ORDER: WorkflowPhase[] = [
  WorkflowPhase.IDLE,
  WorkflowPhase.UPLOADING,
  WorkflowPhase.CHECKPOINT,
  WorkflowPhase.DIARIZING,
  WorkflowPhase.SOAP_GENERATION,
  WorkflowPhase.FINALIZING,
  WorkflowPhase.COMPLETED,
];

export function useWorkflowProgress(): UseWorkflowProgressReturn {
  const [currentPhase, setCurrentPhase] = useState<WorkflowPhase>(WorkflowPhase.IDLE);
  const [phaseProgress, setPhaseProgress] = useState(0); // Progress within current phase (0-100)

  // Set phase with optional progress
  const setPhase = useCallback((phase: WorkflowPhase, progress: number = 0) => {
    setCurrentPhase(phase);
    setPhaseProgress(Math.max(0, Math.min(100, progress)));
  }, []);

  // Update progress within current phase
  const setProgress = useCallback((progress: number) => {
    setPhaseProgress(Math.max(0, Math.min(100, progress)));
  }, []);

  // Move to next phase
  const nextPhase = useCallback(() => {
    const currentIndex = PHASE_ORDER.indexOf(currentPhase);
    if (currentIndex >= 0 && currentIndex < PHASE_ORDER.length - 1) {
      const next = PHASE_ORDER[currentIndex + 1];
      setPhase(next, 0);
    }
  }, [currentPhase, setPhase]);

  // Reset to idle
  const reset = useCallback(() => {
    setPhase(WorkflowPhase.IDLE, 0);
  }, [setPhase]);

  // Check if phase is active
  const isActive = useCallback(
    (phase: WorkflowPhase) => currentPhase === phase,
    [currentPhase]
  );

  // Check if phase is completed
  const isCompleted = useCallback(
    (phase: WorkflowPhase) => {
      const currentIndex = PHASE_ORDER.indexOf(currentPhase);
      const targetIndex = PHASE_ORDER.indexOf(phase);
      return currentIndex > targetIndex;
    },
    [currentPhase]
  );

  // Calculate overall progress (0-100) across all phases
  const calculateOverallProgress = useCallback(() => {
    let totalWeight = 0;
    let completedWeight = 0;

    const currentIndex = PHASE_ORDER.indexOf(currentPhase);

    PHASE_ORDER.forEach((phase, index) => {
      const metadata = PHASE_METADATA[phase];
      totalWeight += metadata.weight;

      if (index < currentIndex) {
        // Completed phases
        completedWeight += metadata.weight;
      } else if (index === currentIndex) {
        // Current phase (partial progress)
        completedWeight += (metadata.weight * phaseProgress) / 100;
      }
    });

    return totalWeight > 0 ? Math.round((completedWeight / totalWeight) * 100) : 0;
  }, [currentPhase, phaseProgress]);

  // Get current phase info
  const phaseInfo: WorkflowPhaseInfo = {
    phase: currentPhase,
    label: PHASE_METADATA[currentPhase].label,
    description: PHASE_METADATA[currentPhase].description,
    progress: phaseProgress,
  };

  const overallProgress = calculateOverallProgress();

  return {
    currentPhase,
    phaseInfo,
    overallProgress,
    setPhase,
    setProgress,
    nextPhase,
    reset,
    isActive,
    isCompleted,
  };
}
