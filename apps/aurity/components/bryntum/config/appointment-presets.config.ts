/**
 * Appointments View Presets Configuration
 * Card: FI-CHECKIN-005 (Phase 2)
 *
 * View configurations for medical appointments calendar.
 * Supports Day, Week, and Month views optimized for clinic schedules.
 */

import { CalendarDays, CalendarRange, LayoutGrid } from 'lucide-react';
import type { ViewPresetConfig } from '../types/scheduler.types';

/**
 * DAY VIEW
 * - Shows 3 days: yesterday, today, tomorrow
 * - Hourly timeline from 8 AM to 8 PM (clinic operating hours)
 * - 80px tick width for comfortable appointment display
 * - Shows full date header + hourly slots
 */
export const DAY_PRESET: ViewPresetConfig = {
  id: 'day',
  label: 'Día',
  icon: CalendarDays,
  preset: {
    base: 'hourAndDay',
    tickWidth: 80,
    headers: [
      { unit: 'day', dateFormat: 'ddd D MMM' },
      { unit: 'hour', dateFormat: 'HH:mm' },
    ],
  },
  getDateRange: (date: Date) => {
    // Start: yesterday at 8 AM
    const start = new Date(date);
    start.setDate(start.getDate() - 1);
    start.setHours(8, 0, 0, 0);
    
    // End: tomorrow at 8 PM
    const end = new Date(date);
    end.setDate(end.getDate() + 1);
    end.setHours(20, 0, 0, 0);
    
    return { start, end };
  },
  navigationUnit: 'day',
  dateFormat: { weekday: 'long', day: 'numeric', month: 'long' },
};

/**
 * WEEK VIEW
 * - Shows Monday-Sunday week grid
 * - 100px tick width per day
 * - Week number header + daily columns
 */
export const WEEK_PRESET: ViewPresetConfig = {
  id: 'week',
  label: 'Semana',
  icon: CalendarRange,
  preset: {
    base: 'weekAndDay',
    tickWidth: 100,
    headers: [
      { unit: 'week', dateFormat: 'Semana W, MMMM YYYY' },
      { unit: 'day', dateFormat: 'ddd D' },
    ],
  },
  getDateRange: (date: Date) => {
    const start = new Date(date);
    const dayOfWeek = start.getDay();
    // Calculate Monday (0 = Sunday, 1 = Monday, etc.)
    const diff = start.getDate() - dayOfWeek + (dayOfWeek === 0 ? -6 : 1);
    start.setDate(diff);
    start.setHours(0, 0, 0, 0);
    
    const end = new Date(start);
    end.setDate(start.getDate() + 6); // Sunday
    end.setHours(23, 59, 59, 999);
    
    return { start, end };
  },
  navigationUnit: 'week',
  dateFormat: { day: 'numeric', month: 'short' },
};

/**
 * MONTH VIEW
 * - Shows entire month calendar
 * - 50px tick width for compact display
 * - Month header + daily cells
 */
export const MONTH_PRESET: ViewPresetConfig = {
  id: 'month',
  label: 'Mes',
  icon: LayoutGrid,
  preset: {
    base: 'monthAndYear',
    tickWidth: 50,
    headers: [
      { unit: 'month', dateFormat: 'MMMM YYYY' },
      { unit: 'day', dateFormat: 'D' },
    ],
  },
  getDateRange: (date: Date) => {
    const start = new Date(date.getFullYear(), date.getMonth(), 1);
    const end = new Date(date.getFullYear(), date.getMonth() + 1, 0, 23, 59, 59, 999);
    return { start, end };
  },
  navigationUnit: 'month',
  dateFormat: { month: 'long', year: 'numeric' },
};

/**
 * Appointments View Presets
 * 
 * @remarks
 * - Day view: Hourly schedule for detailed appointment management
 * - Week view: Multi-day planning and resource allocation
 * - Month view: High-level calendar overview
 * 
 * @example
 * ```ts
 * const presetConfig = APPOINTMENT_VIEW_PRESETS['day'];
 * const { start, end } = presetConfig.getDateRange(new Date());
 * ```
 */
export const APPOINTMENT_VIEW_PRESETS = {
  day: DAY_PRESET,
  week: WEEK_PRESET,
  month: MONTH_PRESET,
} as const;

export type AppointmentViewMode = keyof typeof APPOINTMENT_VIEW_PRESETS;
