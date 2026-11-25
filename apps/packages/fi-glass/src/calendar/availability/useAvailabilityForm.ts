'use client';

import { useMemo, useState } from 'react';
import {
  DEFAULT_RULES,
  availabilityFromWeek,
  emptyAvailability,
  groupByDay,
  hasBlockingErrors,
  suggestNextSlot,
  validateAvailability,
  type AvailabilityError,
  type DateOverride,
  type DaySchedule,
  type DoctorAvailability,
  type SchedulingRules,
  type WeeklySlot,
  type WeekSchedule,
} from '@free-intelligence/core/availability';

interface Draft {
  week: WeekSchedule;
  overrides: DateOverride[];
  rules: SchedulingRules;
}

export interface AvailabilityForm extends Draft {
  availability: DoctorAvailability;
  errors: AvailabilityError[];
  isValid: boolean;
  isDirty: boolean;
  setDayWorking: (day: number, isWorking: boolean) => void;
  addSlot: (day: number) => void;
  removeSlot: (day: number, index: number) => void;
  updateSlot: (day: number, index: number, changes: Partial<WeeklySlot>) => void;
  addOverride: (override: DateOverride) => void;
  removeOverride: (date: string) => void;
  updateOverride: (date: string, changes: Partial<DateOverride>) => void;
  updateRules: (changes: Partial<SchedulingRules>) => void;
  applyWeek: (weeklySchedule: WeeklySlot[]) => void;
  reset: () => void;
}

const draftOf = (availability: DoctorAvailability): Draft => ({
  week: groupByDay(availability.weeklySchedule),
  overrides: availability.overrides,
  rules: availability.rules ?? { ...DEFAULT_RULES },
});

const byDate = (a: DateOverride, b: DateOverride) => a.date.localeCompare(b.date);

export function useAvailabilityForm(initial?: DoctorAvailability | null): AvailabilityForm {
  const [draft, setDraft] = useState<Draft>(() => draftOf(initial ?? emptyAvailability()));
  const [isDirty, setIsDirty] = useState(false);

  const availability = useMemo(() => availabilityFromWeek(draft.week, draft.overrides, draft.rules), [draft]);
  const errors = useMemo(() => validateAvailability(availability), [availability]);

  const edit = (change: (draft: Draft) => Partial<Draft>) => {
    setDraft((current) => ({ ...current, ...change(current) }));
    setIsDirty(true);
  };
  const editDay = (day: number, change: (schedule: DaySchedule) => DaySchedule) =>
    edit(({ week }) => ({ week: { ...week, [day]: change(week[day]) } }));

  return {
    ...draft,
    availability,
    errors,
    isValid: !hasBlockingErrors(errors),
    isDirty,

    setDayWorking: (day, isWorking) =>
      editDay(day, ({ slots }) => {
        const first = isWorking && slots.length === 0 ? suggestNextSlot(day, []) : null;
        return { isWorking, slots: first ? [first] : slots };
      }),
    addSlot: (day) =>
      editDay(day, (schedule) => {
        const next = suggestNextSlot(day, schedule.slots);
        return next ? { isWorking: true, slots: [...schedule.slots, next] } : schedule;
      }),
    removeSlot: (day, index) =>
      editDay(day, ({ slots }) => {
        const remaining = slots.filter((_, i) => i !== index);
        return { isWorking: remaining.length > 0, slots: remaining };
      }),
    updateSlot: (day, index, changes) =>
      editDay(day, (schedule) => ({
        ...schedule,
        slots: schedule.slots.map((slot, i) => (i === index ? { ...slot, ...changes } : slot)),
      })),

    addOverride: (override) =>
      edit(({ overrides }) =>
        overrides.some(({ date }) => date === override.date) ? {} : { overrides: [...overrides, override].sort(byDate) },
      ),
    removeOverride: (date) => edit(({ overrides }) => ({ overrides: overrides.filter((o) => o.date !== date) })),
    updateOverride: (date, changes) =>
      edit(({ overrides }) => ({ overrides: overrides.map((o) => (o.date === date ? { ...o, ...changes } : o)) })),

    updateRules: (changes) => edit(({ rules }) => ({ rules: { ...rules, ...changes } })),
    applyWeek: (weeklySchedule) => edit(() => ({ week: groupByDay(weeklySchedule) })),
    reset: () => {
      setDraft(draftOf(initial ?? emptyAvailability()));
      setIsDirty(false);
    },
  };
}
