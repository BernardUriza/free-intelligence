/**
 * fi-glass/calendar: the week/day/month calendar and the availability editor.
 * FullCalendar 6 is an optional peer; import `fi-glass/calendar.css` once and re-tint with `--fi-calendar-*`.
 */
export { FiCalendar, type FiCalendarHandle, type FiCalendarProps } from './FiCalendar';
export { CALENDAR_DEFAULTS, CALENDAR_HOURS, type CalendarHours } from './presets';
export { useCalendarNavigation, type CalendarNavigation, type UseCalendarNavigationResult } from './useCalendarNavigation';
export {
  availabilityEvents,
  businessHours,
  closedDayEvent,
  type AvailabilityEventKind,
  type AvailabilityEventsOptions,
  type BusinessHours,
} from './availabilityEvents';
export { AvailabilityEditor, type AvailabilityEditorProps, type AvailabilityTab } from './availability/AvailabilityEditor';
export { useAvailabilityForm, type AvailabilityForm } from './availability/useAvailabilityForm';
