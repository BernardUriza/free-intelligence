/**
 * useCalendarNavigation
 *
 * Encapsulates prev / next / today navigation + event/date click
 * handlers for FullCalendar.
 */

import { useCallback, type RefObject } from 'react';
import type FullCalendar from '@fullcalendar/react';
import type { EventClickArg } from '@fullcalendar/core';
import type { DateClickArg } from '@fullcalendar/interaction';
import type { Appointment } from '@/components/bryntum/utils/appointment-transform.utils';

interface UseCalendarNavigationArgs {
  calendarRef: RefObject<FullCalendar | null>;
  onDateChange: (date: Date) => void;
  onSelectAppointment: (appointment: Appointment) => void;
  onCreateAppointment: (date: Date) => void;
}

export function useCalendarNavigation({
  calendarRef,
  onDateChange,
  onSelectAppointment,
  onCreateAppointment,
}: UseCalendarNavigationArgs) {
  const goToToday = useCallback(() => {
    calendarRef.current?.getApi().today();
    onDateChange(new Date());
  }, [calendarRef, onDateChange]);

  const goToPrev = useCallback(() => {
    const api = calendarRef.current?.getApi();
    if (api) {
      api.prev();
      onDateChange(api.getDate());
    }
  }, [calendarRef, onDateChange]);

  const goToNext = useCallback(() => {
    const api = calendarRef.current?.getApi();
    if (api) {
      api.next();
      onDateChange(api.getDate());
    }
  }, [calendarRef, onDateChange]);

  const handleEventClick = useCallback(
    (info: EventClickArg) => {
      const appointment = info.event.extendedProps.appointment as Appointment | undefined;
      if (appointment) {
        onSelectAppointment(appointment);
      }
    },
    [onSelectAppointment],
  );

  /** Blocks clicks on slots in the past (before current hour). */
  const handleDateClick = useCallback(
    (info: DateClickArg) => {
      const now = new Date();
      const currentHourStart = new Date(
        now.getFullYear(),
        now.getMonth(),
        now.getDate(),
        now.getHours(),
        0,
        0,
      );

      if (info.date < currentHourStart) return;

      onCreateAppointment(info.date);
    },
    [onCreateAppointment],
  );

  return { goToToday, goToPrev, goToNext, handleEventClick, handleDateClick };
}
