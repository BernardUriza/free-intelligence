/**
 * Event Transform Utilities
 *
 * Transform various data sources to FullCalendar events
 */

import type { CalendarEvent, CalendarEventCategory } from '../types/calendar.types';
import { EVENT_STYLES } from '../config/calendar-presets.config';

// ============================================================================
// Types (Generic to support various input formats)
// ============================================================================

/**
 * Generic weekly slot input format
 */
interface WeeklySlotInput {
  day: number;        // 0-6
  start: string;      // HH:mm
  end: string;        // HH:mm
  label?: string;
}

/**
 * Generic date override input format
 */
interface DateOverrideInput {
  date: string;       // YYYY-MM-DD
  start?: string;     // HH:mm
  end?: string;       // HH:mm
  fullDayClosed: boolean;
  reason?: string;
}

/**
 * Generic availability input format
 */
interface AvailabilityInput {
  weeklySchedule: WeeklySlotInput[];
  overrides: DateOverrideInput[];
}

// ============================================================================
// Core Transformation Functions
// ============================================================================

/**
 * Apply event styling based on category
 */
export function applyEventStyle(
  event: CalendarEvent,
  category: CalendarEventCategory
): CalendarEvent {
  const style = EVENT_STYLES[category];
  return {
    ...event,
    backgroundColor: style.backgroundColor,
    borderColor: style.borderColor,
    textColor: style.textColor,
    extendedProps: {
      ...event.extendedProps,
      category,
    },
  };
}

/**
 * Generate date range for event generation
 */
export function generateDateRange(
  startDate: Date,
  daysCount: number
): Date[] {
  const dates: Date[] = [];
  for (let i = 0; i < daysCount; i++) {
    const date = new Date(startDate);
    date.setDate(startDate.getDate() + i);
    dates.push(date);
  }
  return dates;
}

/**
 * Format date as ISO date string (YYYY-MM-DD)
 */
export function formatDateISO(date: Date): string {
  return date.toISOString().split('T')[0];
}

// ============================================================================
// Availability to Events Transformation
// ============================================================================

/**
 * Transform availability data to FullCalendar events
 *
 * @param availability - The availability data (weekly + overrides)
 * @param options - Configuration options
 * @returns Array of CalendarEvent objects
 */
export function availabilityToEvents(
  availability: AvailabilityInput,
  options: {
    /** Number of days to generate events for */
    daysToGenerate?: number;
    /** Start date (defaults to previous week) */
    startDate?: Date;
    /** Default label for available slots */
    availableLabel?: string;
    /** Default label for override slots */
    overrideLabel?: string;
  } = {}
): CalendarEvent[] {
  const {
    daysToGenerate = 70,
    startDate: customStartDate,
    availableLabel = 'Disponible',
    overrideLabel = 'Horario especial',
  } = options;

  const result: CalendarEvent[] = [];
  const today = new Date();

  // Default: start from previous week's Sunday
  const startDate = customStartDate ?? (() => {
    const d = new Date(today);
    d.setDate(today.getDate() - today.getDay() - 7);
    return d;
  })();

  // Generate events for each day
  for (let dayOffset = 0; dayOffset < daysToGenerate; dayOffset++) {
    const currentDate = new Date(startDate);
    currentDate.setDate(startDate.getDate() + dayOffset);
    const dateStr = formatDateISO(currentDate);
    const dayOfWeek = currentDate.getDay();

    // Check for date override first
    const override = availability.overrides.find((o) => o.date === dateStr);

    if (override) {
      if (override.fullDayClosed) {
        // Add a "closed" background event
        result.push(
          applyEventStyle(
            {
              id: `closed-${dateStr}`,
              start: dateStr,
              allDay: true,
              display: 'background',
              classNames: ['fc-closed-day'],
              extendedProps: {
                reason: override.reason,
              },
            },
            'closed'
          )
        );
      } else if (override.start && override.end) {
        // Add override slot
        result.push(
          applyEventStyle(
            {
              id: `override-${dateStr}`,
              title: override.reason || overrideLabel,
              start: `${dateStr}T${override.start}:00`,
              end: `${dateStr}T${override.end}:00`,
              classNames: ['fc-override-event'],
              extendedProps: {
                reason: override.reason,
              },
            },
            'override'
          )
        );
      }
    } else {
      // Get weekly slots for this day
      const slots = availability.weeklySchedule.filter(
        (slot) => slot.day === dayOfWeek
      );

      slots.forEach((slot, index) => {
        result.push(
          applyEventStyle(
            {
              id: `slot-${dateStr}-${index}`,
              title: slot.label || availableLabel,
              start: `${dateStr}T${slot.start}:00`,
              end: `${dateStr}T${slot.end}:00`,
              classNames: ['fc-availability-event'],
            },
            'available'
          )
        );
      });

      // If no slots for this day, mark as day off (background)
      if (slots.length === 0) {
        result.push(
          applyEventStyle(
            {
              id: `off-${dateStr}`,
              start: dateStr,
              allDay: true,
              display: 'background',
              classNames: ['fc-day-off'],
            },
            'dayOff'
          )
        );
      }
    }
  }

  return result;
}

// ============================================================================
// Simple Event Creators
// ============================================================================

/**
 * Create a single available slot event
 */
export function createAvailableEvent(
  dateStr: string,
  start: string,
  end: string,
  label?: string
): CalendarEvent {
  return applyEventStyle(
    {
      id: `available-${dateStr}-${start}`,
      title: label || 'Disponible',
      start: `${dateStr}T${start}:00`,
      end: `${dateStr}T${end}:00`,
      classNames: ['fc-availability-event'],
    },
    'available'
  );
}

/**
 * Create a closed day background event
 */
export function createClosedDayEvent(
  dateStr: string,
  reason?: string
): CalendarEvent {
  return applyEventStyle(
    {
      id: `closed-${dateStr}`,
      start: dateStr,
      allDay: true,
      display: 'background',
      classNames: ['fc-closed-day'],
      extendedProps: { reason },
    },
    'closed'
  );
}

/**
 * Create an override event
 */
export function createOverrideEvent(
  dateStr: string,
  start: string,
  end: string,
  reason?: string
): CalendarEvent {
  return applyEventStyle(
    {
      id: `override-${dateStr}`,
      title: reason || 'Horario especial',
      start: `${dateStr}T${start}:00`,
      end: `${dateStr}T${end}:00`,
      classNames: ['fc-override-event'],
      extendedProps: { reason },
    },
    'override'
  );
}

// ============================================================================
// Utilities
// ============================================================================

/**
 * Filter events by date range
 */
export function filterEventsByDateRange(
  events: CalendarEvent[],
  start: Date,
  end: Date
): CalendarEvent[] {
  const startTime = start.getTime();
  const endTime = end.getTime();

  return events.filter((event) => {
    if (!event.start) return false;
    const eventStart =
      typeof event.start === 'string'
        ? new Date(event.start).getTime()
        : event.start.getTime();
    return eventStart >= startTime && eventStart < endTime;
  });
}

/**
 * Count events by category
 */
export function countEventsByCategory(
  events: CalendarEvent[]
): Record<CalendarEventCategory, number> {
  const counts: Record<CalendarEventCategory, number> = {
    available: 0,
    override: 0,
    closed: 0,
    dayOff: 0,
  };

  events.forEach((event) => {
    const category = event.extendedProps?.category as CalendarEventCategory;
    if (category && category in counts) {
      counts[category]++;
    }
  });

  return counts;
}
