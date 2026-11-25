/** `HH:mm`, 24 h. */
type TimeOfDay = string;
/** `YYYY-MM-DD`. */
type CalendarDate = string;
interface WeeklySlot {
    /** As JavaScript counts it: 0 is Sunday. */
    day: number;
    start: TimeOfDay;
    end: TimeOfDay;
    label?: string;
}
/** Replaces the weekly pattern on one date. Without `fullDayClosed` it carries its own hours. */
interface DateOverride {
    date: CalendarDate;
    start?: TimeOfDay;
    end?: TimeOfDay;
    fullDayClosed: boolean;
    reason?: string;
}
/** Durations are minutes. */
interface SchedulingRules {
    breakStart?: TimeOfDay;
    breakEnd?: TimeOfDay;
    minSlotDuration?: number;
    maxPatientsPerHour?: number;
    bufferBetweenAppointments?: number;
}
interface DoctorAvailability {
    version: number;
    weeklySchedule: WeeklySlot[];
    overrides: DateOverride[];
    rules: SchedulingRules;
}
type AvailabilityErrorType = 'overlap' | 'invalid_time' | 'end_before_start' | 'duplicate_date';
interface AvailabilityError {
    type: AvailabilityErrorType;
    day?: number;
    date?: CalendarDate;
    /** Position in that day's list, when the error belongs to one slot. */
    slotIndex?: number;
    message: string;
    severity: 'error' | 'warning';
}
/** Editing keeps the slots of a day that was switched off, so switching it back restores them. */
interface DaySchedule {
    isWorking: boolean;
    slots: WeeklySlot[];
}
type WeekSchedule = Record<number, DaySchedule>;
interface AvailabilityTemplate {
    id: string;
    name: string;
    description: string;
    weeklySchedule: WeeklySlot[];
}

declare const AVAILABILITY_VERSION = 1;
declare const DAYS_OF_WEEK: readonly [{
    readonly value: 0;
    readonly label: "Domingo";
    readonly short: "Dom";
    readonly abbr: "D";
}, {
    readonly value: 1;
    readonly label: "Lunes";
    readonly short: "Lun";
    readonly abbr: "L";
}, {
    readonly value: 2;
    readonly label: "Martes";
    readonly short: "Mar";
    readonly abbr: "M";
}, {
    readonly value: 3;
    readonly label: "Miércoles";
    readonly short: "Mié";
    readonly abbr: "X";
}, {
    readonly value: 4;
    readonly label: "Jueves";
    readonly short: "Jue";
    readonly abbr: "J";
}, {
    readonly value: 5;
    readonly label: "Viernes";
    readonly short: "Vie";
    readonly abbr: "V";
}, {
    readonly value: 6;
    readonly label: "Sábado";
    readonly short: "Sáb";
    readonly abbr: "S";
}];
declare const WEEKDAYS: readonly [1, 2, 3, 4, 5];
declare const WEEKEND: readonly [0, 6];
declare const DEFAULT_WORK_START = "09:00";
declare const DEFAULT_WORK_END = "18:00";
declare const DEFAULT_BREAK_START = "13:00";
declare const DEFAULT_BREAK_END = "14:00";
declare const SLOT_DURATION_CHOICES: readonly [15, 20, 30, 45, 60];
declare const DEFAULT_RULES: Readonly<SchedulingRules>;
declare const COMMON_EXCEPTION_REASONS: readonly ["Vacaciones", "Día festivo", "Conferencia", "Capacitación", "Cita personal", "Enfermedad", "Emergencia familiar"];
declare function emptyAvailability(): DoctorAvailability;
declare const AVAILABILITY_TEMPLATES: AvailabilityTemplate[];

declare const MINUTES_PER_DAY: number;
declare function timeToMinutes(time: TimeOfDay): number;
declare function minutesToTime(minutes: number): TimeOfDay;
declare function isValidTime(time: string): boolean;
declare function isEndAfterStart(start: TimeOfDay, end: TimeOfDay): boolean;
declare function isValidDate(date: string): boolean;
/** Local calendar date; `toISOString` would roll to tomorrow in the evening west of Greenwich. */
declare function toCalendarDate(date: Date): CalendarDate;

declare function slotsOverlap(a: WeeklySlot, b: WeeklySlot): boolean;
declare function validateAvailability(availability: DoctorAvailability): AvailabilityError[];
declare function hasBlockingErrors(errors: AvailabilityError[]): boolean;
interface ScheduleGap {
    day: number;
    from: string;
    to: string;
}
declare function findGaps(slots: WeeklySlot[]): ScheduleGap[];

declare function groupByDay(weeklySchedule: WeeklySlot[]): WeekSchedule;
declare function availabilityFromWeek(week: WeekSchedule, overrides: DateOverride[], rules: SchedulingRules): DoctorAvailability;
/** `null` when the day has no room left before midnight. */
declare function suggestNextSlot(day: number, existing: WeeklySlot[]): WeeklySlot | null;
declare function weeklyHours(availability: DoctorAvailability): number;
declare function workingDays(availability: DoctorAvailability): number[];

export { AVAILABILITY_TEMPLATES, AVAILABILITY_VERSION, type AvailabilityError, type AvailabilityErrorType, type AvailabilityTemplate, COMMON_EXCEPTION_REASONS, type CalendarDate, DAYS_OF_WEEK, DEFAULT_BREAK_END, DEFAULT_BREAK_START, DEFAULT_RULES, DEFAULT_WORK_END, DEFAULT_WORK_START, type DateOverride, type DaySchedule, type DoctorAvailability, MINUTES_PER_DAY, SLOT_DURATION_CHOICES, type ScheduleGap, type SchedulingRules, type TimeOfDay, WEEKDAYS, WEEKEND, type WeekSchedule, type WeeklySlot, availabilityFromWeek, emptyAvailability, findGaps, groupByDay, hasBlockingErrors, isEndAfterStart, isValidDate, isValidTime, minutesToTime, slotsOverlap, suggestNextSlot, timeToMinutes, toCalendarDate, validateAvailability, weeklyHours, workingDays };
