/**
 * useSaveSOAP Hook
 *
 * Encapsulates the save-to-backend logic and save status.
 * SRP: persistence side-effect only.
 *
 * @created 2026-02-22
 */

'use client';

import { useState, useCallback } from 'react';
import { medicalWorkflowApi } from '@aurity-standalone/api-client/medical-workflow';
import type { SOAPData, SaveMessage } from '../types';

interface UseSaveSOAPReturn {
  isSaving: boolean;
  isSaved: boolean;
  saveMessage: SaveMessage | null;
  handleSave: () => Promise<void>;
}

/**
 * Transforms front-end SOAPData into the backend dto shape
 * and persists via the medical workflow API.
 */
export function useSaveSOAP(
  sessionId: string,
  soapData: SOAPData,
): UseSaveSOAPReturn {
  const [isSaving, setIsSaving] = useState(false);
  const [isSaved, setIsSaved] = useState(false);
  const [saveMessage, setSaveMessage] = useState<SaveMessage | null>(null);

  const handleSave = useCallback(async () => {
    setIsSaving(true);
    setIsSaved(false);
    setSaveMessage(null);

    try {
      const backendSOAP = {
        subjective: {
          chiefComplaint: soapData.chiefComplaint,
          hpi: soapData.hpi,
          pastMedicalHistory: soapData.currentMedications,
          allergies: soapData.allergies,
        },
        objective: {
          vitalSigns: Object.entries(soapData.vitalSigns)
            .filter(([, v]) => v)
            .map(([k, v]) => `${k}: ${v}`)
            .join(', '),
          physicalExam: soapData.physicalExam,
        },
        assessment: {
          primaryDiagnosis: soapData.primaryDiagnosis?.description ?? '',
          differentialDiagnoses: soapData.differentialDiagnoses.map(
            (d) => d.description,
          ),
        },
        plan: {
          medications: soapData.medications,
          studies: soapData.diagnosticTests,
          followUp: soapData.followUp,
          treatment: '',
        },
      };

      const result = await medicalWorkflowApi.updateSOAP(
        sessionId,
        backendSOAP,
      );

      setIsSaved(true);
      setSaveMessage({
        type: 'success',
        text:
          result.orders_created > 0
            ? `Notas guardadas. ${result.orders_created} órdenes médicas creadas automáticamente.`
            : 'Notas guardadas correctamente.',
      });

      setTimeout(() => setSaveMessage(null), 5000);
    } catch (err) {
      setSaveMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Error al guardar',
      });
      setIsSaved(false);
    } finally {
      setIsSaving(false);
    }
  }, [sessionId, soapData]);

  return { isSaving, isSaved, saveMessage, handleSave };
}
