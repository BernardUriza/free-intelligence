import type { CalendarDate, TimeOfDay } from './types';

export const MINUTES_PER_DAY = 24 * 60;

const TIME_PATTERN = /^([01]\d|2[0-3]):[0-5]\d$/;
const DATE_PATTERN = /^(\d{4})-(\d{2})-(\d{2})$/;

const twoDigits = (value: number): string => String(value).padStart(2, '0');

export function timeToMinutes(time: TimeOfDay): number {
  const [hours, minutes] = time.split(':').map(Number);
  return hours * 60 + minutes;
}

export function minutesToTime(minutes: number): TimeOfDay {
  return `${twoDigits(Math.floor(minutes / 60) % 24)}:${twoDigits(minutes % 60)}`;
}

export function isValidTime(time: string): boolean {
  return TIME_PATTERN.test(time);
}

export function isEndAfterStart(start: TimeOfDay, end: TimeOfDay): boolean {
  return timeToMinutes(end) > timeToMinutes(start);
}

export function isValidDate(date: string): boolean {
  const match = DATE_PATTERN.exec(date);
  if (!match) return false;
  const [year, month, day] = match.slice(1).map(Number);
  const parsed = new Date(Date.UTC(year, month - 1, day));
  return parsed.getUTCMonth() === month - 1 && parsed.getUTCDate() === day;
}

/** Local calendar date; `toISOString` would roll to tomorrow in the evening west of Greenwich. */
export function toCalendarDate(date: Date): CalendarDate {
  return `${date.getFullYear()}-${twoDigits(date.getMonth() + 1)}-${twoDigits(date.getDate())}`;
}
