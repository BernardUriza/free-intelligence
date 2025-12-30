/**
 * Availability Designer - Form State Hook
 *
 * Manages the complete form state for the availability designer
 */

'use client';

import { useState, useCallback, useMemo } from 'react';
import type {
  DoctorAvailability,
  WeeklySlot,
  DateOverride,
  SchedulingRules,
  DaySchedule,
  ValidationError,
} from '../types';
import {
  DAYS_OF_WEEK,
  DEFAULT_WORK_START,
  DEFAULT_WORK_END,
  DEFAULT_RULES,
  EMPTY_AVAILABILITY,
} from '../constants';
import { validateAvailability, hasErrors } from '../utils/validation';
import { toFormState, fromFormState, fromLegacy } from '../utils/transform';

// =============================================================================
// TYPES
// =============================================================================

export interface UseAvailabilityFormOptions {
  initialAvailability?: DoctorAvailability;
  legacyStartTime?: string | null;
  legacyEndTime?: string | null;
}

export interface UseAvailabilityFormReturn {
  // State
  weeklySchedule: Record<number, DaySchedule>;
  overrides: DateOverride[];
  rules: SchedulingRules;
  isDirty: boolean;
  errors: ValidationError[];
  hasValidationErrors: boolean;

  // Weekly schedule actions
  setDayWorking: (day: number, isWorking: boolean) => void;
  addSlot: (day: number) => void;
  removeSlot: (day: number, index: number) => void;
  updateSlot: (day: number, index: number, updates: Partial<WeeklySlot>) => void;

  // Override actions
  addOverride: (override: DateOverride) => void;
  removeOverride: (date: string) => void;
  updateOverride: (date: string, updates: Partial<DateOverride>) => void;

  // Rules actions
  updateRules: (updates: Partial<SchedulingRules>) => void;

  // Template actions
  applyTemplate: (availability: DoctorAvailability) => void;

  // Form actions
  reset: () => void;
  validate: () => boolean;
  getAvailability: () => DoctorAvailability;
}

// =============================================================================
// HOOK
// =============================================================================

export function useAvailabilityForm(
  options: UseAvailabilityFormOptions = {}
): UseAvailabilityFormReturn {
  // Determine initial availability
  const initialAvailability = useMemo(() => {
    if (options.initialAvailability) {
      return options.initialAvailability;
    }
    if (options.legacyStartTime || options.legacyEndTime) {
      return fromLegacy(options.legacyStartTime ?? null, options.legacyEndTime ?? null);
    }
    return EMPTY_AVAILABILITY;
  }, [options.initialAvailability, options.legacyStartTime, options.legacyEndTime]);

  // Form state
  const [weeklySchedule, setWeeklySchedule] = useState<Record<number, DaySchedule>>(
    () => toFormState(initialAvailability)
  );
  const [overrides, setOverrides] = useState<DateOverride[]>(
    () => initialAvailability.overrides
  );
  const [rules, setRules] = useState<SchedulingRules>(
    () => initialAvailability.rules || { ...DEFAULT_RULES }
  );
  const [isDirty, setIsDirty] = useState(false);

  // Computed errors
  const currentAvailability = useMemo(
    () => fromFormState(weeklySchedule, overrides, rules),
    [weeklySchedule, overrides, rules]
  );

  const errors = useMemo(
    () => validateAvailability(currentAvailability),
    [currentAvailability]
  );

  const hasValidationErrors = useMemo(() => hasErrors(errors), [errors]);

  // ==========================================================================
  // WEEKLY SCHEDULE ACTIONS
  // ==========================================================================

  const setDayWorking = useCallback((day: number, isWorking: boolean) => {
    setWeeklySchedule((prev) => {
      const current = prev[day] || { isWorking: false, slots: [] };

      if (isWorking && current.slots.length === 0) {
        // Add default slot when enabling a day
        return {
          ...prev,
          [day]: {
            isWorking: true,
            slots: [{ day, start: DEFAULT_WORK_START, end: DEFAULT_WORK_END }],
          },
        };
      }

      return {
        ...prev,
        [day]: { ...current, isWorking },
      };
    });
    setIsDirty(true);
  }, []);

  const addSlot = useCallback((day: number) => {
    setWeeklySchedule((prev) => {
      const current = prev[day] || { isWorking: true, slots: [] };
      const lastSlot = current.slots[current.slots.length - 1];

      // Default: start 1 hour after last slot ends, or DEFAULT_WORK_START
      let newStart = DEFAULT_WORK_START;
      let newEnd = DEFAULT_WORK_END;

      if (lastSlot) {
        const lastEndMinutes = timeToMinutes(lastSlot.end);
        newStart = minutesToTime(lastEndMinutes + 60); // 1 hour after
        newEnd = minutesToTime(lastEndMinutes + 60 + 240); // 4 hours duration
      }

      return {
        ...prev,
        [day]: {
          isWorking: true,
          slots: [...current.slots, { day, start: newStart, end: newEnd }],
        },
      };
    });
    setIsDirty(true);
  }, []);

  const removeSlot = useCallback((day: number, index: number) => {
    setWeeklySchedule((prev) => {
      const current = prev[day];
      if (!current) return prev;

      const newSlots = current.slots.filter((_, i) => i !== index);

      return {
        ...prev,
        [day]: {
          isWorking: newSlots.length > 0,
          slots: newSlots,
        },
      };
    });
    setIsDirty(true);
  }, []);

  const updateSlot = useCallback(
    (day: number, index: number, updates: Partial<WeeklySlot>) => {
      setWeeklySchedule((prev) => {
        const current = prev[day];
        if (!current) return prev;

        const newSlots = current.slots.map((slot, i) =>
          i === index ? { ...slot, ...updates } : slot
        );

        return {
          ...prev,
          [day]: { ...current, slots: newSlots },
        };
      });
      setIsDirty(true);
    },
    []
  );

  // ==========================================================================
  // OVERRIDE ACTIONS
  // ==========================================================================

  const addOverride = useCallback((override: DateOverride) => {
    setOverrides((prev) => {
      // Don't add duplicates
      if (prev.some((o) => o.date === override.date)) {
        return prev;
      }
      // Sort by date
      return [...prev, override].sort((a, b) => a.date.localeCompare(b.date));
    });
    setIsDirty(true);
  }, []);

  const removeOverride = useCallback((date: string) => {
    setOverrides((prev) => prev.filter((o) => o.date !== date));
    setIsDirty(true);
  }, []);

  const updateOverride = useCallback(
    (date: string, updates: Partial<DateOverride>) => {
      setOverrides((prev) =>
        prev.map((o) => (o.date === date ? { ...o, ...updates } : o))
      );
      setIsDirty(true);
    },
    []
  );

  // ==========================================================================
  // RULES ACTIONS
  // ==========================================================================

  const updateRules = useCallback((updates: Partial<SchedulingRules>) => {
    setRules((prev) => ({ ...prev, ...updates }));
    setIsDirty(true);
  }, []);

  // ==========================================================================
  // TEMPLATE ACTIONS
  // ==========================================================================

  const applyTemplate = useCallback((availability: DoctorAvailability) => {
    setWeeklySchedule(toFormState(availability));
    setOverrides(availability.overrides);
    setRules(availability.rules || { ...DEFAULT_RULES });
    setIsDirty(true);
  }, []);

  // ==========================================================================
  // FORM ACTIONS
  // ==========================================================================

  const reset = useCallback(() => {
    setWeeklySchedule(toFormState(initialAvailability));
    setOverrides(initialAvailability.overrides);
    setRules(initialAvailability.rules || { ...DEFAULT_RULES });
    setIsDirty(false);
  }, [initialAvailability]);

  const validate = useCallback(() => {
    return !hasValidationErrors;
  }, [hasValidationErrors]);

  const getAvailability = useCallback((): DoctorAvailability => {
    return fromFormState(weeklySchedule, overrides, rules);
  }, [weeklySchedule, overrides, rules]);

  // ==========================================================================
  // RETURN
  // ==========================================================================

  return {
    // State
    weeklySchedule,
    overrides,
    rules,
    isDirty,
    errors,
    hasValidationErrors,

    // Weekly schedule actions
    setDayWorking,
    addSlot,
    removeSlot,
    updateSlot,

    // Override actions
    addOverride,
    removeOverride,
    updateOverride,

    // Rules actions
    updateRules,

    // Template actions
    applyTemplate,

    // Form actions
    reset,
    validate,
    getAvailability,
  };
}

// =============================================================================
// HELPERS
// =============================================================================

function timeToMinutes(time: string): number {
  const [hours, minutes] = time.split(':').map(Number);
  return hours * 60 + minutes;
}

function minutesToTime(minutes: number): string {
  const h = Math.floor(minutes / 60) % 24;
  const m = minutes % 60;
  return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`;
}

export default useAvailabilityForm;
