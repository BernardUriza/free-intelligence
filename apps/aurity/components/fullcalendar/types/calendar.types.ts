/**
 * FullCalendar Types
 *
 * Type definitions for the reusable FullCalendar component
 */

import type { EventInput } from '@fullcalendar/core';

// ============================================================================
// Event Types
// ============================================================================

/**
 * Calendar event categories for styling
 */
export type CalendarEventCategory =
  | 'available'    // Normal availability slot
  | 'override'     // Date-specific override
  | 'closed'       // Full day closed
  | 'dayOff';      // No working hours

/**
 * Extended event with category metadata
 */
export interface CalendarEvent extends EventInput {
  category?: CalendarEventCategory;
  extendedProps?: {
    category?: CalendarEventCategory;
    reason?: string;
    [key: string]: unknown;
  };
}

// ============================================================================
// Configuration Types
// ============================================================================

/**
 * Time slot configuration
 */
export interface TimeSlotConfig {
  minTime: string;  // e.g., "06:00:00"
  maxTime: string;  // e.g., "23:00:00"
  slotDuration: string;  // e.g., "01:00:00"
  slotLabelInterval: string;  // e.g., "01:00:00"
}

/**
 * Calendar view configuration
 */
export interface CalendarViewConfig {
  initialView: 'timeGridWeek' | 'timeGridDay' | 'dayGridMonth';
  headerToolbar: boolean | object;
  height: number | 'auto';
  locale: string;
}

/**
 * Theme configuration for dark/light mode
 */
export interface CalendarThemeConfig {
  borderColor: string;
  pageBgColor: string;
  neutralBgColor: string;
  todayBgColor: string;
  nowIndicatorColor: string;
}

/**
 * Event style configuration per category
 */
export interface EventStyleConfig {
  backgroundColor: string;
  borderColor: string;
  textColor: string;
}

/**
 * Complete calendar configuration
 */
export interface CalendarConfig {
  timeSlot: TimeSlotConfig;
  view: CalendarViewConfig;
  theme: CalendarThemeConfig;
  eventStyles: Record<CalendarEventCategory, EventStyleConfig>;
}

// ============================================================================
// Props Types
// ============================================================================

/**
 * CalendarCore component props
 */
export interface CalendarCoreProps {
  /** Events to display */
  events: CalendarEvent[];

  /** Calendar height in pixels or 'auto' */
  height?: number | 'auto';

  /** Initial view mode */
  initialView?: 'timeGridWeek' | 'timeGridDay' | 'dayGridMonth';

  /** Locale for internationalization */
  locale?: string;

  /** Start time for the time grid */
  slotMinTime?: string;

  /** End time for the time grid */
  slotMaxTime?: string;

  /** Show current time indicator */
  nowIndicator?: boolean;

  /** Show all-day slot */
  allDaySlot?: boolean;

  /** Custom class name for the container */
  className?: string;

  /** Callback when view changes */
  onViewChange?: (view: string) => void;

  /** Callback when date range changes */
  onDatesSet?: (start: Date, end: Date) => void;

  /** Reference to access calendar API */
  calendarRef?: React.RefObject<unknown>;
}

// ============================================================================
// Hook Return Types
// ============================================================================

/**
 * Return type for useCalendarEvents hook
 */
export interface UseCalendarEventsResult {
  events: CalendarEvent[];
  isLoading: boolean;
  error: Error | null;
}

/**
 * Navigation controls return type
 */
export interface CalendarNavigation {
  goToNext: () => void;
  goToPrev: () => void;
  goToToday: () => void;
  goToDate: (date: Date) => void;
  getCurrentDate: () => Date | null;
}
