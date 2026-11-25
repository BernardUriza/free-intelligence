import type { CalendarOptions } from '@fullcalendar/core';

type HoursOptions = Pick<CalendarOptions, 'slotMinTime' | 'slotMaxTime' | 'slotDuration' | 'slotLabelInterval'>;

/** The stretch of the day a calendar shows, and how finely it is ruled. */
export const CALENDAR_HOURS = {
  business: { slotMinTime: '06:00:00', slotMaxTime: '23:00:00', slotDuration: '01:00:00', slotLabelInterval: '01:00:00' },
  extended: { slotMinTime: '05:00:00', slotMaxTime: '24:00:00', slotDuration: '01:00:00', slotLabelInterval: '01:00:00' },
  compact: { slotMinTime: '07:00:00', slotMaxTime: '22:00:00', slotDuration: '00:30:00', slotLabelInterval: '01:00:00' },
  clinic: { slotMinTime: '07:00:00', slotMaxTime: '21:00:00', slotDuration: '00:30:00', slotLabelInterval: '01:00:00' },
} satisfies Record<string, HoursOptions>;

export type CalendarHours = keyof typeof CALENDAR_HOURS;

export const CALENDAR_DEFAULTS = {
  initialView: 'timeGridWeek',
  locale: 'es',
  headerToolbar: false,
  height: 420,
  allDaySlot: false,
  nowIndicator: true,
  eventDisplay: 'block',
  displayEventEnd: false,
  eventTimeFormat: { hour: '2-digit', minute: '2-digit', hour12: false },
  slotLabelFormat: { hour: 'numeric', minute: '2-digit', hour12: false },
  dayHeaderFormat: { weekday: 'short', day: 'numeric', month: 'short' },
} satisfies CalendarOptions;
