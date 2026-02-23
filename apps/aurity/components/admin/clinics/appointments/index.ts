/**
 * Appointments Module — Barrel Export
 *
 * Interface Segregation: consumers import only what they need.
 */

export { AppointmentsSection } from '@/components/admin/clinics/appointments/AppointmentsSection';
export { AppointmentRow } from '@/components/admin/clinics/appointments/AppointmentRow';
export { AppointmentStatusBadge } from '@/components/admin/clinics/appointments/AppointmentStatusBadge';
export {
  getStatusClass,
  formatAppointmentDateTime,
  getAppointmentLabel,
} from '@/components/admin/clinics/appointments/appointment.utils';
