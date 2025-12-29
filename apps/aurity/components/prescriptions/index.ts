/**
 * Prescription Components
 *
 * UI components for the prescription template engine.
 *
 * @author Bernard Uriza Orozco
 * @created 2025-12-28
 * @card FI-RX-002, FI-RX-UI-003
 */

// Form Components
export { MedicationForm } from "./MedicationForm";
export { MedicationList } from "./MedicationList";
export { PrescriptionForm } from "./PrescriptionForm";
export { PrescriptionPreview } from "./PrescriptionPreview";
export { PrescriptionStatusBadge } from "./PrescriptionStatusBadge";

// Safety Components (FI-RX-UI-003)
export { SafetyBadge, getSafetyStatus, type SafetyStatus } from "./SafetyBadge";
export { InteractionAlert } from "./InteractionAlert";
export { AllergyAlert } from "./AllergyAlert";
export { SafetyAlerts } from "./SafetyAlerts";
