'use client';

import { useMemo, useRef, type RefObject } from 'react';
import type { FiCalendarHandle } from './FiCalendar';

export interface CalendarNavigation {
  goToNext: () => void;
  goToPrev: () => void;
  goToToday: () => void;
  goToDate: (date: Date) => void;
}

export interface UseCalendarNavigationResult {
  calendarRef: RefObject<FiCalendarHandle | null>;
  navigation: CalendarNavigation;
}

export function useCalendarNavigation(): UseCalendarNavigationResult {
  const calendarRef = useRef<FiCalendarHandle | null>(null);
  const navigation = useMemo<CalendarNavigation>(() => {
    const api = () => calendarRef.current?.getApi();
    return {
      goToNext: () => api()?.next(),
      goToPrev: () => api()?.prev(),
      goToToday: () => api()?.today(),
      goToDate: (date) => api()?.gotoDate(date),
    };
  }, []);
  return { calendarRef, navigation };
}
