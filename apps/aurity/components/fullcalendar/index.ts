/**
 * FullCalendar Component Library
 *
 * Reusable FullCalendar components for the Aurity design system.
 *
 * @example
 * ```tsx
 * import {
 *   CalendarCore,
 *   useFullCalendar,
 *   availabilityToEvents,
 *   CALENDAR_PRESETS
 * } from '@/components/fullcalendar';
 *
 * function MyComponent({ availability }) {
 *   const { events, calendarRef, navigation } = useFullCalendar(availability);
 *
 *   return (
 *     <>
 *       <button onClick={navigation.goToPrev}>Prev</button>
 *       <button onClick={navigation.goToToday}>Today</button>
 *       <button onClick={navigation.goToNext}>Next</button>
 *       <CalendarCore ref={calendarRef} events={events} />
 *     </>
 *   );
 * }
 * ```
 */

// ============================================================================
// Types
// ============================================================================

export type {
  CalendarEvent,
  CalendarEventCategory,
  TimeSlotConfig,
  CalendarViewConfig,
  CalendarThemeConfig,
  EventStyleConfig,
  CalendarConfig,
  CalendarCoreProps,
  UseCalendarEventsResult,
  CalendarNavigation,
} from './types/calendar.types';

// ============================================================================
// Config
// ============================================================================

export {
  TIME_SLOT_PRESETS,
  VIEW_PRESETS,
  THEME_PRESETS,
  EVENT_STYLES,
  CALENDAR_PRESETS,
  TIME_FORMAT,
  DAY_HEADER_FORMAT,
  SLOT_LABEL_FORMAT,
} from './config/calendar-presets.config';

// ============================================================================
// Hooks
// ============================================================================

export {
  useCalendarEvents,
  useCalendarNavigation,
  useFullCalendar,
} from './hooks/useCalendarEvents';

// ============================================================================
// Utils
// ============================================================================

export {
  applyEventStyle,
  generateDateRange,
  formatDateISO,
  availabilityToEvents,
  createAvailableEvent,
  createClosedDayEvent,
  createOverrideEvent,
  filterEventsByDateRange,
  countEventsByCategory,
} from './utils/event-transform.utils';

// ============================================================================
// Core Component
// ============================================================================

export { CalendarCore } from './core/CalendarCore';
export { default } from './core/CalendarCore';
