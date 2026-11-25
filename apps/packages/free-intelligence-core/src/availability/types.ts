/** `HH:mm`, 24 h. */
export type TimeOfDay = string;

/** `YYYY-MM-DD`. */
export type CalendarDate = string;

export interface WeeklySlot {
  /** As JavaScript counts it: 0 is Sunday. */
  day: number;
  start: TimeOfDay;
  end: TimeOfDay;
  label?: string;
}

/** Replaces the weekly pattern on one date. Without `fullDayClosed` it carries its own hours. */
export interface DateOverride {
  date: CalendarDate;
  start?: TimeOfDay;
  end?: TimeOfDay;
  fullDayClosed: boolean;
  reason?: string;
}

/** Durations are minutes. */
export interface SchedulingRules {
  breakStart?: TimeOfDay;
  breakEnd?: TimeOfDay;
  minSlotDuration?: number;
  maxPatientsPerHour?: number;
  bufferBetweenAppointments?: number;
}

export interface DoctorAvailability {
  version: number;
  weeklySchedule: WeeklySlot[];
  overrides: DateOverride[];
  rules: SchedulingRules;
}

export type AvailabilityErrorType =
  | 'overlap'
  | 'invalid_time'
  | 'end_before_start'
  | 'duplicate_date';

export interface AvailabilityError {
  type: AvailabilityErrorType;
  day?: number;
  date?: CalendarDate;
  /** Position in that day's list, when the error belongs to one slot. */
  slotIndex?: number;
  message: string;
  severity: 'error' | 'warning';
}

/** Editing keeps the slots of a day that was switched off, so switching it back restores them. */
export interface DaySchedule {
  isWorking: boolean;
  slots: WeeklySlot[];
}

export type WeekSchedule = Record<number, DaySchedule>;

export interface AvailabilityTemplate {
  id: string;
  name: string;
  description: string;
  weeklySchedule: WeeklySlot[];
}
