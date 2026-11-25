/**
 * useCalendarEvents
 *
 * Transforms Appointment[] + DoctorAvailability overrides
 * into a unified FullCalendar event array.
 */

import { useMemo } from 'react';
import type { Appointment } from '@/components/bryntum/utils/appointment-transform.utils';
import type { DoctorAvailability } from '@free-intelligence/core/availability';
import { closedDayEvent } from 'fi-glass/calendar';
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
      .map(closedDayEvent);
  }, [availability?.overrides]);

  return useMemo(
    () => [...appointmentEvents, ...closedDayEvents],
    [appointmentEvents, closedDayEvents],
  );
}
