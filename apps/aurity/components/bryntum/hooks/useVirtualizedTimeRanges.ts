/**
 * useVirtualizedTimeRanges - Windowed ResourceTimeRanges
 *
 * Generates non-working time ranges only for the visible viewport,
 * with a buffer zone. Updates dynamically as user navigates.
 *
 * Benefits:
 * - O(visible_days * doctors) instead of O(total_days * doctors)
 * - Smooth navigation with buffer zones
 * - Memory efficient for long date ranges
 *
 * Card: FI-BRYNTUM-PERF-001
 */

import { useCallback, useRef, useEffect } from 'react';
import { createLogger } from '@/lib/internal/logger';
import type { Doctor } from '@/components/bryntum/utils/appointment-transform.utils';
import { resolveWorkingDay } from '@/components/bryntum/utils/working-hours.resolver';
import { getClinicTimeZone, TemporalAPI } from '@/lib/temporal';

const log = createLogger('VirtualizedTimeRanges');

const Temporal = TemporalAPI;

// Buffer: extra days to generate beyond visible range
const BUFFER_DAYS = 1;

// Debounce delay for rapid navigation
const DEBOUNCE_MS = 150;

export interface TimeRangeItem {
  id: string;
  resourceId: string;
  startDate: Date;
  endDate: Date;
  name: string;
  cls: string;
  timeRangeColor: string;
}

interface VirtualizedTimeRangesOptions {
  doctors: Doctor[];
  enabled?: boolean;
}

/**
 * Hook that manages virtualized time ranges for Bryntum scheduler
 */
export function useVirtualizedTimeRanges({
  doctors,
  enabled = true,
}: VirtualizedTimeRangesOptions) {
  const lastRangeRef = useRef<{ start: string; end: string } | null>(null);
  const debounceRef = useRef<NodeJS.Timeout | null>(null);
  const schedulerRef = useRef<any>(null);

  /**
   * Generate time ranges for a specific date range
   */
  const generateRanges = useCallback(
    (startDate: Date, endDate: Date): TimeRangeItem[] => {
      if (!enabled || doctors.length === 0) return [];

      const ranges: TimeRangeItem[] = [];
      const timeZone = getClinicTimeZone();

      // Add buffer
      const bufferedStart = new Date(startDate);
      bufferedStart.setDate(bufferedStart.getDate() - BUFFER_DAYS);
      const bufferedEnd = new Date(endDate);
      bufferedEnd.setDate(bufferedEnd.getDate() + BUFFER_DAYS);

      const startZoned = Temporal.Instant.from(bufferedStart.toISOString()).toZonedDateTimeISO(timeZone);
      const endZoned = Temporal.Instant.from(bufferedEnd.toISOString()).toZonedDateTimeISO(timeZone);

      doctors.forEach((doctor) => {
        let cursor = startZoned;
        let spillover: any[] = [];

        while (Temporal.ZonedDateTime.compare(cursor, endZoned) <= 0) {
          const date = cursor.toPlainDate();
          const resolution = resolveWorkingDay(doctor, date, timeZone, spillover);

          resolution.nonWorking.forEach((window: any, index: number) => {
            ranges.push({
              id: `${doctor.doctor_id}-nw-${resolution.dateISO}-${index}`,
              resourceId: doctor.doctor_id,
              startDate: new Date(Number(window.start.epochMilliseconds)),
              endDate: new Date(Number(window.end.epochMilliseconds)),
              name: 'No disponible',
              cls: 'non-working-time',
              timeRangeColor: 'gray',
            });
          });

          spillover = resolution.spilloverNext;
          cursor = cursor.add({ days: 1 });
        }
      });

      return ranges;
    },
    [doctors, enabled]
  );

  /**
   * Update scheduler's resourceTimeRangeStore with new ranges
   */
  const updateSchedulerRanges = useCallback(
    (scheduler: any, startDate: Date, endDate: Date) => {
      if (!scheduler || !enabled) return;

      const rangeKey = `${startDate.toISOString()}-${endDate.toISOString()}`;
      const lastKey = lastRangeRef.current
        ? `${lastRangeRef.current.start}-${lastRangeRef.current.end}`
        : null;

      // Skip if same range
      if (rangeKey === lastKey) return;

      lastRangeRef.current = {
        start: startDate.toISOString(),
        end: endDate.toISOString(),
      };

      const ranges = generateRanges(startDate, endDate);

      // Try multiple ways to access the store (Bryntum API varies by version)
      const store =
        scheduler.resourceTimeRangeStore ||
        scheduler.features?.resourceTimeRanges?.store ||
        scheduler.timeRangeStore;

      if (store) {
        // Clear and replace using available methods
        if (typeof store.removeAll === 'function') {
          store.removeAll();
        } else if (typeof store.clear === 'function') {
          store.clear();
        }

        if (typeof store.add === 'function') {
          store.add(ranges);
        } else if (typeof store.loadData === 'function') {
          store.loadData(ranges);
        } else if (store.data !== undefined) {
          store.data = ranges;
        }

        // Force scheduler refresh
        scheduler.refresh?.();
      } else {
        log.warn('No resourceTimeRangeStore found on scheduler');
      }
    },
    [generateRanges, enabled]
  );

  /**
   * Debounced update for smooth navigation
   */
  const debouncedUpdate = useCallback(
    (scheduler: any, startDate: Date, endDate: Date) => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }

      debounceRef.current = setTimeout(() => {
        updateSchedulerRanges(scheduler, startDate, endDate);
      }, DEBOUNCE_MS);
    },
    [updateSchedulerRanges]
  );

  /**
   * Attach listeners to scheduler instance
   */
  const attachToScheduler = useCallback(
    (scheduler: any) => {
      if (!scheduler || !enabled) return;

      schedulerRef.current = scheduler;

      // Handler for date range changes
      const onDateRangeChange = ({ new: newRange }: any) => {
        if (newRange?.startDate && newRange?.endDate) {
          debouncedUpdate(scheduler, newRange.startDate, newRange.endDate);
        }
      };

      // Handler for visible date range changes (scroll/zoom)
      const onVisibleDateRangeChange = ({ startDate, endDate }: any) => {
        if (startDate && endDate) {
          debouncedUpdate(scheduler, startDate, endDate);
        }
      };

      // Handler for paint event (scheduler fully rendered)
      const onPaint = () => {
        if (scheduler.startDate && scheduler.endDate) {
          updateSchedulerRanges(scheduler, scheduler.startDate, scheduler.endDate);
        }
        // Remove paint listener after first trigger
        scheduler.off?.('paint', onPaint);
      };

      // Attach listeners
      scheduler.on?.('daterangechange', onDateRangeChange);
      scheduler.on?.('visibleDateRangeChange', onVisibleDateRangeChange);

      // Initial generation for current view
      if (scheduler.startDate && scheduler.endDate) {
        // Scheduler already has dates - generate immediately
        updateSchedulerRanges(scheduler, scheduler.startDate, scheduler.endDate);
      } else {
        // Wait for scheduler to be fully painted
        scheduler.on?.('paint', onPaint);
      }

      // Cleanup function
      return () => {
        scheduler.off?.('daterangechange', onDateRangeChange);
        scheduler.off?.('visibleDateRangeChange', onVisibleDateRangeChange);
        scheduler.off?.('paint', onPaint);
        if (debounceRef.current) {
          clearTimeout(debounceRef.current);
        }
      };
    },
    [debouncedUpdate, updateSchedulerRanges, enabled]
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, []);

  return {
    attachToScheduler,
    generateRanges,
    updateRanges: updateSchedulerRanges,
  };
}

export default useVirtualizedTimeRanges;
