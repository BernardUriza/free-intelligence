/**
 * useClinicalNotesForm Hook
 *
 * Centralises all form state, CRUD handlers, and UI toggles
 * for the ClinicalNotes component.
 * SRP: state management only — no rendering.
 *
 * @created 2026-02-22
 */

'use client';

import { useState, useCallback, useMemo } from 'react';
import type {
  SOAPData,
  VitalSigns,
  Medication,
  Diagnosis,
  ClinicalNotesProps,
  ClinicalNotesFormState,
  ClinicalNotesFormHandlers,
  SectionOrder,
} from '../types';
import { INITIAL_SOAP_DATA, NORMAL_VITAL_SIGNS } from '../constants';
import { useAISuggestions, useSOAPPolling } from './index';
import { useSaveSOAP } from './useSaveSOAP';
import type { AISuggestion } from '../types';

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useClinicalNotesForm(props: ClinicalNotesProps) {
  const { sessionId } = props;

  // --- SOAP data ---
  const [soapData, setSOAPData] = useState<SOAPData>(INITIAL_SOAP_DATA);
  const [error, setError] = useState<string | null>(null);

  // --- UI toggles ---
  const [showAIPanel, setShowAIPanel] = useState(true);
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [showChatbot, setShowChatbot] = useState(false);
  const [sectionOrder, setSectionOrder] = useState<SectionOrder>('SOAP');
  const [voiceActive, setVoiceActive] = useState<string | null>(null);

  // --- Inline search / input ---
  const [icd10Search, setICD10Search] = useState('');
  const [showICD10Dropdown, setShowICD10Dropdown] = useState(false);
  const [newAllergy, setNewAllergy] = useState('');
  const [newMedication, setNewMedication] = useState<Medication>({
    name: '',
    dose: '',
    frequency: '',
  });

  // --- Polling ---
  const handleSOAPSuccess = useCallback((data: SOAPData) => {
    setSOAPData(data);
    setError(null);
  }, []);

  const handleSOAPError = useCallback((msg: string) => {
    setError(msg);
  }, []);

  const { isLoading, status: pollingStatus, attempts: pollingAttempts } =
    useSOAPPolling(sessionId, handleSOAPSuccess, handleSOAPError);

  // --- Save ---
  const { isSaving, isSaved, saveMessage, handleSave } = useSaveSOAP(
    sessionId,
    soapData,
  );

  // --- AI suggestions ---
  const aiSuggestions: AISuggestion[] = useAISuggestions(soapData);

  // --- Computed ---
  const isComplete =
    soapData.chiefComplaint.trim().length > 0 &&
    soapData.primaryDiagnosis !== null;

  // --- Generic field updater ---
  const updateField = useCallback(
    <K extends keyof SOAPData>(field: K, value: SOAPData[K]) => {
      setSOAPData((prev) => ({ ...prev, [field]: value }));
    },
    [],
  );

  const updateVitalSign = useCallback(
    (sign: keyof VitalSigns, value: string) => {
      setSOAPData((prev) => ({
        ...prev,
        vitalSigns: { ...prev.vitalSigns, [sign]: value },
      }));
    },
    [],
  );

  const fillNormalVitals = useCallback(() => {
    setSOAPData((prev) => ({ ...prev, vitalSigns: NORMAL_VITAL_SIGNS }));
  }, []);

  // --- Allergies ---
  const addAllergy = useCallback(() => {
    const trimmed = newAllergy.trim();
    if (!trimmed) return;
    setSOAPData((prev) => ({
      ...prev,
      allergies: [...prev.allergies, trimmed],
    }));
    setNewAllergy('');
  }, [newAllergy]);

  const removeAllergy = useCallback((index: number) => {
    setSOAPData((prev) => ({
      ...prev,
      allergies: prev.allergies.filter((_, i) => i !== index),
    }));
  }, []);

  // --- Medications ---
  const addMedication = useCallback(() => {
    if (!newMedication.name.trim()) return;
    setSOAPData((prev) => ({
      ...prev,
      medications: [...prev.medications, { ...newMedication }],
    }));
    setNewMedication({ name: '', dose: '', frequency: '' });
  }, [newMedication]);

  const removeMedication = useCallback((index: number) => {
    setSOAPData((prev) => ({
      ...prev,
      medications: prev.medications.filter((_, i) => i !== index),
    }));
  }, []);

  // --- Diagnosis ---
  const selectDiagnosis = useCallback((diagnosis: Diagnosis) => {
    setSOAPData((prev) => ({ ...prev, primaryDiagnosis: diagnosis }));
    setICD10Search('');
    setShowICD10Dropdown(false);
  }, []);

  const clearPrimaryDiagnosis = useCallback(() => {
    setSOAPData((prev) => ({ ...prev, primaryDiagnosis: null }));
  }, []);

  const removeDifferentialDiagnosis = useCallback((index: number) => {
    setSOAPData((prev) => ({
      ...prev,
      differentialDiagnoses: prev.differentialDiagnoses.filter(
        (_, i) => i !== index,
      ),
    }));
  }, []);

  // --- Diagnostic tests ---
  const toggleDiagnosticTest = useCallback((test: string) => {
    setSOAPData((prev) => ({
      ...prev,
      diagnosticTests: prev.diagnosticTests.includes(test)
        ? prev.diagnosticTests.filter((t) => t !== test)
        : [...prev.diagnosticTests, test],
    }));
  }, []);

  const removeDiagnosticTest = useCallback((index: number) => {
    setSOAPData((prev) => ({
      ...prev,
      diagnosticTests: prev.diagnosticTests.filter((_, i) => i !== index),
    }));
  }, []);

  // --- Assemble return values ---
  const state: ClinicalNotesFormState = useMemo(
    () => ({
      soapData,
      error,
      isLoading,
      pollingStatus,
      pollingAttempts,
      showAIPanel,
      showPreviewModal,
      showChatbot,
      sectionOrder,
      voiceActive,
      icd10Search,
      showICD10Dropdown,
      newAllergy,
      newMedication,
      isSaving,
      isSaved,
      saveMessage,
      isComplete,
    }),
    [
      soapData,
      error,
      isLoading,
      pollingStatus,
      pollingAttempts,
      showAIPanel,
      showPreviewModal,
      showChatbot,
      sectionOrder,
      voiceActive,
      icd10Search,
      showICD10Dropdown,
      newAllergy,
      newMedication,
      isSaving,
      isSaved,
      saveMessage,
      isComplete,
    ],
  );

  const handlers: ClinicalNotesFormHandlers = useMemo(
    () => ({
      updateField,
      updateVitalSign,
      fillNormalVitals,
      setSOAPData,
      addAllergy,
      removeAllergy,
      setNewAllergy,
      addMedication,
      removeMedication,
      setNewMedication,
      selectDiagnosis,
      clearPrimaryDiagnosis,
      removeDifferentialDiagnosis,
      setICD10Search,
      setShowICD10Dropdown,
      toggleDiagnosticTest,
      removeDiagnosticTest,
      setShowAIPanel,
      setShowPreviewModal,
      setShowChatbot,
      setSectionOrder,
      setVoiceActive,
      handleSave,
    }),
    [
      updateField,
      updateVitalSign,
      fillNormalVitals,
      addAllergy,
      removeAllergy,
      addMedication,
      removeMedication,
      selectDiagnosis,
      clearPrimaryDiagnosis,
      removeDifferentialDiagnosis,
      toggleDiagnosticTest,
      removeDiagnosticTest,
      handleSave,
    ],
  );

  return { state, handlers, aiSuggestions } as const;
}
