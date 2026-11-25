import { AVAILABILITY_VERSION, DAYS_OF_WEEK, DEFAULT_WORK_END, DEFAULT_WORK_START } from './defaults';
import { MINUTES_PER_DAY, minutesToTime, timeToMinutes } from './time';
import type { DateOverride, DoctorAvailability, SchedulingRules, WeeklySlot, WeekSchedule } from './types';

const GAP_BEFORE_NEW_SLOT = 60;
const NEW_SLOT_LENGTH = 4 * 60;
const SHORTEST_NEW_SLOT = 30;
const LAST_MINUTE = MINUTES_PER_DAY - 1;

export function groupByDay(weeklySchedule: WeeklySlot[]): WeekSchedule {
  return Object.fromEntries(
    DAYS_OF_WEEK.map(({ value }) => {
      const slots = weeklySchedule
        .filter((slot) => slot.day === value)
        .sort((a, b) => timeToMinutes(a.start) - timeToMinutes(b.start));
      return [value, { isWorking: slots.length > 0, slots }];
    }),
  );
}

export function availabilityFromWeek(
  week: WeekSchedule,
  overrides: DateOverride[],
  rules: SchedulingRules,
): DoctorAvailability {
  const weeklySchedule = Object.values(week).flatMap((day) => (day.isWorking ? day.slots : []));
  return { version: AVAILABILITY_VERSION, weeklySchedule, overrides, rules };
}

/** `null` when the day has no room left before midnight. */
export function suggestNextSlot(day: number, existing: WeeklySlot[]): WeeklySlot | null {
  const last = existing[existing.length - 1];
  if (!last) return { day, start: DEFAULT_WORK_START, end: DEFAULT_WORK_END };
  const start = timeToMinutes(last.end) + GAP_BEFORE_NEW_SLOT;
  const end = Math.min(start + NEW_SLOT_LENGTH, LAST_MINUTE);
  if (!(end - start >= SHORTEST_NEW_SLOT)) return null;
  return { day, start: minutesToTime(start), end: minutesToTime(end) };
}

export function weeklyHours(availability: DoctorAvailability): number {
  const minutes = availability.weeklySchedule.reduce(
    (total, slot) => total + timeToMinutes(slot.end) - timeToMinutes(slot.start),
    0,
  );
  return minutes / 60;
}

export function workingDays(availability: DoctorAvailability): number[] {
  return [...new Set(availability.weeklySchedule.map((slot) => slot.day))].sort();
}
