/**
 * Patient Components Barrel Export
 *
 * SOLID-compliant patient selection components.
 * All components follow Single Responsibility and are fully reusable.
 */

export { PatientCard, type PatientCardProps } from './PatientCard';
export { SessionCard, type SessionCardProps } from './SessionCard';
export { PatientList, type PatientListProps } from './PatientList';
export { SessionList, type SessionListProps } from './SessionList';
export { PatientSelector, type PatientSelectorProps } from './PatientSelector';
export { PatientForm, type PatientFormProps } from './PatientForm';
export { PatientModal, type PatientModalProps } from './PatientModal';

// Shared form components
export { PatientFormFields, type PatientFormFieldsProps } from './PatientFormFields';
export {
  usePatientFormValidation,
  validatePatientField,
  validatePatientForm,
  validateCURP,
  type PatientFormData,
  type PatientFormErrors,
  type PatientFormField,
} from './usePatientFormValidation';
