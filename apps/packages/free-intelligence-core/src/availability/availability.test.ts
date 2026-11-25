import { describe, expect, it } from 'vitest';
import {
  AVAILABILITY_TEMPLATES,
  availabilityFromWeek,
  emptyAvailability,
  findGaps,
  groupByDay,
  hasBlockingErrors,
  isValidDate,
  suggestNextSlot,
  toCalendarDate,
  validateAvailability,
  weeklyHours,
  workingDays,
  type DoctorAvailability,
} from './index';

const availability = (changes: Partial<DoctorAvailability>): DoctorAvailability => ({
  ...emptyAvailability(),
  ...changes,
});
const types = (changes: Partial<DoctorAvailability>) =>
  validateAvailability(availability(changes)).map((error) => error.type);

describe('validateAvailability', () => {
  it('accepts every shipped template', () => {
    for (const { weeklySchedule } of AVAILABILITY_TEMPLATES) expect(types({ weeklySchedule })).toEqual([]);
  });

  it('points an overlap at the later slot of that day', () => {
    const errors = validateAvailability(
      availability({
        weeklySchedule: [
          { day: 1, start: '09:00', end: '12:00' },
          { day: 1, start: '11:59', end: '14:00' },
        ],
      }),
    );
    expect(errors).toMatchObject([{ type: 'overlap', day: 1, slotIndex: 1 }]);
  });

  it('lets slots touch, and lets different days share hours', () => {
    expect(
      types({
        weeklySchedule: [
          { day: 1, start: '09:00', end: '12:00' },
          { day: 1, start: '12:00', end: '14:00' },
          { day: 2, start: '09:00', end: '12:00' },
        ],
      }),
    ).toEqual([]);
  });

  it.each([
    ['9:00', '12:00', 'invalid_time'],
    ['09:00', '24:00', 'invalid_time'],
    ['', '12:00', 'invalid_time'],
    ['12:00', '12:00', 'end_before_start'],
  ])('rejects %s-%s as %s', (start, end, type) => {
    expect(types({ weeklySchedule: [{ day: 1, start, end }] })).toEqual([type]);
  });

  it('requires hours on an open override and a real, unique date', () => {
    expect(types({ overrides: [{ date: '2026-12-24', fullDayClosed: false }] })).toEqual(['invalid_time']);
    expect(types({ overrides: [{ date: '2026-02-31', fullDayClosed: true }] })).toEqual(['invalid_time']);
    expect(
      types({
        overrides: [
          { date: '2026-12-25', fullDayClosed: true },
          { date: '2026-12-25', fullDayClosed: true },
        ],
      }),
    ).toEqual(['duplicate_date']);
  });

  it('treats half a break as a warning and a reversed break as an error', () => {
    const half = validateAvailability(availability({ rules: { breakStart: '13:00' } }));
    expect(half).toMatchObject([{ severity: 'warning' }]);
    expect(hasBlockingErrors(half)).toBe(false);
    expect(hasBlockingErrors(validateAvailability(availability({ rules: { breakStart: '14:00', breakEnd: '13:00' } })))).toBe(true);
  });

  it('bounds the numeric rules', () => {
    expect(types({ rules: { minSlotDuration: 4 } })).toEqual(['invalid_time']);
    expect(types({ rules: { maxPatientsPerHour: 0 } })).toEqual(['invalid_time']);
  });
});

describe('the week being edited', () => {
  it('round-trips, sorting each day and dropping the days switched off', () => {
    const week = groupByDay([
      { day: 1, start: '16:00', end: '20:00' },
      { day: 1, start: '09:00', end: '13:00' },
      { day: 2, start: '09:00', end: '13:00' },
    ]);
    week[2].isWorking = false;
    expect(availabilityFromWeek(week, [], {}).weeklySchedule).toEqual([
      { day: 1, start: '09:00', end: '13:00' },
      { day: 1, start: '16:00', end: '20:00' },
    ]);
  });

  it('suggests a slot after the last one, stops at midnight and gives up without room', () => {
    const after = (end: string) => suggestNextSlot(1, [{ day: 1, start: '08:00', end }]);
    expect(suggestNextSlot(1, [])).toEqual({ day: 1, start: '09:00', end: '18:00' });
    expect(after('13:00')).toEqual({ day: 1, start: '14:00', end: '18:00' });
    expect(after('21:00')).toEqual({ day: 1, start: '22:00', end: '23:59' });
    expect(after('22:45')).toBeNull();
    expect(after('')).toBeNull();
  });

  it('measures the week', () => {
    const split = availability({ weeklySchedule: AVAILABILITY_TEMPLATES[3].weeklySchedule });
    expect(weeklyHours(split)).toBe(40);
    expect(workingDays(split)).toEqual([1, 2, 3, 4, 5]);
    expect(findGaps(split.weeklySchedule)[0]).toEqual({ day: 1, from: '13:00', to: '16:00' });
  });
});

describe('dates', () => {
  it('rejects days that do not exist', () => {
    expect(isValidDate('2028-02-29')).toBe(true);
    expect(isValidDate('2026-02-29')).toBe(false);
    expect(isValidDate('2026-2-9')).toBe(false);
  });

  it('reads the local day even late in the evening', () => {
    expect(toCalendarDate(new Date(2026, 10, 25, 23, 30))).toBe('2026-11-25');
  });
});
