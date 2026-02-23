/**
 * AppointmentsSection Component
 *
 * Orchestrates the appointment list within a clinic detail panel.
 * Single Responsibility: compose header, list, and empty state.
 * Delegates row rendering to AppointmentRow (SRP).
 *
 * Card: FI-CHECKIN-002
 */

import { Calendar } from 'lucide-react';
import type { Appointment } from '@/lib/api/clinics';
import { AppointmentRow } from '@/components/admin/clinics/appointments/AppointmentRow';

interface AppointmentsSectionProps {
  appointments: Appointment[];
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
        {appointments.length === 0 ? (
          <p className="clinic-empty-text">No hay citas registradas</p>
        ) : (
          appointments.map((apt) => (
            <AppointmentRow key={apt.appointment_id} appointment={apt} />
          ))
        )}
      </div>
    </div>
  );
}
