'use client';

import { useMemo, useState } from 'react';
import type { DatesSetArg } from '@fullcalendar/core';
import { weeklyHours, workingDays } from '@free-intelligence/core/availability';
import { availabilityEvents, type AvailabilityEventKind } from '../availabilityEvents';
import { FiCalendar } from '../FiCalendar';
import { useCalendarNavigation } from '../useCalendarNavigation';
import { Action, TabHeading } from './controls';
import type { AvailabilityTabProps } from './tab';

const DAYS_SHOWN = 7;

const WEEK_TITLE = { left: 'title', center: '', right: '' };
const DAY_HEADER = { weekday: 'short', day: 'numeric' } as const;

const LEGEND: { kind: AvailabilityEventKind; label: string }[] = [
  { kind: 'available', label: 'Disponible' },
  { kind: 'override', label: 'Horario especial' },
  { kind: 'closed', label: 'Cerrado' },
  { kind: 'day-off', label: 'Día libre' },
];

export function PreviewTab({ form }: AvailabilityTabProps) {
  const { availability } = form;
  const { calendarRef, navigation } = useCalendarNavigation();
  const [from, setFrom] = useState(() => new Date());

  const dayCount = workingDays(availability).length;
  const events = useMemo(() => availabilityEvents(availability, { from, days: DAYS_SHOWN }), [availability, from]);
  const showWeek = ({ start }: DatesSetArg) => setFrom(start);

  return (
    <>
      <TabHeading title="Vista previa">
        {`${weeklyHours(availability)} h por semana en ${dayCount} ${dayCount === 1 ? 'día' : 'días'}.`}
      </TabHeading>
      <div className="fi-availability-row">
        <Action onClick={navigation.goToPrev}>Anterior</Action>
        <Action onClick={navigation.goToToday}>Hoy</Action>
        <Action onClick={navigation.goToNext}>Siguiente</Action>
      </div>
      <FiCalendar
        ref={calendarRef}
        className="fi-availability-preview"
        theme="inherit"
        events={events}
        datesSet={showWeek}
        headerToolbar={WEEK_TITLE}
        dayHeaderFormat={DAY_HEADER}
      />
      <ul className="fi-availability-legend">
        {LEGEND.map(({ kind, label }) => (
          <li key={kind} data-kind={kind}>{label}</li>
        ))}
      </ul>
    </>
  );
}
