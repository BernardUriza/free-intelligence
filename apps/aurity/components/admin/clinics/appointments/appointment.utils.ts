/**
 * Appointment Utilities
 *
 * Pure functions for appointment display logic.
 * Single Responsibility: status mapping and date formatting.
 * Open/Closed: extend via the STATUS_CLASS_MAP record without modifying functions.
 */

/** Known appointment statuses mapped to their CSS class names. */
const STATUS_CLASS_MAP: Record<string, string> = {
  scheduled: 'clinic-apt-status-scheduled',
  confirmed: 'clinic-apt-status-confirmed',
  checked_in: 'clinic-apt-status-checked-in',
  in_progress: 'clinic-apt-status-in-progress',
  completed: 'clinic-apt-status-completed',
  cancelled: 'clinic-apt-status-cancelled',
} as const;

const DEFAULT_STATUS_CLASS = 'clinic-apt-status-default';

/** Returns the CSS class for a given appointment status. */
export function getStatusClass(status: string): string {
  return STATUS_CLASS_MAP[status] ?? DEFAULT_STATUS_CLASS;
}

/** Formats an ISO date string for display in es-MX locale. */
export function formatAppointmentDateTime(isoDate: string): string {
  return new Date(isoDate).toLocaleString('es-MX');
}

/** Resolves the display label for an appointment's purpose. */
export function getAppointmentLabel(
  reason: string | null,
  appointmentType: string,
): string {
  return reason || appointmentType;
}
