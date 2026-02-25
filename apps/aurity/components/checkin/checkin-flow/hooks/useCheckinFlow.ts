/**
 * useCheckinFlow Hook
 *
 * Manages the entire check-in flow state and handlers.
 */

import { useState, useEffect, useCallback } from 'react';
import { createLogger } from '@/lib/internal/logger';
import {
  checkinAPI,
  isValidCurp,
} from '@aurity-standalone/api-client/checkin';

const log = createLogger('CheckinFlow');
import type { IdentifyPatientResponse, CompleteCheckinResponse } from '@aurity-standalone/types/checkin';
import type { FlowState, IdentificationMethod, IdentificationFormState } from '../types';

interface UseCheckinFlowProps {
  clinicId: string;
  onComplete?: (response: CompleteCheckinResponse) => void;
}

export function useCheckinFlow({ clinicId, onComplete }: UseCheckinFlowProps) {
  const [state, setState] = useState<FlowState>({
    step: 'identify',
    session: null,
    identificationMethod: 'code',
    patientData: null,
    pendingActions: [],
    completedActions: [],
    skippedActions: [],
    error: null,
    isLoading: false,
  });

  const [formState, setFormState] = useState<IdentificationFormState>({
    checkinCode: '',
    curp: '',
    firstName: '',
    lastName: '',
    dateOfBirth: '',
  });

  // Start session on mount
  useEffect(() => {
    async function initSession() {
      try {
        const session = await checkinAPI.startSession(clinicId, 'mobile');
        setState(prev => ({ ...prev, session }));
      } catch (error) {
        log.error('Failed to start session', { error: String(error) });
      }
    }
    initSession();
  }, [clinicId]);

  const setIdentificationMethod = useCallback((method: IdentificationMethod) => {
    setState(prev => ({ ...prev, identificationMethod: method, error: null }));
  }, []);

  const updateFormField = useCallback((field: keyof IdentificationFormState, value: string) => {
    setFormState(prev => ({ ...prev, [field]: value }));
  }, []);

  const clearError = useCallback(() => {
    setState(prev => ({ ...prev, error: null }));
  }, []);

  const handleIdentify = useCallback(async () => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      let response: IdentifyPatientResponse;

      switch (state.identificationMethod) {
        case 'code':
          if (formState.checkinCode.replace('-', '').length !== 6) {
            throw new Error('El código debe tener 6 dígitos');
          }
          response = await checkinAPI.identifyByCode({
            clinic_id: clinicId,
            checkin_code: formState.checkinCode.replace('-', ''),
          });
          break;

        case 'curp':
          if (!isValidCurp(formState.curp)) {
            throw new Error('CURP inválido');
          }
          response = await checkinAPI.identifyByCurp({
            clinic_id: clinicId,
            curp: formState.curp.toUpperCase(),
          });
          break;

        case 'name_dob':
          if (!formState.firstName.trim() || !formState.lastName.trim() || !formState.dateOfBirth) {
            throw new Error('Completa todos los campos');
          }
          response = await checkinAPI.identifyByName({
            clinic_id: clinicId,
            first_name: formState.firstName.trim(),
            last_name: formState.lastName.trim(),
            date_of_birth: formState.dateOfBirth,
          });
          break;

        default:
          throw new Error('Método de identificación no válido');
      }

      if (!response.success || !response.patient) {
        throw new Error(response.error || 'No se encontró tu cita');
      }

      setState(prev => ({
        ...prev,
        step: 'confirm_identity',
        patientData: response,
        pendingActions: response.pending_actions || [],
        isLoading: false,
      }));
    } catch (error) {
      setState(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Error de identificación',
        isLoading: false,
      }));
    }
  }, [clinicId, state.identificationMethod, formState]);

  const handleConfirmIdentity = useCallback((confirmed: boolean) => {
    if (confirmed) {
      const blockingActions = state.pendingActions.filter(a => a.is_blocking && a.status === 'pending');

      if (blockingActions.length > 0 || state.pendingActions.length > 0) {
        setState(prev => ({ ...prev, step: 'pending_actions' }));
      } else {
        handleCompleteCheckin();
      }
    } else {
      setState(prev => ({
        ...prev,
        step: 'identify',
        patientData: null,
        error: null,
      }));
      setFormState({
        checkinCode: '',
        curp: '',
        firstName: '',
        lastName: '',
        dateOfBirth: '',
      });
    }
  }, [state.pendingActions]);

  const handleCompleteAction = useCallback(async (actionId: string) => {
    setState(prev => ({ ...prev, isLoading: true }));

    try {
      await checkinAPI.completeAction(actionId);
      setState(prev => ({
        ...prev,
        completedActions: [...prev.completedActions, actionId],
        pendingActions: prev.pendingActions.map(a =>
          a.action_id === actionId ? { ...a, status: 'completed' as const } : a
        ),
        isLoading: false,
      }));
    } catch {
      setState(prev => ({
        ...prev,
        error: 'Error completando acción',
        isLoading: false,
      }));
    }
  }, []);

  const handleSkipAction = useCallback(async (actionId: string) => {
    setState(prev => ({ ...prev, isLoading: true }));

    try {
      await checkinAPI.skipAction(actionId);
      setState(prev => ({
        ...prev,
        skippedActions: [...prev.skippedActions, actionId],
        pendingActions: prev.pendingActions.map(a =>
          a.action_id === actionId ? { ...a, status: 'skipped' as const } : a
        ),
        isLoading: false,
      }));
    } catch {
      setState(prev => ({
        ...prev,
        error: 'Error omitiendo acción',
        isLoading: false,
      }));
    }
  }, []);

  const handleCompleteCheckin = useCallback(async () => {
    if (!state.patientData?.appointment?.appointment_id || !state.session?.session_id) {
      setState(prev => ({ ...prev, step: 'success' }));
      return;
    }

    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const response = await checkinAPI.completeCheckin({
        session_id: state.session!.session_id,
        appointment_id: state.patientData!.appointment!.appointment_id,
        completed_actions: state.completedActions,
        skipped_actions: state.skippedActions,
      });

      if (response.success) {
        setState(prev => ({ ...prev, step: 'success', isLoading: false }));
        onComplete?.(response);
      } else {
        throw new Error(response.error || 'Error completando check-in');
      }
    } catch (error) {
      setState(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Error de check-in',
        isLoading: false,
      }));
    }
  }, [state.patientData, state.session, state.completedActions, state.skippedActions, onComplete]);

  const goToStep = useCallback((step: FlowState['step']) => {
    setState(prev => ({ ...prev, step }));
  }, []);

  const canProceedFromActions = useCallback(() => {
    const blockingPending = state.pendingActions.filter(
      a => a.is_blocking && a.status === 'pending'
    );
    return blockingPending.length === 0;
  }, [state.pendingActions]);

  return {
    state,
    formState,
    setIdentificationMethod,
    updateFormField,
    clearError,
    handleIdentify,
    handleConfirmIdentity,
    handleCompleteAction,
    handleSkipAction,
    handleCompleteCheckin,
    goToStep,
    canProceedFromActions,
  };
}
