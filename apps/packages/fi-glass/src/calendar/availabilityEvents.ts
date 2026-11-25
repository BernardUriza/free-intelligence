import type { EventInput } from '@fullcalendar/core';
import { toCalendarDate, type DateOverride, type DoctorAvailability, type WeeklySlot } from '@free-intelligence/core/availability';

export type AvailabilityEventKind = 'available' | 'override' | 'closed' | 'day-off';

export interface AvailabilityEventsOptions {
  from: Date;
  days: number;
  availableLabel?: string;
  overrideLabel?: string;
}

export interface BusinessHours {
  daysOfWeek: number[];
  startTime: string;
  endTime: string;
}

const eventClass = (kind: AvailabilityEventKind) => [`fi-calendar-event--${kind}`];

const wholeDay = (kind: AvailabilityEventKind, date: string, reason?: string): EventInput => ({
  id: `${kind}-${date}`,
  start: date,
  allDay: true,
  display: 'background',
  classNames: eventClass(kind),
  extendedProps: { kind, reason },
});

const block = (kind: AvailabilityEventKind, date: string, index: number, hours: { start: string; end: string }, title: string): EventInput => ({
  id: `${kind}-${date}-${index}`,
  title,
  start: `${date}T${hours.start}:00`,
  end: `${date}T${hours.end}:00`,
  classNames: eventClass(kind),
  extendedProps: { kind },
});

export function closedDayEvent({ date, reason }: Pick<DateOverride, 'date' | 'reason'>): EventInput {
  return wholeDay('closed', date, reason);
}

export function availabilityEvents(
  { weeklySchedule, overrides }: Pick<DoctorAvailability, 'weeklySchedule' | 'overrides'>,
  { from, days, availableLabel = 'Disponible', overrideLabel = 'Horario especial' }: AvailabilityEventsOptions,
): EventInput[] {
  const overrideByDate = new Map(overrides.map((override) => [override.date, override]));

  return Array.from({ length: days }, (_, offset) => {
    const day = new Date(from.getFullYear(), from.getMonth(), from.getDate() + offset);
    const date = toCalendarDate(day);
    const override = overrideByDate.get(date);

    if (override?.fullDayClosed) return [closedDayEvent(override)];
    if (override) {
      const { start, end, reason } = override;
      return start && end ? [block('override', date, 0, { start, end }, reason || overrideLabel)] : [];
    }
    const slots = weeklySchedule.filter((slot) => slot.day === day.getDay());
    if (slots.length === 0) return [wholeDay('day-off', date)];
    return slots.map((slot, index) => block('available', date, index, slot, slot.label || availableLabel));
  }).flat();
}

export function businessHours(weeklySchedule: WeeklySlot[]): BusinessHours[] {
  return weeklySchedule.map(({ day, start, end }) => ({ daysOfWeek: [day], startTime: start, endTime: end }));
}
