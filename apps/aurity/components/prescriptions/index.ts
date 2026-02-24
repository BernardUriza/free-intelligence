/**
 * Prescription Components
 *
 * UI components for the prescription template engine.
 *
 * @author Bernard Uriza Orozco
 * @created 2025-12-28
 * @refactored 2026-02-22
 * @card FI-RX-002, FI-RX-UI-003
 */

// Form Components
export { MedicationForm } from "./MedicationForm";
export { MedicationList } from "./MedicationList";
export { PrescriptionForm } from "./PrescriptionForm";
export { PrescriptionPreview } from "./PrescriptionPreview";
export { PrescriptionStatusBadge } from "./PrescriptionStatusBadge";

// Tab Components
export { PatientTab } from "./tabs/PatientTab";
export { PhysicianTab } from "./tabs/PhysicianTab";
export { DiagnosisTab } from "./tabs/DiagnosisTab";
export { MedicationsTab } from "./tabs/MedicationsTab";
export { PreviewTab } from "./tabs/PreviewTab";

// Hooks
export { usePrescriptionForm } from "./hooks/usePrescriptionForm";
export { usePrescriptionPreview } from "./hooks/usePrescriptionPreview";

// Types
export type {
  PrescriptionFormProps,
  PrescriptionTab,
  PrescriptionFormState,
  PrescriptionFormHandlers,
} from "./types";

// Safety Components (FI-RX-UI-003)
export { SafetyBadge, getSafetyStatus, type SafetyStatus } from "./SafetyBadge";
export { InteractionAlert } from "./InteractionAlert";
export { AllergyAlert } from "./AllergyAlert";
export { SafetyAlerts } from "./SafetyAlerts";
