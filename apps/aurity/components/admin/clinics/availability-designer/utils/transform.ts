/**
 * Availability Designer - Transform Utilities
 *
 * Convert between DoctorAvailability and WorkingHour[] formats
 * for compatibility with working-hours.resolver.ts
 */

import type {
  DoctorAvailability,
  WeeklySlot,
  DateOverride,
  WorkingHour,
  DaySchedule,
} from '../types';
import { DAYS_OF_WEEK, DEFAULT_WORK_START, DEFAULT_WORK_END, EMPTY_AVAILABILITY } from '../constants';

// =============================================================================
// TO WORKING HOURS (for resolver)
// =============================================================================

/**
 * Transform DoctorAvailability to WorkingHour[] format
 * This is consumed by working-hours.resolver.ts and Bryntum
 */
export function toWorkingHours(availability: DoctorAvailability): WorkingHour[] {
  const hours: WorkingHour[] = [];

  // Convert weekly schedule
  for (const slot of availability.weeklySchedule) {
    hours.push({
      day: slot.day,
      start: slot.start,
      end: slot.end,
    });
  }

  // Convert date overrides
  for (const override of availability.overrides) {
    if (override.fullDayClosed) {
      hours.push({
        date: override.date,
        start: '00:00',
        end: '00:00',
        fullDayClosed: true,
        reason: override.reason,
      });
    } else if (override.start && override.end) {
      hours.push({
        date: override.date,
        start: override.start,
        end: override.end,
        reason: override.reason,
      });
    }
  }

  return hours;
}

// =============================================================================
// FROM LEGACY (work_start_time/work_end_time)
// =============================================================================

/**
 * Create DoctorAvailability from legacy work_start_time/work_end_time
 * Applies the same hours to all weekdays (Mon-Fri)
 */
export function fromLegacy(
  workStartTime: string | null,
  workEndTime: string | null
): DoctorAvailability {
  const start = workStartTime || DEFAULT_WORK_START;
  const end = workEndTime || DEFAULT_WORK_END;

  // Default: Mon-Fri with same hours
  const weeklySchedule: WeeklySlot[] = [1, 2, 3, 4, 5].map((day) => ({
    day,
    start,
    end,
  }));

  return {
    version: 1,
    weeklySchedule,
    overrides: [],
    rules: {},
  };
}

/**
 * Extract legacy work_start_time/work_end_time from availability
 * Returns the most common start/end times for backward compatibility
 */
export function toLegacy(availability: DoctorAvailability): {
  work_start_time: string | null;
  work_end_time: string | null;
} {
  if (availability.weeklySchedule.length === 0) {
    return { work_start_time: null, work_end_time: null };
  }

  // Find most common start and end times
  const startCounts = new Map<string, number>();
  const endCounts = new Map<string, number>();

  for (const slot of availability.weeklySchedule) {
    startCounts.set(slot.start, (startCounts.get(slot.start) || 0) + 1);
    endCounts.set(slot.end, (endCounts.get(slot.end) || 0) + 1);
  }

  let mostCommonStart = DEFAULT_WORK_START;
  let mostCommonEnd = DEFAULT_WORK_END;
  let maxStartCount = 0;
  let maxEndCount = 0;

  for (const [time, count] of startCounts) {
    if (count > maxStartCount) {
      maxStartCount = count;
      mostCommonStart = time;
    }
  }

  for (const [time, count] of endCounts) {
    if (count > maxEndCount) {
      maxEndCount = count;
      mostCommonEnd = time;
    }
  }

  return {
    work_start_time: mostCommonStart,
    work_end_time: mostCommonEnd,
  };
}

// =============================================================================
// FROM WORKING HOURS (reverse transform)
// =============================================================================

/**
 * Convert WorkingHour[] back to DoctorAvailability
 * Used when loading existing data from API
 */
export function fromWorkingHours(hours: WorkingHour[]): DoctorAvailability {
  const weeklySchedule: WeeklySlot[] = [];
  const overrides: DateOverride[] = [];

  for (const hour of hours) {
    if (hour.date) {
      // This is a date override
      overrides.push({
        date: hour.date,
        start: hour.fullDayClosed ? undefined : hour.start,
        end: hour.fullDayClosed ? undefined : hour.end,
        fullDayClosed: hour.fullDayClosed || false,
        reason: hour.reason,
      });
    } else if (hour.day !== undefined) {
      // This is a weekly slot
      weeklySchedule.push({
        day: hour.day,
        start: hour.start,
        end: hour.end,
      });
    }
  }

  return {
    version: 1,
    weeklySchedule,
    overrides,
    rules: {},
  };
}

// =============================================================================
// FORM STATE TRANSFORMS
// =============================================================================

/**
 * Convert DoctorAvailability to form state (grouped by day)
 */
export function toFormState(
  availability: DoctorAvailability
): Record<number, DaySchedule> {
  const state: Record<number, DaySchedule> = {};

  // Initialize all days as off
  for (const day of DAYS_OF_WEEK) {
    state[day.value] = {
      isWorking: false,
      slots: [],
    };
  }

  // Populate from weekly schedule
  for (const slot of availability.weeklySchedule) {
    if (!state[slot.day]) {
      state[slot.day] = { isWorking: true, slots: [] };
    }
    state[slot.day].isWorking = true;
    state[slot.day].slots.push(slot);
  }

  // Sort slots by start time within each day
  for (const day of Object.keys(state)) {
    state[Number(day)].slots.sort((a, b) => {
      const aMin = timeToMinutes(a.start);
      const bMin = timeToMinutes(b.start);
      return aMin - bMin;
    });
  }

  return state;
}

/**
 * Convert form state back to DoctorAvailability
 */
export function fromFormState(
  formState: Record<number, DaySchedule>,
  overrides: DateOverride[],
  rules: DoctorAvailability['rules']
): DoctorAvailability {
  const weeklySchedule: WeeklySlot[] = [];

  for (const [day, schedule] of Object.entries(formState)) {
    if (schedule.isWorking) {
      for (const slot of schedule.slots) {
        weeklySchedule.push({
          ...slot,
          day: Number(day),
        });
      }
    }
  }

  return {
    version: 1,
    weeklySchedule,
    overrides,
    rules,
  };
}

// =============================================================================
// HELPERS
// =============================================================================

function timeToMinutes(time: string): number {
  const [hours, minutes] = time.split(':').map(Number);
  return hours * 60 + minutes;
}

/**
 * Check if availability is empty (no working hours defined)
 */
export function isEmptyAvailability(availability: DoctorAvailability): boolean {
  return availability.weeklySchedule.length === 0;
}

/**
 * Merge two availabilities (used for templates)
 */
export function mergeAvailability(
  base: DoctorAvailability,
  override: Partial<DoctorAvailability>
): DoctorAvailability {
  return {
    version: 1,
    weeklySchedule: override.weeklySchedule ?? base.weeklySchedule,
    overrides: override.overrides ?? base.overrides,
    rules: { ...base.rules, ...override.rules },
  };
}

/**
 * Calculate total working hours per week
 */
export function calculateWeeklyHours(availability: DoctorAvailability): number {
  let totalMinutes = 0;

  for (const slot of availability.weeklySchedule) {
    const start = timeToMinutes(slot.start);
    const end = timeToMinutes(slot.end);
    totalMinutes += end - start;
  }

  return totalMinutes / 60;
}

/**
 * Get working days as array of day numbers
 */
export function getWorkingDays(availability: DoctorAvailability): number[] {
  const days = new Set<number>();
  for (const slot of availability.weeklySchedule) {
    days.add(slot.day);
  }
  return Array.from(days).sort();
}
