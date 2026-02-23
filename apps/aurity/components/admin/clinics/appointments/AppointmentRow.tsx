/**
 * AppointmentRow Component
 *
 * Single Responsibility: renders one appointment item within a list.
 * Depends on abstractions (Appointment type) not concretions (DIP).
 */

import { QrCode } from 'lucide-react';
import type { Appointment } from '@/lib/api/clinics';
import { AppointmentStatusBadge } from '@/components/admin/clinics/appointments/AppointmentStatusBadge';
import {
  formatAppointmentDateTime,
  getAppointmentLabel,
} from '@/components/admin/clinics/appointments/appointment.utils';

interface AppointmentRowProps {
  appointment: Appointment;
}

export function AppointmentRow({ appointment }: AppointmentRowProps) {
  return (
    <div className="clinic-apt-row">
      <div className="fi-flex-between">
        <div>
          <p className="clinic-apt-time">
            {formatAppointmentDateTime(appointment.scheduled_at)}
          </p>
          <p className="clinic-apt-reason">
            {getAppointmentLabel(appointment.reason, appointment.appointment_type)}
          </p>
        </div>

        <div className="text-right">
          <div className="fi-flex-gap">
            <QrCode className="clinic-apt-code-icon" />
            <span className="clinic-apt-code">{appointment.checkin_code}</span>
          </div>
          <AppointmentStatusBadge status={appointment.status} />
        </div>
      </div>
    </div>
  );
}
