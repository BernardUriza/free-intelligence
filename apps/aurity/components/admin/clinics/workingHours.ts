import {
  AVAILABILITY_VERSION,
  DEFAULT_WORK_END,
  DEFAULT_WORK_START,
  WEEKDAYS,
  type DoctorAvailability,
} from '@free-intelligence/core/availability';

/** The flat shape `working-hours.resolver.ts` feeds to Bryntum. */
export interface WorkingHour {
  day?: number;
  start: string;
  end: string;
  date?: string;
  fullDayClosed?: boolean;
  reason?: string;
  legacyDerived?: boolean;
}

export function toWorkingHours({ weeklySchedule, overrides }: DoctorAvailability): WorkingHour[] {
  const weekly = weeklySchedule.map(({ day, start, end }) => ({ day, start, end }));
  const dated = overrides.flatMap(({ date, start, end, fullDayClosed, reason }): WorkingHour[] => {
    if (fullDayClosed) return [{ date, start: '00:00', end: '00:00', fullDayClosed: true, reason }];
    return start && end ? [{ date, start, end, reason }] : [];
  });
  return [...weekly, ...dated];
}

export function availabilityFromWorkTimes(
  workStart: string | null | undefined,
  workEnd: string | null | undefined,
): DoctorAvailability | null {
  if (!workStart && !workEnd) return null;
  const start = workStart || DEFAULT_WORK_START;
  const end = workEnd || DEFAULT_WORK_END;
  return {
    version: AVAILABILITY_VERSION,
    weeklySchedule: WEEKDAYS.map((day) => ({ day, start, end })),
    overrides: [],
    rules: {},
  };
}

function mostCommon(values: string[], fallback: string): string {
  const counts = new Map<string, number>();
  for (const value of values) counts.set(value, (counts.get(value) ?? 0) + 1);
  return [...counts].reduce((best, entry) => (entry[1] > best[1] ? entry : best), [fallback, 0] as [string, number])[0];
}

export function commonWorkTimes({ weeklySchedule }: DoctorAvailability): { start: string; end: string } {
  return {
    start: mostCommon(weeklySchedule.map((slot) => slot.start), DEFAULT_WORK_START),
    end: mostCommon(weeklySchedule.map((slot) => slot.end), DEFAULT_WORK_END),
  };
}
