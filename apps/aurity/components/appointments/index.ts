/**
 * Appointments Components
 * Card: FI-CHECKIN-005 (Phase 2)
 *
 * Re-export all appointments-related UI components.
 */

export { AppointmentsCalendar } from './AppointmentsCalendar';
export { AppointmentsToolbar } from './AppointmentsToolbar';
export { StatusLegend } from './StatusLegend';
export { EmptyState } from './EmptyState';
export { AppointmentModal } from './appointment-modal';
// Backward-compatible aliases
export { AppointmentModal as NewAppointmentModal } from './appointment-modal';
export { AppointmentModal as EditAppointmentModal } from './appointment-modal';
// Re-export types
export type { AppointmentId, AppointmentDraft, AppointmentModalProps } from './appointment-modal';
