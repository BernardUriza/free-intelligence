import type { AvailabilityTemplate, DoctorAvailability, SchedulingRules, WeeklySlot } from './types';

export const AVAILABILITY_VERSION = 1;

export const DAYS_OF_WEEK = [
  { value: 0, label: 'Domingo', short: 'Dom', abbr: 'D' },
  { value: 1, label: 'Lunes', short: 'Lun', abbr: 'L' },
  { value: 2, label: 'Martes', short: 'Mar', abbr: 'M' },
  { value: 3, label: 'Miércoles', short: 'Mié', abbr: 'X' },
  { value: 4, label: 'Jueves', short: 'Jue', abbr: 'J' },
  { value: 5, label: 'Viernes', short: 'Vie', abbr: 'V' },
  { value: 6, label: 'Sábado', short: 'Sáb', abbr: 'S' },
] as const;

export const WEEKDAYS = [1, 2, 3, 4, 5] as const;
export const WEEKEND = [0, 6] as const;

export const DEFAULT_WORK_START = '09:00';
export const DEFAULT_WORK_END = '18:00';
export const DEFAULT_BREAK_START = '13:00';
export const DEFAULT_BREAK_END = '14:00';

export const SLOT_DURATION_CHOICES = [15, 20, 30, 45, 60] as const;

export const DEFAULT_RULES: Readonly<SchedulingRules> = {
  minSlotDuration: 15,
  maxPatientsPerHour: 4,
  bufferBetweenAppointments: 5,
};

export const COMMON_EXCEPTION_REASONS = [
  'Vacaciones',
  'Día festivo',
  'Conferencia',
  'Capacitación',
  'Cita personal',
  'Enfermedad',
  'Emergencia familiar',
] as const;

export function emptyAvailability(): DoctorAvailability {
  return { version: AVAILABILITY_VERSION, weeklySchedule: [], overrides: [], rules: { ...DEFAULT_RULES } };
}

const everyDay = (days: readonly number[], ...hours: Omit<WeeklySlot, 'day'>[]): WeeklySlot[] =>
  days.flatMap((day) => hours.map((slot) => ({ day, ...slot })));

export const AVAILABILITY_TEMPLATES: AvailabilityTemplate[] = [
  {
    id: 'standard-9-5',
    name: 'Estándar 9-18 (L-V)',
    description: '9:00 - 18:00, lunes a viernes, fines de semana libres',
    weeklySchedule: everyDay(WEEKDAYS, { start: '09:00', end: '18:00' }),
  },
  {
    id: 'morning-clinic',
    name: 'Clínica Matutina (L-V)',
    description: '8:00 - 14:00, lunes a viernes',
    weeklySchedule: everyDay(WEEKDAYS, { start: '08:00', end: '14:00' }),
  },
  {
    id: 'afternoon-clinic',
    name: 'Clínica Vespertina (L-V)',
    description: '15:00 - 21:00, lunes a viernes',
    weeklySchedule: everyDay(WEEKDAYS, { start: '15:00', end: '21:00' }),
  },
  {
    id: 'split-shift',
    name: 'Turno Partido (L-V)',
    description: '9:00 - 13:00 y 16:00 - 20:00, lunes a viernes',
    weeklySchedule: everyDay(
      WEEKDAYS,
      { start: '09:00', end: '13:00', label: 'Mañana' },
      { start: '16:00', end: '20:00', label: 'Tarde' },
    ),
  },
  {
    id: 'weekend-doctor',
    name: 'Doctor de Fin de Semana',
    description: '10:00 - 14:00, sábado y domingo',
    weeklySchedule: everyDay(WEEKEND, { start: '10:00', end: '14:00' }),
  },
  {
    id: 'full-week',
    name: 'Semana Completa',
    description: '9:00 - 18:00, todos los días',
    weeklySchedule: everyDay([0, ...WEEKDAYS, 6], { start: '09:00', end: '18:00' }),
  },
];
