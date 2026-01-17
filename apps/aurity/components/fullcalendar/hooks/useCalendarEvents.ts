/**
 * useCalendarEvents Hook
 *
 * Transform availability data to FullCalendar events with memoization
 */

'use client';

import { useMemo } from 'react';
import type { CalendarEvent, UseCalendarEventsResult } from '../types/calendar.types';
import { availabilityToEvents } from '../utils/event-transform.utils';

// ============================================================================
// Types
// ============================================================================

interface WeeklySlot {
  day: number;
  start: string;
  end: string;
  label?: string;
}

interface DateOverride {
  date: string;
  start?: string;
  end?: string;
  fullDayClosed: boolean;
  reason?: string;
}

interface AvailabilityData {
  weeklySchedule: WeeklySlot[];
  overrides: DateOverride[];
}

interface UseCalendarEventsOptions {
  /** Number of days to generate events for (default: 70) */
  daysToGenerate?: number;
  /** Start date for event generation */
  startDate?: Date;
  /** Label for available slots */
  availableLabel?: string;
  /** Label for override slots */
  overrideLabel?: string;
}

// ============================================================================
// Hook Implementation
// ============================================================================

/**
 * Hook to transform availability data into FullCalendar events
 *
 * @example
 * ```tsx
 * const { events } = useCalendarEvents(availability);
 *
 * <CalendarCore events={events} />
 * ```
 */
export function useCalendarEvents(
  availability: AvailabilityData | null | undefined,
  options: UseCalendarEventsOptions = {}
): UseCalendarEventsResult {
  const {
    daysToGenerate = 70,
    startDate,
    availableLabel,
    overrideLabel,
  } = options;

  const events = useMemo((): CalendarEvent[] => {
    if (!availability) {
      return [];
    }

    return availabilityToEvents(availability, {
      daysToGenerate,
      startDate,
      availableLabel,
      overrideLabel,
    });
  }, [
    availability,
    daysToGenerate,
    startDate?.getTime(),
    availableLabel,
    overrideLabel,
  ]);

  return {
    events,
    isLoading: false,
    error: null,
  };
}

// ============================================================================
// Navigation Hook
// ============================================================================

import { useCallback, useRef } from 'react';
import type { CalendarNavigation } from '../types/calendar.types';
import type FullCalendar from '@fullcalendar/react';

/**
 * Hook for calendar navigation controls
 *
 * @example
 * ```tsx
 * const calendarRef = useRef<FullCalendar>(null);
 * const { goToNext, goToPrev, goToToday } = useCalendarNavigation(calendarRef);
 * ```
 */
export function useCalendarNavigation(
  calendarRef: React.RefObject<FullCalendar | null>
): CalendarNavigation {
  const goToNext = useCallback(() => {
    calendarRef.current?.getApi()?.next();
  }, [calendarRef]);

  const goToPrev = useCallback(() => {
    calendarRef.current?.getApi()?.prev();
  }, [calendarRef]);

  const goToToday = useCallback(() => {
    calendarRef.current?.getApi()?.today();
  }, [calendarRef]);

  const goToDate = useCallback(
    (date: Date) => {
      calendarRef.current?.getApi()?.gotoDate(date);
    },
    [calendarRef]
  );

  const getCurrentDate = useCallback((): Date | null => {
    return calendarRef.current?.getApi()?.getDate() ?? null;
  }, [calendarRef]);

  return {
    goToNext,
    goToPrev,
    goToToday,
    goToDate,
    getCurrentDate,
  };
}

// ============================================================================
// Combined Hook
// ============================================================================

interface UseFullCalendarOptions extends UseCalendarEventsOptions {
  /** Whether to include navigation controls */
  withNavigation?: boolean;
}

interface UseFullCalendarResult extends UseCalendarEventsResult {
  /** Ref to the FullCalendar instance. Use as ref={calendarRef} on CalendarCore */
  calendarRef: React.RefObject<FullCalendar>;
  navigation: CalendarNavigation;
}

/**
 * All-in-one hook for FullCalendar with events and navigation
 *
 * @example
 * ```tsx
 * const { events, calendarRef, navigation } = useFullCalendar(availability);
 *
 * <CalendarCore ref={calendarRef} events={events} />
 * <button onClick={navigation.goToNext}>Next</button>
 * ```
 */
export function useFullCalendar(
  availability: AvailabilityData | null | undefined,
  options: UseFullCalendarOptions = {}
): UseFullCalendarResult {
  // Note: useRef<T>(null) returns RefObject<T | null> in React 19
  // We cast to RefObject<T> for forwardRef compatibility
  const calendarRef = useRef<FullCalendar>(null) as React.RefObject<FullCalendar>;
  const { events, isLoading, error } = useCalendarEvents(availability, options);
  const navigation = useCalendarNavigation(calendarRef);

  return {
    events,
    isLoading,
    error,
    calendarRef,
    navigation,
  };
}

export default useCalendarEvents;
