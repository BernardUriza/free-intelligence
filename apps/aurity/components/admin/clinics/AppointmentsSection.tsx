/**
 * AppointmentsSection Component
 *
 * Renders the appointments list within a clinic detail panel.
 * Single Responsibility: Appointment display within clinic admin.
 *
 * Card: FI-CHECKIN-002
 */

import { Calendar, QrCode } from 'lucide-react';
import type { Appointment } from '@/lib/api/clinics';

interface AppointmentsSectionProps {
  appointments: Appointment[];
}

function getStatusClass(status: string): string {
  switch (status) {
    case 'scheduled':
      return 'clinic-apt-status-scheduled';
    case 'confirmed':
      return 'clinic-apt-status-confirmed';
    case 'checked_in':
      return 'clinic-apt-status-checked-in';
    default:
      return 'clinic-apt-status-default';
  }
}

export function AppointmentsSection({ appointments }: AppointmentsSectionProps) {
  return (
    <div>
      <div className="clinic-section-header">
        <h3 className="clinic-section-title">
          <Calendar className="clinic-section-icon" />
          Citas ({appointments.length})
        </h3>
      </div>
      <div className="clinic-apt-list">
        {appointments.map((apt) => (
          <div key={apt.appointment_id} className="clinic-apt-row">
            <div className="fi-flex-between">
              <div>
                <p className="clinic-apt-time">
                  {new Date(apt.scheduled_at).toLocaleString('es-MX')}
                </p>
                <p className="clinic-apt-reason">{apt.reason || apt.appointment_type}</p>
              </div>
              <div className="text-right">
                <div className="fi-flex-gap">
                  <QrCode className="clinic-apt-code-icon" />
                  <span className="clinic-apt-code">{apt.checkin_code}</span>
                </div>
                <span className={getStatusClass(apt.status)}>
                  {apt.status}
                </span>
              </div>
            </div>
          </div>
        ))}
        {appointments.length === 0 && (
          <p className="clinic-empty-text">No hay citas registradas</p>
        )}
      </div>
    </div>
  );
}
