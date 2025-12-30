/**
 * Availability Designer - Validation Utilities
 *
 * Overlap detection, time validation, and constraint checking
 */

import type {
  WeeklySlot,
  DateOverride,
  SchedulingRules,
  DoctorAvailability,
  ValidationError,
} from '../types';

// =============================================================================
// TIME HELPERS
// =============================================================================

/**
 * Parse HH:mm string to minutes since midnight
 */
export function timeToMinutes(time: string): number {
  const [hours, minutes] = time.split(':').map(Number);
  return hours * 60 + minutes;
}

/**
 * Convert minutes since midnight to HH:mm string
 */
export function minutesToTime(minutes: number): string {
  const h = Math.floor(minutes / 60) % 24;
  const m = minutes % 60;
  return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`;
}

/**
 * Validate HH:mm format
 */
export function isValidTimeFormat(time: string): boolean {
  return /^([0-1][0-9]|2[0-3]):[0-5][0-9]$/.test(time);
}

/**
 * Check if end time is after start time
 */
export function isEndAfterStart(start: string, end: string): boolean {
  return timeToMinutes(end) > timeToMinutes(start);
}

/**
 * Calculate duration in minutes between start and end
 */
export function calculateDuration(start: string, end: string): number {
  const startMin = timeToMinutes(start);
  const endMin = timeToMinutes(end);
  // Handle overnight slots (end < start means next day)
  if (endMin <= startMin) {
    return (24 * 60 - startMin) + endMin;
  }
  return endMin - startMin;
}

// =============================================================================
// SLOT VALIDATION
// =============================================================================

/**
 * Validate a single time slot
 */
export function validateSlot(slot: WeeklySlot): ValidationError | null {
  if (!isValidTimeFormat(slot.start)) {
    return {
      type: 'invalid_time',
      day: slot.day,
      message: `Hora de inicio inválida: ${slot.start}`,
      severity: 'error',
    };
  }

  if (!isValidTimeFormat(slot.end)) {
    return {
      type: 'invalid_time',
      day: slot.day,
      message: `Hora de fin inválida: ${slot.end}`,
      severity: 'error',
    };
  }

  if (!isEndAfterStart(slot.start, slot.end)) {
    return {
      type: 'end_before_start',
      day: slot.day,
      message: `La hora de fin (${slot.end}) debe ser posterior a la de inicio (${slot.start})`,
      severity: 'error',
    };
  }

  return null;
}

/**
 * Check if two slots overlap
 */
export function slotsOverlap(a: WeeklySlot, b: WeeklySlot): boolean {
  if (a.day !== b.day) return false;

  const aStart = timeToMinutes(a.start);
  const aEnd = timeToMinutes(a.end);
  const bStart = timeToMinutes(b.start);
  const bEnd = timeToMinutes(b.end);

  // Overlap exists if one slot starts before the other ends
  return aStart < bEnd && bStart < aEnd;
}

/**
 * Detect overlaps among slots for the same day
 */
export function detectOverlaps(slots: WeeklySlot[]): ValidationError[] {
  const errors: ValidationError[] = [];
  const slotsByDay = new Map<number, WeeklySlot[]>();

  // Group slots by day
  for (const slot of slots) {
    const daySlots = slotsByDay.get(slot.day) || [];
    daySlots.push(slot);
    slotsByDay.set(slot.day, daySlots);
  }

  // Check each day for overlaps
  for (const [day, daySlots] of slotsByDay) {
    for (let i = 0; i < daySlots.length; i++) {
      for (let j = i + 1; j < daySlots.length; j++) {
        if (slotsOverlap(daySlots[i], daySlots[j])) {
          errors.push({
            type: 'overlap',
            day,
            message: `Solapamiento detectado: ${daySlots[i].start}-${daySlots[i].end} y ${daySlots[j].start}-${daySlots[j].end}`,
            severity: 'error',
          });
        }
      }
    }
  }

  return errors;
}

/**
 * Detect gaps between slots (informational, not an error)
 */
export function detectGaps(slots: WeeklySlot[]): Array<{ day: number; gap: string }> {
  const gaps: Array<{ day: number; gap: string }> = [];
  const slotsByDay = new Map<number, WeeklySlot[]>();

  // Group and sort slots by day
  for (const slot of slots) {
    const daySlots = slotsByDay.get(slot.day) || [];
    daySlots.push(slot);
    slotsByDay.set(slot.day, daySlots);
  }

  // Check each day for gaps
  for (const [day, daySlots] of slotsByDay) {
    if (daySlots.length < 2) continue;

    // Sort by start time
    const sorted = [...daySlots].sort(
      (a, b) => timeToMinutes(a.start) - timeToMinutes(b.start)
    );

    for (let i = 0; i < sorted.length - 1; i++) {
      const currentEnd = timeToMinutes(sorted[i].end);
      const nextStart = timeToMinutes(sorted[i + 1].start);

      if (nextStart > currentEnd) {
        gaps.push({
          day,
          gap: `${sorted[i].end} - ${sorted[i + 1].start}`,
        });
      }
    }
  }

  return gaps;
}

// =============================================================================
// OVERRIDE VALIDATION
// =============================================================================

/**
 * Validate date format (YYYY-MM-DD)
 */
export function isValidDateFormat(date: string): boolean {
  return /^\d{4}-\d{2}-\d{2}$/.test(date) && !isNaN(Date.parse(date));
}

/**
 * Validate a date override
 */
export function validateOverride(override: DateOverride): ValidationError | null {
  if (!isValidDateFormat(override.date)) {
    return {
      type: 'invalid_time',
      date: override.date,
      message: `Fecha inválida: ${override.date}`,
      severity: 'error',
    };
  }

  if (!override.fullDayClosed) {
    if (!override.start || !override.end) {
      return {
        type: 'invalid_time',
        date: override.date,
        message: 'Debe especificar hora de inicio y fin, o marcar como día libre',
        severity: 'error',
      };
    }

    if (!isValidTimeFormat(override.start)) {
      return {
        type: 'invalid_time',
        date: override.date,
        message: `Hora de inicio inválida: ${override.start}`,
        severity: 'error',
      };
    }

    if (!isValidTimeFormat(override.end)) {
      return {
        type: 'invalid_time',
        date: override.date,
        message: `Hora de fin inválida: ${override.end}`,
        severity: 'error',
      };
    }

    if (!isEndAfterStart(override.start, override.end)) {
      return {
        type: 'end_before_start',
        date: override.date,
        message: `La hora de fin debe ser posterior a la de inicio`,
        severity: 'error',
      };
    }
  }

  return null;
}

/**
 * Check for duplicate dates in overrides
 */
export function detectDuplicateDates(overrides: DateOverride[]): ValidationError[] {
  const errors: ValidationError[] = [];
  const seen = new Set<string>();

  for (const override of overrides) {
    if (seen.has(override.date)) {
      errors.push({
        type: 'duplicate_date',
        date: override.date,
        message: `Fecha duplicada: ${override.date}`,
        severity: 'error',
      });
    }
    seen.add(override.date);
  }

  return errors;
}

// =============================================================================
// RULES VALIDATION
// =============================================================================

/**
 * Validate scheduling rules
 */
export function validateRules(rules: SchedulingRules): ValidationError[] {
  const errors: ValidationError[] = [];

  // Validate break times if both are set
  if (rules.breakStart && rules.breakEnd) {
    if (!isValidTimeFormat(rules.breakStart)) {
      errors.push({
        type: 'invalid_time',
        message: `Hora de inicio de descanso inválida: ${rules.breakStart}`,
        severity: 'error',
      });
    }

    if (!isValidTimeFormat(rules.breakEnd)) {
      errors.push({
        type: 'invalid_time',
        message: `Hora de fin de descanso inválida: ${rules.breakEnd}`,
        severity: 'error',
      });
    }

    if (
      isValidTimeFormat(rules.breakStart) &&
      isValidTimeFormat(rules.breakEnd) &&
      !isEndAfterStart(rules.breakStart, rules.breakEnd)
    ) {
      errors.push({
        type: 'end_before_start',
        message: 'La hora de fin del descanso debe ser posterior a la de inicio',
        severity: 'error',
      });
    }
  } else if (rules.breakStart || rules.breakEnd) {
    // Only one is set - that's incomplete
    errors.push({
      type: 'invalid_time',
      message: 'Debe especificar tanto inicio como fin del descanso',
      severity: 'warning',
    });
  }

  // Validate numeric constraints
  if (rules.minSlotDuration !== undefined && rules.minSlotDuration < 5) {
    errors.push({
      type: 'invalid_time',
      message: 'La duración mínima debe ser al menos 5 minutos',
      severity: 'error',
    });
  }

  if (rules.maxPatientsPerHour !== undefined && rules.maxPatientsPerHour < 1) {
    errors.push({
      type: 'invalid_time',
      message: 'Debe permitir al menos 1 paciente por hora',
      severity: 'error',
    });
  }

  return errors;
}

// =============================================================================
// FULL AVAILABILITY VALIDATION
// =============================================================================

/**
 * Validate entire availability configuration
 */
export function validateAvailability(availability: DoctorAvailability): ValidationError[] {
  const errors: ValidationError[] = [];

  // Validate each slot individually
  for (const slot of availability.weeklySchedule) {
    const slotError = validateSlot(slot);
    if (slotError) {
      errors.push(slotError);
    }
  }

  // Check for overlaps
  errors.push(...detectOverlaps(availability.weeklySchedule));

  // Validate each override
  for (const override of availability.overrides) {
    const overrideError = validateOverride(override);
    if (overrideError) {
      errors.push(overrideError);
    }
  }

  // Check for duplicate dates
  errors.push(...detectDuplicateDates(availability.overrides));

  // Validate rules
  errors.push(...validateRules(availability.rules));

  return errors;
}

/**
 * Check if availability has any critical errors (not just warnings)
 */
export function hasErrors(errors: ValidationError[]): boolean {
  return errors.some((e) => e.severity === 'error');
}

/**
 * Get errors for a specific day
 */
export function getErrorsForDay(errors: ValidationError[], day: number): ValidationError[] {
  return errors.filter((e) => e.day === day);
}

/**
 * Get errors for a specific date
 */
export function getErrorsForDate(errors: ValidationError[], date: string): ValidationError[] {
  return errors.filter((e) => e.date === date);
}
