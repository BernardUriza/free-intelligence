import type { Doctor, WorkingHour } from '@/components/bryntum/utils/appointment-transform.utils';
import { TemporalAPI, getClinicTimeZone } from '@/lib/temporal';
import type { DoctorAvailability } from '@/components/admin/clinics/availability-designer/types';
import { toWorkingHours } from '@/components/admin/clinics/availability-designer/utils/transform';

const Temporal = TemporalAPI;

type ZonedDateTime = {
  epochNanoseconds: number;
  epochMilliseconds: number;
  add(duration: { days?: number }): ZonedDateTime;
};

type PlainDate = {
  year: number;
  month: number;
  day: number;
  dayOfWeek: number;
  toString(): string;
};

type PlainTime = {
  hour: number;
  minute: number;
  second: number;
  millisecond: number;
  microsecond: number;
  nanosecond: number;
};

export type WorkingHourOverride = WorkingHour & {
  fullDayClosed?: boolean;
  reason?: string;
  legacyDerived?: boolean;
};

export type ResolvedWindow = {
  start: ZonedDateTime;
  end: ZonedDateTime;
  source: 'override' | 'weekly' | 'legacy' | 'spillover';
  legacyDerived?: boolean;
};

export type DayResolution = {
  dateISO: string;
  windows: ResolvedWindow[];
  nonWorking: ResolvedWindow[];
  spilloverNext: ResolvedWindow[];
  mergesApplied: boolean;
  fullDayOff: boolean;
  totalMinutes: number;
};

const MINUTES_PER_DAY = 24 * 60;

function dayBounds(date: PlainDate, timeZone: string) {
  const dayStart = Temporal.ZonedDateTime.from({
    timeZone,
    year: date.year,
    month: date.month,
    day: date.day,
    hour: 0,
    minute: 0,
    second: 0,
    millisecond: 0,
    microsecond: 0,
    nanosecond: 0,
  });

  const dayEnd = dayStart.add({ days: 1 });
  return { dayStart, dayEnd };
}

function parsePlainTime(value: string): PlainTime {
  try {
    return Temporal.PlainTime.from(value);
  } catch {
    throw new Error(`Invalid time format: "${value}" (expected HH:mm)`);
  }
}

function slotToWindows(
  slot: WorkingHourOverride,
  date: PlainDate,
  timeZone: string,
  bounds: { dayStart: ZonedDateTime; dayEnd: ZonedDateTime }
): { currentDay: ResolvedWindow[]; spillover: ResolvedWindow[] } {
  if (slot.start === '24:00' || slot.start === '24:00:00') {
    throw new Error('Start time cannot be 24:00');
  }

  const startPlain = parsePlainTime(slot.start);
  const endIsEndOfDay = slot.end === '24:00' || slot.end === '24:00:00';
  const endPlain = endIsEndOfDay ? null : parsePlainTime(slot.end);

  const start = Temporal.ZonedDateTime.from({
    timeZone,
    year: date.year,
    month: date.month,
    day: date.day,
    hour: startPlain.hour,
    minute: startPlain.minute,
    second: startPlain.second,
    millisecond: startPlain.millisecond,
    microsecond: startPlain.microsecond,
    nanosecond: startPlain.nanosecond,
  });

  let end = endIsEndOfDay
    ? bounds.dayEnd
    : Temporal.ZonedDateTime.from({
        timeZone,
        year: date.year,
        month: date.month,
        day: date.day,
        hour: endPlain!.hour,
        minute: endPlain!.minute,
        second: endPlain!.second,
        millisecond: endPlain!.millisecond,
        microsecond: endPlain!.microsecond,
        nanosecond: endPlain!.nanosecond,
      });

  if (Temporal.ZonedDateTime.compare(end, start) <= 0) {
    end = end.add({ days: 1 });
  }

  const { dayStart, dayEnd } = bounds;
  const currentDay: ResolvedWindow[] = [];
  const spillover: ResolvedWindow[] = [];

  const currentStart = Temporal.ZonedDateTime.compare(start, dayStart) < 0 ? dayStart : start;
  const currentEnd = Temporal.ZonedDateTime.compare(end, dayEnd) > 0 ? dayEnd : end;

  if (Temporal.ZonedDateTime.compare(currentEnd, currentStart) <= 0) {
    throw new Error('Working window must have positive duration');
  }

  currentDay.push({
    start: currentStart,
    end: currentEnd,
    source: slot.date ? 'override' : slot.day !== undefined ? 'weekly' : 'legacy',
    legacyDerived: slot.legacyDerived,
  });

  if (Temporal.ZonedDateTime.compare(end, dayEnd) > 0) {
    spillover.push({
      start: dayEnd,
      end,
      source: 'spillover',
      legacyDerived: slot.legacyDerived,
    });
  }

  return { currentDay, spillover };
}

function mergeWindows(windows: ResolvedWindow[]): { merged: ResolvedWindow[]; mergesApplied: boolean; totalMinutes: number } {
  if (!windows.length) {
    return { merged: [], mergesApplied: false, totalMinutes: 0 };
  }

  const sorted = [...windows].sort((a, b) => Temporal.ZonedDateTime.compare(a.start, b.start));
  const merged: ResolvedWindow[] = [];

  let current = sorted[0];

  for (let i = 1; i < sorted.length; i++) {
    const candidate = sorted[i];
    if (Temporal.ZonedDateTime.compare(candidate.start, current.end) <= 0) {
      const laterEnd = Temporal.ZonedDateTime.compare(candidate.end, current.end) > 0 ? candidate.end : current.end;
      current = {
        ...current,
        end: laterEnd,
        legacyDerived: current.legacyDerived && candidate.legacyDerived ? true : current.legacyDerived || candidate.legacyDerived,
      };
    } else {
      merged.push(current);
      current = candidate;
    }
  }

  merged.push(current);

  const totalMinutes = merged.reduce((acc, window) => {
    const durationMs = window.end.epochMilliseconds - window.start.epochMilliseconds;
    return acc + Math.floor(durationMs / 1000 / 60);
  }, 0);

  if (totalMinutes > MINUTES_PER_DAY) {
    throw new Error('Working windows exceed 24 hours for a single day');
  }

  return { merged, mergesApplied: merged.length !== windows.length, totalMinutes };
}

function buildNonWorkingRanges(
  dayStart: ZonedDateTime,
  dayEnd: ZonedDateTime,
  working: ResolvedWindow[]
): ResolvedWindow[] {
  if (!working.length) {
    return [
      {
        start: dayStart,
        end: dayEnd,
        source: 'override',
      },
    ];
  }

  const ranges: ResolvedWindow[] = [];
  let cursor = dayStart;

  working.forEach((window) => {
    if (Temporal.ZonedDateTime.compare(window.start, cursor) > 0) {
      ranges.push({ start: cursor, end: window.start, source: 'override' });
    }
    cursor = window.end;
  });

  if (Temporal.ZonedDateTime.compare(cursor, dayEnd) < 0) {
    ranges.push({ start: cursor, end: dayEnd, source: 'override' });
  }

  return ranges;
}

/**
 * Normalize working_hours to WorkingHourOverride[] format
 * Handles both new DoctorAvailability object format and legacy array format
 */
function normalizeWorkingHours(workingHours: unknown): WorkingHourOverride[] {
  if (!workingHours) return [];

  // New format: DoctorAvailability object with version, weeklySchedule, etc.
  if (typeof workingHours === 'object' && 'version' in (workingHours as object)) {
    return toWorkingHours(workingHours as DoctorAvailability) as WorkingHourOverride[];
  }

  // Legacy format: already an array
  if (Array.isArray(workingHours)) {
    return workingHours as WorkingHourOverride[];
  }

  return [];
}

function pickSlotsForDate(
  doctor: Doctor,
  date: PlainDate
): { slots: WorkingHourOverride[]; fullDayClosed: boolean; dateISO: string } {
  const dateISO = date.toString();
  const dailySlots = normalizeWorkingHours(doctor.working_hours);
  const override = dailySlots.filter((slot) => slot.date === dateISO);
  if (override.length) {
    const closed = override.some((slot) => slot.fullDayClosed || !slot.start || !slot.end);
    if (closed) {
      return { slots: [], fullDayClosed: true, dateISO };
    }
    return { slots: override, fullDayClosed: false, dateISO };
  }

  const dayOfWeek = date.dayOfWeek % 7; // Temporal: Monday=1 .. Sunday=7 -> map Sunday to 0
  const weekly = dailySlots.filter((slot) => slot.day === dayOfWeek);
  if (weekly.length) {
    return { slots: weekly, fullDayClosed: false, dateISO };
  }

  if (doctor.work_start_time && doctor.work_end_time) {
    return {
      slots: [
        {
          day: dayOfWeek,
          start: doctor.work_start_time,
          end: doctor.work_end_time,
          legacyDerived: true,
        },
      ],
      fullDayClosed: false,
      dateISO,
    };
  }

  return { slots: [], fullDayClosed: true, dateISO };
}

export function resolveWorkingDay(
  doctor: Doctor,
  targetDate: PlainDate,
  timeZone = getClinicTimeZone(),
  spilloverFromPrev: ResolvedWindow[] = []
): DayResolution {
  const { dayStart, dayEnd } = dayBounds(targetDate, timeZone);
  const { slots, fullDayClosed, dateISO } = pickSlotsForDate(doctor, targetDate);
  const windows: ResolvedWindow[] = [];
  const spilloverNext: ResolvedWindow[] = [];

  if (fullDayClosed) {
    const nonWorking = buildNonWorkingRanges(dayStart, dayEnd, []);
    return {
      dateISO,
      windows: [],
      nonWorking,
      spilloverNext: [],
      mergesApplied: false,
      fullDayOff: true,
      totalMinutes: 0,
    };
  }

  slots.forEach((slot) => {
    const { currentDay, spillover } = slotToWindows(slot, targetDate, timeZone, { dayStart, dayEnd });
    windows.push(...currentDay);
    spilloverNext.push(...spillover);
  });

  if (spilloverFromPrev.length) {
    windows.push(
      ...spilloverFromPrev.map(
        (w): ResolvedWindow => ({
          ...w,
          source: 'spillover',
        })
      )
    );
  }

  const { merged, mergesApplied, totalMinutes } = mergeWindows(windows);
  const nonWorking = buildNonWorkingRanges(dayStart, dayEnd, merged);

  return {
    dateISO,
    windows: merged,
    nonWorking,
    spilloverNext,
    mergesApplied,
    fullDayOff: false,
    totalMinutes,
  };
}

export function zonedToDate(zdt: ZonedDateTime): Date {
  return new Date(zdt.epochMilliseconds);
}

/**
 * Check if a given date/time falls within a doctor's working hours
 *
 * @param doctor - Doctor with working_hours configuration
 * @param date - Date to check
 * @returns true if the date is within working hours, false otherwise
 */
export function isDateInWorkingHours(doctor: Doctor, date: Date): boolean {
  const timeZone = getClinicTimeZone();

  // Convert Date to PlainDate for resolveWorkingDay
  const instant = Temporal.Instant.from(date.toISOString());
  const zonedDate = instant.toZonedDateTimeISO(timeZone);
  const plainDate = zonedDate.toPlainDate();

  // Get the working windows for this day
  const resolution = resolveWorkingDay(doctor, plainDate, timeZone);

  // If it's a full day off, nothing is allowed
  if (resolution.fullDayOff) {
    return false;
  }

  // Check if the date falls within any working window
  const dateMs = date.getTime();

  for (const window of resolution.windows) {
    const startMs = window.start.epochMilliseconds;
    const endMs = window.end.epochMilliseconds;

    if (dateMs >= startMs && dateMs < endMs) {
      return true;
    }
  }

  return false;
}
