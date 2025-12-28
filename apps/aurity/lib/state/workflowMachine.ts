/**
 * Medical Recording Workflow State Machine
 *
 * Uses XState v5 to model the entire medical recording workflow
 * Prevents invalid states, ensures proper transitions
 *
 * Created: 2025-11-15
 * Part of: ConversationCapture decomposition refactoring
 *
 * Note: This is a preparatory implementation. XState v5 needs to be installed:
 * npm install xstate@latest
 *
 * For now, this file exports a TypeScript-only state machine definition
 * that can be used as a reference for refactoring ConversationCapture.
 */

// Workflow States
export enum WorkflowState {
  IDLE = 'idle',
  RECORDING = 'recording',
  PAUSED = 'paused',
  UPLOADING_CHUNKS = 'uploadingChunks',
  CHECKPOINT = 'checkpoint',
  DIARIZING = 'diarizing',
  SOAP_GENERATION = 'soapGeneration',
  ENCRYPTING = 'encrypting',
  COMPLETED = 'completed',
  ERROR = 'error',
}

// Workflow Events
export type WorkflowEvent =
  | { type: 'START_RECORDING' }
  | { type: 'PAUSE' }
  | { type: 'RESUME' }
  | { type: 'STOP' }
  | { type: 'UPLOAD_COMPLETE' }
  | { type: 'CHECKPOINT_COMPLETE' }
  | { type: 'DIARIZATION_COMPLETE' }
  | { type: 'SOAP_COMPLETE' }
  | { type: 'ENCRYPTION_COMPLETE' }
  | { type: 'ERROR'; error: string }
  | { type: 'RETRY' }
  | { type: 'RESET' };

// Workflow Context (shared data across states)
export interface WorkflowContext {
  sessionId: string | null;
  chunkCount: number;
  completedChunks: number;
  errorMessage: string | null;
  diarizationJobId: string | null;
  soapJobId: string | null;
  startedAt: Date | null;
  completedAt: Date | null;
}

// Initial context
export const initialContext: WorkflowContext = {
  sessionId: null,
  chunkCount: 0,
  completedChunks: 0,
  errorMessage: null,
  diarizationJobId: null,
  soapJobId: null,
  startedAt: null,
  completedAt: null,
};

// State machine definition (TypeScript-only, no XState dependency yet)
export interface StateMachineConfig {
  id: string;
  initial: WorkflowState;
  context: WorkflowContext;
  states: Record<
    WorkflowState,
    {
      on?: Record<string, { target: WorkflowState; actions?: string[] }>;
      type?: 'final';
    }
  >;
}

export const workflowMachineConfig: StateMachineConfig = {
  id: 'medicalRecording',
  initial: WorkflowState.IDLE,
  context: initialContext,
  states: {
    [WorkflowState.IDLE]: {
      on: {
        START_RECORDING: {
          target: WorkflowState.RECORDING,
          actions: ['initializeSession'],
        },
      },
    },
    [WorkflowState.RECORDING]: {
      on: {
        PAUSE: {
          target: WorkflowState.PAUSED,
          actions: ['pauseRecording'],
        },
        STOP: {
          target: WorkflowState.UPLOADING_CHUNKS,
          actions: ['stopRecording'],
        },
        ERROR: {
          target: WorkflowState.ERROR,
          actions: ['setError'],
        },
      },
    },
    [WorkflowState.PAUSED]: {
      on: {
        RESUME: {
          target: WorkflowState.RECORDING,
          actions: ['resumeRecording'],
        },
        STOP: {
          target: WorkflowState.CHECKPOINT,
          actions: ['stopRecording', 'createCheckpoint'],
        },
      },
    },
    [WorkflowState.UPLOADING_CHUNKS]: {
      on: {
        UPLOAD_COMPLETE: {
          target: WorkflowState.DIARIZING,
          actions: ['startDiarization'],
        },
        ERROR: {
          target: WorkflowState.ERROR,
          actions: ['setError'],
        },
      },
    },
    [WorkflowState.CHECKPOINT]: {
      on: {
        CHECKPOINT_COMPLETE: {
          target: WorkflowState.DIARIZING,
          actions: ['startDiarization'],
        },
        ERROR: {
          target: WorkflowState.ERROR,
          actions: ['setError'],
        },
      },
    },
    [WorkflowState.DIARIZING]: {
      on: {
        DIARIZATION_COMPLETE: {
          target: WorkflowState.SOAP_GENERATION,
          actions: ['startSOAPGeneration'],
        },
        ERROR: {
          target: WorkflowState.ERROR,
          actions: ['setError'],
        },
      },
    },
    [WorkflowState.SOAP_GENERATION]: {
      on: {
        SOAP_COMPLETE: {
          target: WorkflowState.ENCRYPTING,
          actions: ['startEncryption'],
        },
        ERROR: {
          target: WorkflowState.ERROR,
          actions: ['setError'],
        },
      },
    },
    [WorkflowState.ENCRYPTING]: {
      on: {
        ENCRYPTION_COMPLETE: {
          target: WorkflowState.COMPLETED,
          actions: ['markCompleted'],
        },
        ERROR: {
          target: WorkflowState.ERROR,
          actions: ['setError'],
        },
      },
    },
    [WorkflowState.COMPLETED]: {
      type: 'final',
      on: {
        RESET: {
          target: WorkflowState.IDLE,
          actions: ['resetContext'],
        },
      },
    },
    [WorkflowState.ERROR]: {
      on: {
        RETRY: {
          target: WorkflowState.IDLE,
          actions: ['clearError', 'resetContext'],
        },
        RESET: {
          target: WorkflowState.IDLE,
          actions: ['clearError', 'resetContext'],
        },
      },
    },
  },
};

// Helper: Get valid transitions for a state
export function getValidTransitions(state: WorkflowState): WorkflowEvent['type'][] {
  const stateConfig = workflowMachineConfig.states[state];
  return stateConfig.on ? (Object.keys(stateConfig.on) as WorkflowEvent['type'][]) : [];
}

// Helper: Check if transition is valid
export function canTransition(
  currentState: WorkflowState,
  event: WorkflowEvent['type']
): boolean {
  return getValidTransitions(currentState).includes(event);
}

// Helper: Get next state for an event
export function getNextState(
  currentState: WorkflowState,
  event: WorkflowEvent['type']
): WorkflowState | null {
  const stateConfig = workflowMachineConfig.states[currentState];
  const transition = stateConfig.on?.[event];
  return transition?.target || null;
}

// TODO: When XState v5 is installed, uncomment this:
/*
import { createMachine, interpret } from 'xstate';

export const workflowMachine = createMachine({
  id: 'medicalRecording',
  initial: WorkflowState.IDLE,
  context: initialContext,
  states: {
    // ... convert workflowMachineConfig to XState format
  },
});

export const workflowService = interpret(workflowMachine);
*/
