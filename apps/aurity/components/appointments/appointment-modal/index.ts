/**
 * AppointmentModal Module
 *
 * Unified create/edit modal for appointments.
 *
 * Modular structure:
 * - types.ts: TypeScript interfaces (AppointmentDraft, AppointmentModalProps)
 * - hooks/: usePatientSearch (debounced search + creation), useAppointmentForm (form state)
 * - components/: PatientSearchField, AppointmentFormFields
 */

export { AppointmentModal, default } from './AppointmentModal';
export type { AppointmentId, AppointmentDraft, AppointmentModalProps } from './types';
