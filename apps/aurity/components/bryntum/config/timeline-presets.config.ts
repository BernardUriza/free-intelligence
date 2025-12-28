/**
 * Timeline View Presets Configuration
 * 
 * Purpose: Define consistent time axis configurations for Bryntum SchedulerPro
 * across different temporal granularities (day, week, month).
 * 
 * Design Decisions:
 * - Three core presets optimized for medical/chat timeline visualization
 * - Spanish locale for user-facing labels (es-MX)
 * - Balanced tick widths for optimal visual density
 * - Navigation aligned with calendar boundaries (start of day/week/month)
 * 
 * @see {@link https://bryntum.com/products/schedulerpro/docs/api/Scheduler/preset/ViewPreset}
 */

import {
  CalendarDays,
  CalendarRange,
  LayoutGrid,
  type LucideIcon,
} from 'lucide-react';
import type { ViewMode, ViewPresetConfig } from '../types/scheduler.types';

/**
 * DAY VIEW
 * 
 * Optimal for: Detailed event inspection within a 24-hour period
 * Tick width: 60px (hourly granularity)
 * Time span: 00:00 - 23:59 of selected date
 */
const DAY_PRESET: ViewPresetConfig = {
  id: 'day',
  label: 'Día',
  icon: CalendarDays,
  preset: {
    base: 'hourAndDay',
    tickWidth: 60,
    headers: [
      {
        unit: 'day',
        dateFormat: 'dddd, D MMMM YYYY', // "lunes, 8 diciembre 2025"
      },
      {
        unit: 'hour',
        dateFormat: 'HH:mm', // "14:30"
      },
    ],
  },
  getDateRange: (date: Date) => {
    const start = new Date(date);
    start.setHours(0, 0, 0, 0);
    
    const end = new Date(date);
    end.setHours(23, 59, 59, 999);
    
    return { start, end };
  },
  navigationUnit: 'day',
  dateFormat: { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' },
};

/**
 * WEEK VIEW
 * 
 * Optimal for: Weekly patterns, multi-day session analysis
 * Tick width: 80px (daily granularity)
 * Time span: Monday 00:00 - Sunday 23:59 (ISO 8601 week)
 * 
 * Note: Week starts on Monday (standard for medical scheduling)
 */
const WEEK_PRESET: ViewPresetConfig = {
  id: 'week',
  label: 'Semana',
  icon: CalendarRange,
  preset: {
    base: 'weekAndDay',
    tickWidth: 80,
    headers: [
      {
        unit: 'week',
        dateFormat: 'Semana W, MMMM YYYY', // "Semana 49, diciembre 2025"
      },
      {
        unit: 'day',
        dateFormat: 'ddd D', // "lun 8"
      },
    ],
  },
  getDateRange: (date: Date) => {
    const start = new Date(date);
    const dayOfWeek = start.getDay();
    
    // Calculate days to subtract to get to Monday (ISO week start)
    const diff = start.getDate() - dayOfWeek + (dayOfWeek === 0 ? -6 : 1);
    start.setDate(diff);
    start.setHours(0, 0, 0, 0);
    
    const end = new Date(start);
    end.setDate(start.getDate() + 6); // Sunday
    end.setHours(23, 59, 59, 999);
    
    return { start, end };
  },
  navigationUnit: 'week',
  dateFormat: { weekday: 'short', day: 'numeric', month: 'short' },
};

/**
 * MONTH VIEW
 * 
 * Optimal for: Long-term trends, monthly session distribution
 * Tick width: 40px (daily granularity, compact)
 * Time span: First day of month 00:00 - Last day of month 23:59
 */
const MONTH_PRESET: ViewPresetConfig = {
  id: 'month',
  label: 'Mes',
  icon: LayoutGrid,
  preset: {
    base: 'monthAndYear',
    tickWidth: 40,
    headers: [
      {
        unit: 'month',
        dateFormat: 'MMMM YYYY', // "diciembre 2025"
      },
      {
        unit: 'day',
        dateFormat: 'D', // "8"
      },
    ],
  },
  getDateRange: (date: Date) => {
    // First day of current month
    const start = new Date(date.getFullYear(), date.getMonth(), 1);
    
    // Last day of current month (day 0 of next month)
    const end = new Date(date.getFullYear(), date.getMonth() + 1, 0, 23, 59, 59, 999);
    
    return { start, end };
  },
  navigationUnit: 'month',
  dateFormat: { month: 'long', year: 'numeric' },
};

/**
 * VIEW_PRESETS Registry
 * 
 * Centralized configuration for all available view modes.
 * Used by TimelineScheduler to switch between temporal granularities.
 * 
 * Usage:
 * ```ts
 * const config = VIEW_PRESETS['week'];
 * const { start, end } = config.getDateRange(new Date());
 * scheduler.viewPreset = config.preset;
 * ```
 */
export const VIEW_PRESETS: Record<ViewMode, ViewPresetConfig> = {
  day: DAY_PRESET,
  week: WEEK_PRESET,
  month: MONTH_PRESET,
};

/**
 * Get all available view modes as array
 * Useful for rendering view mode selector UI
 */
export const getViewModes = (): ViewMode[] => {
  return Object.keys(VIEW_PRESETS) as ViewMode[];
};

/**
 * Get icon component for a specific view mode
 */
export const getViewModeIcon = (mode: ViewMode): LucideIcon => {
  return VIEW_PRESETS[mode].icon;
};

/**
 * Get human-readable label for a view mode
 */
export const getViewModeLabel = (mode: ViewMode): string => {
  return VIEW_PRESETS[mode].label;
};

/**
 * Calculate date range for a given view mode and date
 * 
 * @param mode - View mode (day/week/month)
 * @param date - Reference date (defaults to today)
 * @returns Start and end dates for the view range
 */
export const getDateRangeForView = (
  mode: ViewMode,
  date: Date = new Date()
): { start: Date; end: Date } => {
  return VIEW_PRESETS[mode].getDateRange(date);
};

/**
 * Navigate date by one unit forward or backward
 * 
 * @param mode - Current view mode
 * @param currentDate - Current reference date
 * @param direction - Navigation direction
 * @returns New date after navigation
 */
export const navigateDate = (
  mode: ViewMode,
  currentDate: Date,
  direction: 'prev' | 'next'
): Date => {
  const newDate = new Date(currentDate);
  const delta = direction === 'next' ? 1 : -1;
  const unit = VIEW_PRESETS[mode].navigationUnit;

  switch (unit) {
    case 'day':
      newDate.setDate(newDate.getDate() + delta);
      break;
    case 'week':
      newDate.setDate(newDate.getDate() + delta * 7);
      break;
    case 'month':
      newDate.setMonth(newDate.getMonth() + delta);
      break;
  }

  return newDate;
};

/**
 * Format date for display based on view mode
 * 
 * @param mode - Current view mode
 * @param date - Date to format
 * @returns Formatted date string (Spanish locale)
 */
export const formatDateForView = (mode: ViewMode, date: Date): string => {
  const config = VIEW_PRESETS[mode];
  const { start, end } = config.getDateRange(date);

  // Week view shows range
  if (mode === 'week') {
    const startStr = start.toLocaleDateString('es-MX', {
      day: 'numeric',
      month: 'short',
    });
    const endStr = end.toLocaleDateString('es-MX', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
    return `${startStr} - ${endStr}`;
  }

  // Day and month views show single date
  return date.toLocaleDateString('es-MX', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });
};
