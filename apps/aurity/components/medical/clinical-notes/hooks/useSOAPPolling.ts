/**
 * useSOAPPolling Hook
 *
 * Handles SOAP note fetching and polling.
 */

import { useState, useEffect } from 'react';
import {
  medicalWorkflowApi,
  type SOAPNoteResponse,
} from '@aurity-standalone/api-client/medical-workflow';
import type { SOAPData, SOAPGenerationStatus } from '../types';
import { POLLING_CONFIG, DEFAULT_VITAL_SIGNS } from '../constants';

interface UseSOAPPollingResult {
  isLoading: boolean;
  status: SOAPGenerationStatus;
  attempts: number;
}

export function useSOAPPolling(
  sessionId: string,
  onSuccess: (data: SOAPData) => void,
  onError: (error: string) => void
): UseSOAPPollingResult {
  const [isLoading, setIsLoading] = useState(true);
  const [status, setStatus] = useState<SOAPGenerationStatus>(null);
  const [attempts, setAttempts] = useState(0);

  useEffect(() => {
    if (!sessionId) {
      onError('No session ID provided');
      setIsLoading(false);
      return;
    }

    let pollingTimer: NodeJS.Timeout | null = null;
    let isMounted = true;

    const checkSOAPStatus = async (): Promise<boolean> => {
      try {
        const monitorOutput =
          await medicalWorkflowApi.getSessionMonitor(sessionId);
        const hasCompleted =
          monitorOutput.includes('SOAP_GENERATION') &&
          monitorOutput.includes('✅');
        const isInProgress =
          monitorOutput.includes('SOAP_GENERATION') &&
          (monitorOutput.includes('⏳') || monitorOutput.includes('🔄'));

        if (hasCompleted) {
          setStatus('completed');
          return true;
        }
        if (isInProgress) {
          setStatus('in_progress');
          return false;
        }
        setStatus('pending');
        return false;
      } catch {
        return false;
      }
    };

    const parseSOAPResponse = (response: SOAPNoteResponse): SOAPData => {
      const { soap_note } = response;
      return {
        chiefComplaint: soap_note.subjective.chief_complaint || '',
        hpi: soap_note.subjective.history_present_illness || '',
        allergies: [],
        currentMedications: [],
        vitalSigns: DEFAULT_VITAL_SIGNS,
        physicalExam: soap_note.objective.physical_exam || '',
        primaryDiagnosis: soap_note.assessment.primary_diagnosis
          ? {
              code: '',
              description: soap_note.assessment.primary_diagnosis,
              severity: 'Moderada',
            }
          : null,
        differentialDiagnoses: soap_note.assessment.differential_diagnoses.map(
          (d) => ({ code: '', description: d })
        ),
        medications: [],
        diagnosticTests: soap_note.plan.studies || [],
        followUp: soap_note.plan.follow_up || '',
      };
    };

    const fetchSOAPNotes = async (): Promise<boolean> => {
      try {
        const response = await medicalWorkflowApi.getSOAPNote(sessionId);
        if (isMounted) {
          onSuccess(parseSOAPResponse(response));
          setStatus('completed');
          setIsLoading(false);
        }
        return true;
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : String(err);
        const isNoDataError =
          errorMsg.includes('No SOAP data found') ||
          errorMsg.includes('404') ||
          errorMsg.includes('Task SOAP_GENERATION does not exist');

        if (!isNoDataError && isMounted) {
          onError('Failed to load SOAP notes');
          setStatus('error');
          setIsLoading(false);
          return true;
        }
        return false;
      }
    };

    const poll = async (attempt: number) => {
      if (!isMounted) return;

      if (attempt >= POLLING_CONFIG.maxAttempts) {
        onError('SOAP generation timeout. Please refresh to try again.');
        setStatus('error');
        setIsLoading(false);
        return;
      }

      setAttempts(attempt + 1);

      const isReady = await checkSOAPStatus();
      if (isReady) {
        const success = await fetchSOAPNotes();
        if (!success && isMounted) {
          pollingTimer = setTimeout(
            () => poll(attempt + 1),
            POLLING_CONFIG.intervalMs
          );
        }
      } else if (isMounted) {
        pollingTimer = setTimeout(
          () => poll(attempt + 1),
          POLLING_CONFIG.intervalMs
        );
      }
    };

    const initialize = async () => {
      setIsLoading(true);

      const initialSuccess = await fetchSOAPNotes();
      if (initialSuccess || !isMounted) return;

      const isReady = await checkSOAPStatus();
      if (isReady) {
        await fetchSOAPNotes();
        return;
      }

      try {
        await medicalWorkflowApi.startSOAPGeneration(sessionId);
        setStatus('in_progress');
        setAttempts(0);
        pollingTimer = setTimeout(() => poll(1), POLLING_CONFIG.intervalMs);
      } catch {
        if (isMounted) {
          onError('Failed to start SOAP generation');
          setIsLoading(false);
        }
      }
    };

    initialize();

    return () => {
      isMounted = false;
      if (pollingTimer) clearTimeout(pollingTimer);
    };
  }, [sessionId, onSuccess, onError]);

  return { isLoading, status, attempts };
}
