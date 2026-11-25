import { describe, expect, it } from 'vitest';
import { availabilityEvents, businessHours } from './availabilityEvents';

const monday = new Date(2026, 10, 23, 22, 30);
const schedule = {
  weeklySchedule: [
    { day: 1, start: '09:00', end: '13:00', label: 'Mañana' },
    { day: 1, start: '16:00', end: '20:00' },
    { day: 3, start: '09:00', end: '13:00' },
  ],
  overrides: [
    { date: '2026-11-25', fullDayClosed: true, reason: 'Congreso' },
    { date: '2026-11-26', fullDayClosed: false, start: '10:00', end: '11:00' },
  ],
};

describe('availabilityEvents', () => {
  const events = availabilityEvents(schedule, { from: monday, days: 4 });

  it('starts on the local day, even when the clock is past UTC midnight', () => {
    expect(events.slice(0, 2)).toMatchObject([
      { title: 'Mañana', start: '2026-11-23T09:00:00', end: '2026-11-23T13:00:00' },
      { title: 'Disponible', start: '2026-11-23T16:00:00' },
    ]);
  });

  it('marks free days, and lets an override replace that date', () => {
    expect(events.slice(2).map((event) => event.extendedProps)).toEqual([
      { kind: 'day-off', reason: undefined },
      { kind: 'closed', reason: 'Congreso' },
      { kind: 'override' },
    ]);
    expect(events[4]).toMatchObject({ title: 'Horario especial', classNames: ['fi-calendar-event--override'] });
  });

  it('gives every event its own id', () => {
    expect(new Set(events.map((event) => event.id)).size).toBe(events.length);
  });
});

it('businessHours follows the weekly pattern', () => {
  expect(businessHours(schedule.weeklySchedule)[2]).toEqual({ daysOfWeek: [3], startTime: '09:00', endTime: '13:00' });
});
