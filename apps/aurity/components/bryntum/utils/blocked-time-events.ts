/**
 * Blocked Time Events Generator
 *
 * WORKAROUND for Bryntum CSS/JS version mismatch (CSS v6.0.0-alpha-1 vs JS v5.6.6)
 *
 * Instead of using ResourceTimeRanges (which renders off-screen due to canvas
 * positioning issues between versions), we create regular events styled as
 * blocked/non-working time slots.
 *
 * These events:
 * - Are non-draggable, non-resizable, non-editable
 * - Have gray striped appearance
 * - Don't respond to clicks
 * - Are filtered from appointment handlers
 *
 * Card: FI-BRYNTUM-CSS-001 (workaround)
 * Created: 2026-01-06
 */

import type { Doctor } from './appointment-transform.utils';
import { resolveWorkingDay, zonedToDate } from './working-hours.resolver';
import { TemporalAPI, getClinicTimeZone } from '@/lib/temporal';

const Temporal = TemporalAPI;

export interface BlockedTimeEvent {
  id: string;
  resourceId: string;
  startDate: Date;
  endDate: Date;
  name: string;
  cls: string;
  eventColor: string;
  draggable: false;
  resizable: false;
  editable: false;
  // Custom marker to identify blocked events
  isBlockedTime: true;
  // Index signature for Bryntum compatibility
  [key: string]: unknown;
}

/**
 * Generate blocked time events for non-working hours per doctor
 *
 * These are regular events that appear in the events array but are styled
 * to look like disabled/blocked time slots.
 *
 * @param doctors - Array of doctors with working hours
 * @param startDate - Scheduler visible start date
 * @param endDate - Scheduler visible end date
 * @returns Array of blocked time events
 */
export function generateBlockedTimeEvents(
  doctors: Doctor[],
  startDate: Date,
  endDate: Date
): BlockedTimeEvent[] {
  const events: BlockedTimeEvent[] = [];
  const timeZone = getClinicTimeZone();

  const startZoned = Temporal.Instant.from(startDate.toISOString()).toZonedDateTimeISO(timeZone);
  const endZoned = Temporal.Instant.from(endDate.toISOString()).toZonedDateTimeISO(timeZone);

  doctors.forEach((doctor) => {
    let cursor = startZoned;
    let spillover: ReturnType<typeof resolveWorkingDay>['spilloverNext'] = [];

    while (Temporal.ZonedDateTime.compare(cursor, endZoned) <= 0) {
      const date = cursor.toPlainDate();
      const resolution = resolveWorkingDay(doctor, date, timeZone, spillover);

      resolution.nonWorking.forEach((window, index) => {
        events.push({
          id: `blocked-${doctor.doctor_id}-${resolution.dateISO}-${index}`,
          resourceId: doctor.doctor_id,
          startDate: zonedToDate(window.start),
          endDate: zonedToDate(window.end),
          name: '', // No label - pure visual block
          cls: 'blocked-time-event',
          eventColor: 'gray',
          draggable: false,
          resizable: false,
          editable: false,
          isBlockedTime: true,
        });
      });

      spillover = resolution.spilloverNext;
      cursor = cursor.add({ days: 1 });
    }
  });

  return events;
}

/**
 * Check if an event record is a blocked time event
 * Use this to filter blocked events from click/edit handlers
 */
export function isBlockedTimeEvent(eventData: Record<string, unknown>): boolean {
  return eventData.isBlockedTime === true ||
         (typeof eventData.id === 'string' && eventData.id.startsWith('blocked-'));
}
