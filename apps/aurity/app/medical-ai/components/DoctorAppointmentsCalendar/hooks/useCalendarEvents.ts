/**
 * useCalendarEvents
 *
 * Transforms Appointment[] + DoctorAvailability overrides
 * into a unified FullCalendar event array.
 */

import { useMemo } from 'react';
import type { Appointment } from '@/components/bryntum/utils/appointment-transform.utils';
import type { DoctorAvailability } from '@/components/admin/clinics/availability-designer/types';
import { STATUS_COLORS } from '../constants';

// ============================================================================
// Helpers (pure functions — easily testable)
// ============================================================================

function toAppointmentEvent(apt: Appointment) {
  const colors = STATUS_COLORS[apt.status] ?? STATUS_COLORS.scheduled;
  const startDate = new Date(apt.scheduled_at);
  const endDate = new Date(startDate.getTime() + apt.estimated_duration * 60_000);

  return {
    id: apt.appointment_id,
    title: apt.reason || 'Consulta',
    start: startDate,
    end: endDate,
    backgroundColor: colors.bg,
    borderColor: colors.border,
    textColor: colors.text,
    extendedProps: { appointment: apt },
  };
}

function toClosedDayEvent(override: { date: string; reason?: string }) {
  return {
    id: `closed-${override.date}`,
    start: override.date,
    allDay: true as const,
    display: 'background' as const,
    backgroundColor: 'rgba(239, 68, 68, 0.15)',
    borderColor: 'transparent',
    extendedProps: {
      type: 'closed',
      reason: override.reason || 'No disponible',
    },
  };
}

// ============================================================================
// Hook
// ============================================================================

export function useCalendarEvents(
  appointments: Appointment[],
  availability?: DoctorAvailability | null,
) {
  const appointmentEvents = useMemo(
    () => appointments.map(toAppointmentEvent),
    [appointments],
  );

  const closedDayEvents = useMemo(() => {
    if (!availability?.overrides?.length) return [];
    return availability.overrides
      .filter((o) => o.fullDayClosed)
      .map(toClosedDayEvent);
  }, [availability?.overrides]);

  return useMemo(
    () => [...appointmentEvents, ...closedDayEvents],
    [appointmentEvents, closedDayEvents],
  );
}
