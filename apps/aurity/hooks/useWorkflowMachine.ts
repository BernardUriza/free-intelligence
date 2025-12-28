/**
 * useWorkflowMachine - React hook for medical workflow state machine
 *
 * Lightweight state machine hook without XState dependency
 * Implements the workflow logic defined in workflowMachine.ts
 *
 * Created: 2025-11-15
 * Part of: ConversationCapture decomposition refactoring
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import {
  WorkflowState,
  WorkflowEvent,
  WorkflowContext,
  initialContext,
  canTransition,
  getNextState,
  getValidTransitions,
} from '@/lib/state/workflowMachine';

export interface UseWorkflowMachineReturn {
  // Current state
  state: WorkflowState;
  context: WorkflowContext;

  // State queries
  isIdle: boolean;
  isRecording: boolean;
  isPaused: boolean;
  isProcessing: boolean;
  isCompleted: boolean;
  hasError: boolean;

  // Transitions
  send: (event: WorkflowEvent) => void;
  canSend: (eventType: WorkflowEvent['type']) => boolean;
  getValidEvents: () => WorkflowEvent['type'][];

  // Context updates
  updateContext: (updates: Partial<WorkflowContext>) => void;
  reset: () => void;

  // History (debugging)
  history: Array<{ state: WorkflowState; timestamp: Date }>;
}

export function useWorkflowMachine(): UseWorkflowMachineReturn {
  const [state, setState] = useState<WorkflowState>(WorkflowState.IDLE);
  const [context, setContext] = useState<WorkflowContext>(initialContext);
  const [history, setHistory] = useState<Array<{ state: WorkflowState; timestamp: Date }>>([
    { state: WorkflowState.IDLE, timestamp: new Date() },
  ]);

  const stateRef = useRef(state);

  // Sync state ref
  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  // Send event to state machine
  const send = useCallback((event: WorkflowEvent) => {
    const currentState = stateRef.current;

    console.log(`[WorkflowMachine] Event: ${event.type} (from state: ${currentState})`);

    // Check if transition is valid
    if (!canTransition(currentState, event.type)) {
      console.warn(
        `[WorkflowMachine] Invalid transition: ${event.type} from ${currentState}. ` +
        `Valid events: ${getValidTransitions(currentState).join(', ')}`
      );
      return;
    }

    // Get next state
    const nextState = getNextState(currentState, event.type);

    if (!nextState) {
      console.error(`[WorkflowMachine] No next state for event: ${event.type}`);
      return;
    }

    console.log(`[WorkflowMachine] Transition: ${currentState} → ${nextState}`);

    // Update state
    setState(nextState);

    // Update history
    setHistory((prev) => [
      ...prev,
      { state: nextState, timestamp: new Date() },
    ]);

    // Execute actions based on event
    switch (event.type) {
      case 'START_RECORDING':
        setContext((ctx) => ({
          ...ctx,
          startedAt: new Date(),
          sessionId: `session_${Date.now()}`,
        }));
        break;

      case 'ERROR':
        setContext((ctx) => ({
          ...ctx,
          errorMessage: 'error' in event ? event.error : 'Unknown error',
        }));
        break;

      case 'RESET':
      case 'RETRY':
        setContext(initialContext);
        setHistory([{ state: WorkflowState.IDLE, timestamp: new Date() }]);
        break;

      case 'DIARIZATION_COMPLETE':
        // Context updated externally (diarizationJobId set by component)
        break;

      case 'ENCRYPTION_COMPLETE':
        setContext((ctx) => ({
          ...ctx,
          completedAt: new Date(),
        }));
        break;

      default:
        // Other events don't modify context
        break;
    }
  }, []);

  // Check if event can be sent
  const canSend = useCallback(
    (eventType: WorkflowEvent['type']): boolean => {
      return canTransition(state, eventType);
    },
    [state]
  );

  // Get valid events for current state
  const getValidEvents = useCallback((): WorkflowEvent['type'][] => {
    return getValidTransitions(state);
  }, [state]);

  // Update context
  const updateContext = useCallback((updates: Partial<WorkflowContext>) => {
    setContext((prev) => ({ ...prev, ...updates }));
  }, []);

  // Reset machine
  const reset = useCallback(() => {
    send({ type: 'RESET' });
  }, [send]);

  // State queries
  const isIdle = state === WorkflowState.IDLE;
  const isRecording = state === WorkflowState.RECORDING;
  const isPaused = state === WorkflowState.PAUSED;
  const isProcessing =
    state === WorkflowState.UPLOADING_CHUNKS ||
    state === WorkflowState.CHECKPOINT ||
    state === WorkflowState.DIARIZING ||
    state === WorkflowState.SOAP_GENERATION ||
    state === WorkflowState.ENCRYPTING;
  const isCompleted = state === WorkflowState.COMPLETED;
  const hasError = state === WorkflowState.ERROR;

  return {
    state,
    context,
    isIdle,
    isRecording,
    isPaused,
    isProcessing,
    isCompleted,
    hasError,
    send,
    canSend,
    getValidEvents,
    updateContext,
    reset,
    history,
  };
}
