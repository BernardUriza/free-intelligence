/**
 * Availability Designer - Constants
 *
 * Days of week, presets, and default values
 */

import type { DoctorAvailability, AvailabilityTemplate, SchedulingRules } from './types';

// =============================================================================
// DAYS OF WEEK
// =============================================================================

export const DAYS_OF_WEEK = [
  { value: 0, label: 'Domingo', short: 'Dom', abbr: 'D' },
  { value: 1, label: 'Lunes', short: 'Lun', abbr: 'L' },
  { value: 2, label: 'Martes', short: 'Mar', abbr: 'M' },
  { value: 3, label: 'Miércoles', short: 'Mié', abbr: 'X' },
  { value: 4, label: 'Jueves', short: 'Jue', abbr: 'J' },
  { value: 5, label: 'Viernes', short: 'Vie', abbr: 'V' },
  { value: 6, label: 'Sábado', short: 'Sáb', abbr: 'S' },
] as const;

// Weekdays only (Mon-Fri)
export const WEEKDAYS = [1, 2, 3, 4, 5] as const;

// Weekend only (Sat-Sun)
export const WEEKEND = [0, 6] as const;

// =============================================================================
// DEFAULT VALUES
// =============================================================================

export const DEFAULT_RULES: SchedulingRules = {
  breakStart: undefined,
  breakEnd: undefined,
  minSlotDuration: 15,
  maxPatientsPerHour: 4,
  bufferBetweenAppointments: 5,
};

export const DEFAULT_WORK_START = '09:00';
export const DEFAULT_WORK_END = '18:00';
export const DEFAULT_BREAK_START = '13:00';
export const DEFAULT_BREAK_END = '14:00';

// =============================================================================
// PRESET TEMPLATES
// =============================================================================

export const AVAILABILITY_TEMPLATES: AvailabilityTemplate[] = [
  {
    id: 'standard-9-5',
    name: 'Estándar 9-18 (L-V)',
    description: '9:00 - 18:00, lunes a viernes, fines de semana libres',
    availability: {
      version: 1,
      weeklySchedule: [
        { day: 1, start: '09:00', end: '18:00' },
        { day: 2, start: '09:00', end: '18:00' },
        { day: 3, start: '09:00', end: '18:00' },
        { day: 4, start: '09:00', end: '18:00' },
        { day: 5, start: '09:00', end: '18:00' },
      ],
      overrides: [],
      rules: { ...DEFAULT_RULES },
    },
  },
  {
    id: 'morning-clinic',
    name: 'Clínica Matutina (L-V)',
    description: '8:00 - 14:00, lunes a viernes',
    availability: {
      version: 1,
      weeklySchedule: [
        { day: 1, start: '08:00', end: '14:00' },
        { day: 2, start: '08:00', end: '14:00' },
        { day: 3, start: '08:00', end: '14:00' },
        { day: 4, start: '08:00', end: '14:00' },
        { day: 5, start: '08:00', end: '14:00' },
      ],
      overrides: [],
      rules: { ...DEFAULT_RULES },
    },
  },
  {
    id: 'afternoon-clinic',
    name: 'Clínica Vespertina (L-V)',
    description: '15:00 - 21:00, lunes a viernes',
    availability: {
      version: 1,
      weeklySchedule: [
        { day: 1, start: '15:00', end: '21:00' },
        { day: 2, start: '15:00', end: '21:00' },
        { day: 3, start: '15:00', end: '21:00' },
        { day: 4, start: '15:00', end: '21:00' },
        { day: 5, start: '15:00', end: '21:00' },
      ],
      overrides: [],
      rules: { ...DEFAULT_RULES },
    },
  },
  {
    id: 'split-shift',
    name: 'Turno Partido (L-V)',
    description: '9:00 - 13:00 y 16:00 - 20:00, lunes a viernes',
    availability: {
      version: 1,
      weeklySchedule: [
        { day: 1, start: '09:00', end: '13:00', label: 'Mañana' },
        { day: 1, start: '16:00', end: '20:00', label: 'Tarde' },
        { day: 2, start: '09:00', end: '13:00', label: 'Mañana' },
        { day: 2, start: '16:00', end: '20:00', label: 'Tarde' },
        { day: 3, start: '09:00', end: '13:00', label: 'Mañana' },
        { day: 3, start: '16:00', end: '20:00', label: 'Tarde' },
        { day: 4, start: '09:00', end: '13:00', label: 'Mañana' },
        { day: 4, start: '16:00', end: '20:00', label: 'Tarde' },
        { day: 5, start: '09:00', end: '13:00', label: 'Mañana' },
        { day: 5, start: '16:00', end: '20:00', label: 'Tarde' },
      ],
      overrides: [],
      rules: { ...DEFAULT_RULES },
    },
  },
  {
    id: 'weekend-doctor',
    name: 'Doctor de Fin de Semana',
    description: '10:00 - 14:00, sábado y domingo',
    availability: {
      version: 1,
      weeklySchedule: [
        { day: 0, start: '10:00', end: '14:00' },
        { day: 6, start: '10:00', end: '14:00' },
      ],
      overrides: [],
      rules: { ...DEFAULT_RULES },
    },
  },
  {
    id: 'full-week',
    name: 'Semana Completa',
    description: '9:00 - 18:00, todos los días',
    availability: {
      version: 1,
      weeklySchedule: [
        { day: 0, start: '09:00', end: '18:00' },
        { day: 1, start: '09:00', end: '18:00' },
        { day: 2, start: '09:00', end: '18:00' },
        { day: 3, start: '09:00', end: '18:00' },
        { day: 4, start: '09:00', end: '18:00' },
        { day: 5, start: '09:00', end: '18:00' },
        { day: 6, start: '09:00', end: '18:00' },
      ],
      overrides: [],
      rules: { ...DEFAULT_RULES },
    },
  },
];

// =============================================================================
// COMMON EXCEPTION REASONS
// =============================================================================

export const COMMON_EXCEPTION_REASONS = [
  'Vacaciones',
  'Día festivo',
  'Conferencia',
  'Capacitación',
  'Cita personal',
  'Enfermedad',
  'Emergencia familiar',
  'Otro',
] as const;

// =============================================================================
// TIME OPTIONS
// =============================================================================

/**
 * Generate time options for dropdowns (every 15 minutes)
 */
export function generateTimeOptions(interval: 15 | 30 | 60 = 30): string[] {
  const options: string[] = [];
  for (let hour = 0; hour < 24; hour++) {
    for (let minute = 0; minute < 60; minute += interval) {
      options.push(
        `${hour.toString().padStart(2, '0')}:${minute.toString().padStart(2, '0')}`
      );
    }
  }
  return options;
}

export const TIME_OPTIONS_30MIN = generateTimeOptions(30);
export const TIME_OPTIONS_15MIN = generateTimeOptions(15);

// =============================================================================
// EMPTY STATE
// =============================================================================

export const EMPTY_AVAILABILITY: DoctorAvailability = {
  version: 1,
  weeklySchedule: [],
  overrides: [],
  rules: { ...DEFAULT_RULES },
};
