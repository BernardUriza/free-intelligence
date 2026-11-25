import { isEndAfterStart, isValidDate, isValidTime, timeToMinutes } from './time';
import type {
  AvailabilityError,
  DateOverride,
  DoctorAvailability,
  SchedulingRules,
  WeeklySlot,
} from './types';

const MIN_SLOT_DURATION = 5;

type Problem = Pick<AvailabilityError, 'type' | 'message'>;

function problemInHours(start: string, end: string): Problem | null {
  if (!isValidTime(start)) return { type: 'invalid_time', message: `Hora de inicio inválida: ${start}` };
  if (!isValidTime(end)) return { type: 'invalid_time', message: `Hora de fin inválida: ${end}` };
  if (!isEndAfterStart(start, end)) {
    return {
      type: 'end_before_start',
      message: `La hora de fin (${end}) debe ser posterior a la de inicio (${start})`,
    };
  }
  return null;
}

function problemInOverride(override: DateOverride): Problem | null {
  if (!isValidDate(override.date)) return { type: 'invalid_time', message: `Fecha inválida: ${override.date}` };
  if (override.fullDayClosed) return null;
  if (!override.start || !override.end) {
    return { type: 'invalid_time', message: 'Debe especificar hora de inicio y fin, o marcar como día libre' };
  }
  return problemInHours(override.start, override.end);
}

function problemsInRules(rules: SchedulingRules): AvailabilityError[] {
  const errors: AvailabilityError[] = [];
  const { breakStart, breakEnd, minSlotDuration, maxPatientsPerHour } = rules;

  if (breakStart && breakEnd) {
    const problem = problemInHours(breakStart, breakEnd);
    if (problem) errors.push({ ...problem, message: `Descanso: ${problem.message}`, severity: 'error' });
  } else if (breakStart || breakEnd) {
    errors.push({
      type: 'invalid_time',
      message: 'Debe especificar tanto inicio como fin del descanso',
      severity: 'warning',
    });
  }
  if (minSlotDuration !== undefined && minSlotDuration < MIN_SLOT_DURATION) {
    errors.push({
      type: 'invalid_time',
      message: `La duración mínima debe ser al menos ${MIN_SLOT_DURATION} minutos`,
      severity: 'error',
    });
  }
  if (maxPatientsPerHour !== undefined && maxPatientsPerHour < 1) {
    errors.push({ type: 'invalid_time', message: 'Debe permitir al menos 1 paciente por hora', severity: 'error' });
  }
  return errors;
}

export function slotsOverlap(a: WeeklySlot, b: WeeklySlot): boolean {
  return (
    a.day === b.day &&
    timeToMinutes(a.start) < timeToMinutes(b.end) &&
    timeToMinutes(b.start) < timeToMinutes(a.end)
  );
}

function slotsByDay(slots: WeeklySlot[]): Map<number, WeeklySlot[]> {
  const days = new Map<number, WeeklySlot[]>();
  for (const slot of slots) days.set(slot.day, [...(days.get(slot.day) ?? []), slot]);
  return days;
}

function problemsInDay(day: number, slots: WeeklySlot[]): AvailabilityError[] {
  const errors: AvailabilityError[] = [];
  slots.forEach((slot, slotIndex) => {
    const problem = problemInHours(slot.start, slot.end);
    if (problem) errors.push({ ...problem, day, slotIndex, severity: 'error' });
    slots.slice(0, slotIndex).forEach((earlier) => {
      if (!slotsOverlap(earlier, slot)) return;
      errors.push({
        type: 'overlap',
        day,
        slotIndex,
        message: `Solapamiento detectado: ${earlier.start}-${earlier.end} y ${slot.start}-${slot.end}`,
        severity: 'error',
      });
    });
  });
  return errors;
}

function problemsInOverrides(overrides: DateOverride[]): AvailabilityError[] {
  const errors: AvailabilityError[] = [];
  const seen = new Set<string>();
  for (const override of overrides) {
    const { date } = override;
    const problem = problemInOverride(override);
    if (problem) errors.push({ ...problem, date, severity: 'error' });
    if (seen.has(date)) {
      errors.push({ type: 'duplicate_date', date, message: `Fecha duplicada: ${date}`, severity: 'error' });
    }
    seen.add(date);
  }
  return errors;
}

export function validateAvailability(availability: DoctorAvailability): AvailabilityError[] {
  const weekly = [...slotsByDay(availability.weeklySchedule)].flatMap(([day, slots]) => problemsInDay(day, slots));
  return [...weekly, ...problemsInOverrides(availability.overrides), ...problemsInRules(availability.rules)];
}

export function hasBlockingErrors(errors: AvailabilityError[]): boolean {
  return errors.some((error) => error.severity === 'error');
}

export interface ScheduleGap {
  day: number;
  from: string;
  to: string;
}

export function findGaps(slots: WeeklySlot[]): ScheduleGap[] {
  return [...slotsByDay(slots)].flatMap(([day, daySlots]) => {
    const sorted = [...daySlots].sort((a, b) => timeToMinutes(a.start) - timeToMinutes(b.start));
    return sorted.slice(1).flatMap((next, i) => {
      const previous = sorted[i];
      return isEndAfterStart(previous.end, next.start) ? [{ day, from: previous.end, to: next.start }] : [];
    });
  });
}
