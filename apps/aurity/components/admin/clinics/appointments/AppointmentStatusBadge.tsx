/**
 * AppointmentStatusBadge Component
 *
 * Single Responsibility: renders a styled status indicator.
 * Open/Closed: new statuses are added in appointment.utils.ts
 * without touching this component.
 */

import { getStatusClass } from '@/components/admin/clinics/appointments/appointment.utils';

interface AppointmentStatusBadgeProps {
  status: string;
}

export function AppointmentStatusBadge({ status }: AppointmentStatusBadgeProps) {
  return <span className={getStatusClass(status)}>{status}</span>;
}
