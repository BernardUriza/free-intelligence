/**
 * Prescription Form Types
 *
 * Shared interfaces and props for prescription form components.
 * Single Responsibility: type definitions only.
 *
 * @author Bernard Uriza Orozco
 * @created 2025-12-28
 * @refactored 2026-02-22
 */

import type {
  Medication,
  PatientInfo,
  PhysicianInfo,
  Prescription,
} from "@/lib/api/prescriptions";

/** Top-level props for the PrescriptionForm composition root. */
export interface PrescriptionFormProps {
  sessionId?: string;
  initialPatient?: Partial<PatientInfo>;
  initialPhysician?: Partial<PhysicianInfo>;
  initialDiagnosis?: string;
  onComplete?: (prescription: Prescription) => void;
}

/** Tab identifiers used across the form. */
export type PrescriptionTab =
  | "patient"
  | "physician"
  | "diagnosis"
  | "medications"
  | "preview";

/** Shared state shape exposed by usePrescriptionForm. */
export interface PrescriptionFormState {
  patient: PatientInfo;
  physician: PhysicianInfo;
  diagnosis: string;
  diagnosisCode: string;
  medications: Medication[];
  generalInstructions: string;
  nextAppointment: string;
  activeTab: PrescriptionTab;
  editingMedIndex: number | null;
  isSubmitting: boolean;
  createdPrescription: Prescription | null;
  allergyInput: string;
}

/** Handlers exposed by usePrescriptionForm. */
export interface PrescriptionFormHandlers {
  setPatient: React.Dispatch<React.SetStateAction<PatientInfo>>;
  setPhysician: React.Dispatch<React.SetStateAction<PhysicianInfo>>;
  setDiagnosis: (value: string) => void;
  setDiagnosisCode: (value: string) => void;
  setGeneralInstructions: (value: string) => void;
  setNextAppointment: (value: string) => void;
  setActiveTab: (tab: string) => void;
  setAllergyInput: (value: string) => void;
  handleAddMedication: (med: Medication) => void;
  handleEditMedication: (index: number) => void;
  handleRemoveMedication: (index: number) => void;
  handleCancelEditMedication: () => void;
  handleAddAllergy: () => void;
  handleRemoveAllergy: (allergy: string) => void;
  handleSubmit: () => Promise<void>;
  handleSign: () => Promise<void>;
  handlePrint: () => void;
}
