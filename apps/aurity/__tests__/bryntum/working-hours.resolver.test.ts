import { describe, it, expect, beforeEach } from 'vitest';
import { TemporalAPI } from '@/lib/temporal';
import { resolveWorkingDay, zonedToDate } from '@/components/bryntum/utils/working-hours.resolver';
import type { Doctor } from '@/components/bryntum/utils/appointment-transform.utils';

const Temporal = TemporalAPI;

describe('working-hours resolver', () => {
  beforeEach(() => {
    process.env.CLINIC_TZ = 'America/Mexico_City';
  });

  it('merges overlapping or touching weekly slots into canonical windows', () => {
    const doctor: Doctor = {
      doctor_id: 'doc-merge',
      nombre: 'Merge',
      apellido: 'Tester',
      display_name: null,
      especialidad: null,
      avg_consultation_minutes: 30,
      work_start_time: null,
      work_end_time: null,
      working_hours: [
        { day: 1, start: '09:00', end: '13:00' },
        { day: 1, start: '13:00', end: '17:00' },
      ],
    };

    const date = Temporal.PlainDate.from('2025-01-06'); // Monday
    const result = resolveWorkingDay(doctor, date);

    expect(result.mergesApplied).toBe(true);
    expect(result.windows).toHaveLength(1);
    const minutes = (result.windows[0].end.epochMilliseconds - result.windows[0].start.epochMilliseconds) / (1000 * 60);
    expect(minutes).toBe(8 * 60);
    expect(result.nonWorking).toHaveLength(2);
  });

  it('returns full-day off when date override is closed', () => {
    const doctor: Doctor = {
      doctor_id: 'doc-closed',
      nombre: 'Closed',
      apellido: 'Override',
      display_name: null,
      especialidad: null,
      avg_consultation_minutes: 30,
      work_start_time: '08:00',
      work_end_time: '16:00',
      working_hours: [
        { date: '2025-01-07', day: 2, start: '', end: '', fullDayClosed: true },
      ],
    };

    const date = Temporal.PlainDate.from('2025-01-07');
    const result = resolveWorkingDay(doctor, date);

    expect(result.fullDayOff).toBe(true);
    expect(result.windows).toHaveLength(0);
    expect(result.nonWorking).toHaveLength(1);
    const [range] = result.nonWorking;
    expect(zonedToDate(range.start).getTime()).toBeLessThan(zonedToDate(range.end).getTime());
  });

  it('falls back to legacy bounds with legacyDerived flag', () => {
    const doctor: Doctor = {
      doctor_id: 'doc-legacy',
      nombre: 'Legacy',
      apellido: 'Bounds',
      display_name: null,
      especialidad: null,
      avg_consultation_minutes: 30,
      work_start_time: '08:00',
      work_end_time: '16:00',
      working_hours: [],
    };

    const date = Temporal.PlainDate.from('2025-01-08');
    const result = resolveWorkingDay(doctor, date);

    expect(result.windows).toHaveLength(1);
    expect(result.windows[0].legacyDerived).toBe(true);
    expect(result.nonWorking).toHaveLength(2);
  });

  it('handles cross-midnight shifts with spillover into next day', () => {
    const doctor: Doctor = {
      doctor_id: 'doc-overnight',
      nombre: 'Night',
      apellido: 'Shift',
      display_name: null,
      especialidad: null,
      avg_consultation_minutes: 30,
      work_start_time: null,
      work_end_time: null,
      working_hours: [{ day: 3, start: '22:00', end: '02:00' }],
    };

    const wednesday = Temporal.PlainDate.from('2025-01-08'); // Wednesday
    const first = resolveWorkingDay(doctor, wednesday);
    expect(first.windows).toHaveLength(1);
    expect(first.spilloverNext).toHaveLength(1);

    const thursday = Temporal.PlainDate.from('2025-01-09');
    const second = resolveWorkingDay(doctor, thursday, process.env.CLINIC_TZ, first.spilloverNext);
    expect(second.windows.some((w) => w.start.hour === 0 && w.end.hour === 2)).toBe(true);
  });

  it('respects DST transitions when computing durations', () => {
    process.env.CLINIC_TZ = 'America/New_York';
    const doctor: Doctor = {
      doctor_id: 'doc-dst',
      nombre: 'DST',
      apellido: 'Aware',
      display_name: null,
      especialidad: null,
      avg_consultation_minutes: 30,
      work_start_time: null,
      work_end_time: null,
      working_hours: [{ day: 0, start: '01:00', end: '04:00' }],
    };

    const springForward = Temporal.PlainDate.from('2025-03-09'); // DST starts in US
    const result = resolveWorkingDay(doctor, springForward, process.env.CLINIC_TZ);

    expect(result.windows).toHaveLength(1);
    const durationHours = (result.windows[0].end.epochMilliseconds - result.windows[0].start.epochMilliseconds) / (1000 * 60 * 60);
    expect(durationHours).toBeCloseTo(3, 1);
  });
});
