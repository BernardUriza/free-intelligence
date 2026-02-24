/**
 * ClinicalNotes Types
 *
 * All type definitions for the clinical notes module.
 * SRP: type declarations only.
 *
 * @refactored 2026-02-22
 */

import type { LucideIcon } from 'lucide-react';

// ---------------------------------------------------------------------------
// Component Props
// ---------------------------------------------------------------------------

export interface ClinicalNotesProps {
  sessionId: string;
  onNext?: () => void;
  onPrevious?: () => void;
  className?: string;
}

// ---------------------------------------------------------------------------
// Domain Models
// ---------------------------------------------------------------------------

export interface VitalSigns {
  temperature: string;
  heartRate: string;
  bloodPressure: string;
  respiratoryRate: string;
  oxygenSaturation: string;
}

export interface Diagnosis {
  code: string;
  description: string;
  severity?: string;
}

export interface Medication {
  name: string;
  dose: string;
  frequency: string;
  duration?: string;
  route?: string;
}

export interface SOAPData {
  chiefComplaint: string;
  hpi: string;
  allergies: string[];
  currentMedications: string[];
  vitalSigns: VitalSigns;
  physicalExam: string;
  primaryDiagnosis: Diagnosis | null;
  differentialDiagnoses: Diagnosis[];
  medications: Medication[];
  diagnosticTests: string[];
  followUp: string;
}

// ---------------------------------------------------------------------------
// AI Types
// ---------------------------------------------------------------------------

export interface AISuggestion {
  type: 'warning' | 'suggestion' | 'insight';
  content: string;
  confidence: number;
  source: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface SuggestionStyles {
  bg: string;
  border: string;
  text: string;
  icon: LucideIcon;
}

// ---------------------------------------------------------------------------
// Status Types
// ---------------------------------------------------------------------------

export type SOAPGenerationStatus =
  | 'pending'
  | 'in_progress'
  | 'completed'
  | 'error'
  | null;

export type SectionOrder = 'SOAP' | 'APSO';

export interface SaveMessage {
  type: 'success' | 'error';
  text: string;
}

// ---------------------------------------------------------------------------
// Form State & Handlers (used by hooks and section components)
// ---------------------------------------------------------------------------

/** Core SOAP data + all ephemeral UI state. */
export interface ClinicalNotesFormState {
  soapData: SOAPData;
  error: string | null;
  isLoading: boolean;
  pollingStatus: SOAPGenerationStatus;
  pollingAttempts: number;

  // UI toggles
  showAIPanel: boolean;
  showPreviewModal: boolean;
  showChatbot: boolean;
  sectionOrder: SectionOrder;
  voiceActive: string | null;

  // Inline inputs
  icd10Search: string;
  showICD10Dropdown: boolean;
  newAllergy: string;
  newMedication: Medication;

  // Save
  isSaving: boolean;
  isSaved: boolean;
  saveMessage: SaveMessage | null;

  // Computed
  isComplete: boolean;
}

/** All callbacks exposed to section components. */
export interface ClinicalNotesFormHandlers {
  // SOAP data
  updateField: <K extends keyof SOAPData>(field: K, value: SOAPData[K]) => void;
  updateVitalSign: (sign: keyof VitalSigns, value: string) => void;
  fillNormalVitals: () => void;
  setSOAPData: React.Dispatch<React.SetStateAction<SOAPData>>;

  // Allergies
  addAllergy: () => void;
  removeAllergy: (index: number) => void;
  setNewAllergy: (value: string) => void;

  // Medications
  addMedication: () => void;
  removeMedication: (index: number) => void;
  setNewMedication: React.Dispatch<React.SetStateAction<Medication>>;

  // Diagnosis
  selectDiagnosis: (diagnosis: Diagnosis) => void;
  clearPrimaryDiagnosis: () => void;
  removeDifferentialDiagnosis: (index: number) => void;
  setICD10Search: (value: string) => void;
  setShowICD10Dropdown: (value: boolean) => void;

  // Diagnostic tests
  toggleDiagnosticTest: (test: string) => void;
  removeDiagnosticTest: (index: number) => void;

  // UI toggles
  setShowAIPanel: (fn: (prev: boolean) => boolean) => void;
  setShowPreviewModal: (value: boolean) => void;
  setShowChatbot: (fn: (prev: boolean) => boolean) => void;
  setSectionOrder: (fn: (prev: SectionOrder) => SectionOrder) => void;
  setVoiceActive: (fn: (prev: string | null) => string | null) => void;

  // Save & navigation
  handleSave: () => Promise<void>;
}
