/**
 * Bryntum Config Builders - Pure Functions
 *
 * Factory functions for building Bryntum SchedulerPro configurations.
 * No I/O, no side effects, fully testable.
 *
 * Exports:
 * - buildTimelineSchedulerConfig (for Timeline view)
 * - buildAppointmentSchedulerConfig (for Appointments calendar)
 *
 * Card: FI-BRYNTUM-UNIFY-001
 * Created: 2025-12-11
 * Updated: 2025-12-29 - Temporal API fix, cleanup console.logs, type safety
 */

const IS_DEV = process.env.NODE_ENV === 'development';

// Timeline imports
import { VIEW_PRESETS } from '../config/timeline-presets.config';
import { TIMELINE_RESOURCES } from '../config/timeline-resources.config';
import { TIMELINE_COLUMNS } from '../config/timeline-columns.config';
import { TIMELINE_FEATURES } from '../features/timeline-features.config';
import { transformEvents } from '../utils/event-transform.utils';
import type { ViewMode, UnifiedEvent } from '../types/scheduler.types';

// Appointments imports
import { APPOINTMENT_VIEW_PRESETS, type AppointmentViewMode } from '../config/appointment-presets.config';
import { APPOINTMENT_FEATURES } from '../config/appointment-features.config';
import { APPOINTMENT_COLUMNS } from '../config/appointment-columns.config';
import { appointmentEventRenderer } from '../renderers/appointmentEventRenderer.fn';
import {
  transformDoctors,
  transformAppointments,
  type Doctor,
  type Appointment,
} from '../utils/appointment-transform.utils';
import { resolveWorkingDay, zonedToDate, isDateInWorkingHours } from '../utils/working-hours.resolver';
import { generateBlockedTimeEvents, isBlockedTimeEvent } from '../utils/blocked-time-events';
import { TemporalAPI, getClinicTimeZone } from '@/lib/temporal';
import type { BryntumSchedulerConfig } from '../types/scheduler.types';

const Temporal = TemporalAPI;

// ============================================================================
// Shared Utilities
// ============================================================================

/** Calculate duration in minutes between two dates */
const getDurationMinutes = (start: Date, end: Date): number =>
  Math.round((end.getTime() - start.getTime()) / 60_000);

// ============================================================================
// Timeline Scheduler Config
// ============================================================================

interface TimelineSchedulerParams {
  viewMode: ViewMode;
  currentDate: Date;
  events: UnifiedEvent[];
  onEventClick?: (event: UnifiedEvent) => void;
}

/**
 * Build Timeline Scheduler Configuration
 * 
 * Pure function for timeline memory view.
 * - 2 resource rows (Chat, Audio)
 * - Read-only (no DnD, no resize, no edit)
 * - Custom tooltip with event details
 * - rowHeight: 60, subGridConfigs with locked resource column
 * 
 * @param params - View state and callbacks
 * @returns Complete Bryntum config object
 */
export function buildTimelineSchedulerConfig({
  viewMode,
  currentDate,
  events,
  onEventClick,
}: TimelineSchedulerParams): BryntumSchedulerConfig {
  const viewConfig = VIEW_PRESETS[viewMode];
  const { start, end } = viewConfig.getDateRange(currentDate);

  return {
    // Time axis
    startDate: start,
    endDate: end,
    viewPreset: viewConfig.preset,

    // Layout
    rowHeight: 60,
    barMargin: 4,
    
    // Grid: locked resource column + flexible timeline
    subGridConfigs: {
      locked: {
        width: 200,
        flex: 0,
      },
      normal: {
        flex: 1,
      },
    },

    // Data
    resources: TIMELINE_RESOURCES,
    events: transformEvents(events),
    columns: TIMELINE_COLUMNS,

    // Features (read-only)
    features: TIMELINE_FEATURES,

    // Custom renderer - returns DomConfig for WC bundle compatibility
    eventRenderer: appointmentEventRenderer,

    listeners: {
      eventClick: onEventClick
        ? ({ eventRecord }: { eventRecord: { data: Record<string, unknown> } }) => {
            const originalEvent = eventRecord.data.originalEvent as UnifiedEvent;
            if (originalEvent) {
              onEventClick(originalEvent);
            }
          }
        : undefined,
    },
  };
}

// ============================================================================
// Appointment Scheduler Config
// ============================================================================

interface AppointmentSchedulerParams {
  viewMode: AppointmentViewMode;
  currentDate: Date;
  doctors: Doctor[];
  appointments: Appointment[];
  onEventDrop?: (eventData: {
    appointment_id: string;
    scheduled_at: string;
    doctor_id: string;
  }) => Promise<void>;
  onEventResize?: (eventData: {
    appointment_id: string;
    estimated_duration: number;
  }) => Promise<void>;
  onEventEdit?: (eventData: {
    appointment_id: string;
    scheduled_at?: string;
    estimated_duration?: number;
    doctor_id?: string;
    status?: string;
    reason?: string;
    notes?: string;
  }) => Promise<void>;
  onEventClick?: (appointment: Appointment) => void;
  onScheduleClick?: (date: Date, doctorId: string, endDate?: Date | null) => void;
  /** Skip initial timeRanges generation (use virtualized hook instead) */
  skipTimeRanges?: boolean;
}

/**
 * Build Appointment Scheduler Configuration
 * 
 * Pure function for appointments calendar view.
 * - Resources = doctors, Events = appointments
 * - Editable: DnD, resize, edit via modal
 * - Async finalize pattern for API calls
 * - eventEdit: false (use custom modal)
 * - rowHeight: 60, consistent with timeline
 * 
 * @param params - View state and API callbacks
 * @returns Complete Bryntum config object
 */
export function buildAppointmentSchedulerConfig({
  viewMode,
  currentDate,
  doctors,
  appointments,
  onEventDrop,
  onEventResize,
  onEventEdit,
  onEventClick,
  onScheduleClick,
  skipTimeRanges = false,
}: AppointmentSchedulerParams): BryntumSchedulerConfig {
  const viewConfig = APPOINTMENT_VIEW_PRESETS[viewMode];
  const { start, end } = viewConfig.getDateRange(currentDate);

  // WORKAROUND: Generate blocked time as regular events (CSS/JS version mismatch)
  // ResourceTimeRanges don't render correctly due to canvas positioning issues
  // between CSS v6.0.0-alpha-1 and JS v5.6.6. Using regular events instead.
  const blockedTimeEvents = skipTimeRanges ? [] : generateBlockedTimeEvents(doctors, start, end);
  const appointmentEvents = transformAppointments(appointments);

  // Combine appointments with blocked time events
  // Blocked events render as gray stripes in non-working hours
  const allEvents = [...appointmentEvents, ...blockedTimeEvents];

  return {
    // Time axis
    startDate: start,
    endDate: end,
    viewPreset: viewConfig.preset,

    // Center the view on the current date (today), not the start date (yesterday)
    visibleDate: currentDate,

    // Layout - taller rows for appointment cards with patient info
    rowHeight: 200,
    barMargin: 5,

    // Grid: locked resource column + flexible timeline
    subGridConfigs: {
      locked: {
        width: 280,
        minWidth: 280,
        flex: 0,
        collapsed: false,
      },
      normal: {
        flex: 1,
      },
    },

    // Data
    resources: transformDoctors(doctors),
    events: allEvents,
    // Disabled: ResourceTimeRanges don't work due to CSS/JS mismatch
    // resourceTimeRangesData: resourceTimeRanges,
    columns: APPOINTMENT_COLUMNS,
    // Custom event renderer using React component via adapter
    eventRenderer: appointmentEventRenderer,

    // Features (editable, but no native editor)
    features: {
      ...APPOINTMENT_FEATURES,
      eventEdit: false, // CRITICAL: use custom modal
      scheduleTooltip: false, // Disable schedule tooltip that shows on hover
    },

    // Allow event creation
    readOnly: false,
    allowOverlap: true,

    // Zoom restrictions - prevent zooming beyond day/week views
    // These are top-level config properties, not features
    zoomOnMouseWheel: false,
    zoomOnTimeAxisDoubleClick: false,
    zoomKeepsOriginalTimespan: true, // Keep the same timespan when view changes
    // Zoom level limits: 0=finest (minutes), 23=coarsest (years)
    // For medical scheduler: min=5 (30min slots), max=14 (week view)
    minZoomLevel: 5,
    maxZoomLevel: 14,
    
    // Event listeners with async finalize pattern
    // Note: Type assertion needed because Bryntum's SchedulerListeners type is incomplete
    // and doesn't include dragCreateEnd, but the event is valid at runtime
    listeners: {
      // VALIDATION: Block drag-create in non-working hours
      // Returning false prevents the drag create operation from starting
      beforeDragCreate: ({ date, resourceRecord }: { date: Date; resourceRecord: { id: string } }) => {
        const doctor = doctors.find((d) => d.doctor_id === resourceRecord.id);
        if (!doctor) {
          return false; // Block if doctor not found
        }
        const isAllowed = isDateInWorkingHours(doctor, date);
        if (!isAllowed) {
          console.log(`[Bryntum] Blocked drag-create at ${date.toISOString()} - outside working hours for ${doctor.display_name || doctor.nombre}`);
        }
        return isAllowed;
      },

      // CRITICAL: Intercept drag-created events to open custom modal
      dragCreateEnd: ({ eventRecord, resourceRecord }: { eventRecord: { startDate: Date; endDate: Date; eventStore: { remove: (record: unknown) => void } }; resourceRecord: { id: string } }) => {
        if (onScheduleClick) {
          const startDate = eventRecord.startDate;
          const endDate = eventRecord.endDate;
          const doctorId = resourceRecord.id;

          // Remove the temporary event immediately
          eventRecord.eventStore.remove(eventRecord);

          // Open modal with the drawn time range (start and end)
          onScheduleClick(startDate, doctorId, endDate);
        }
      },

      // VALIDATION: Block event drop in non-working hours
      // context.valid = false aborts the drop immediately
      beforeEventDropFinalize: ({ context }: {
        context: {
          valid: boolean;
          eventRecords: { startDate: Date; id: string }[];
          newResource?: { id: string };
        }
      }) => {
        const targetDoctorId = context.newResource?.id;
        if (!targetDoctorId) {
          return; // No resource change, allow
        }
        const doctor = doctors.find((d) => d.doctor_id === targetDoctorId);
        if (!doctor) {
          context.valid = false;
          return;
        }
        // Check all dragged events
        for (const eventRecord of context.eventRecords) {
          // Skip blocked time events (shouldn't be draggable anyway)
          if (typeof eventRecord.id === 'string' && eventRecord.id.startsWith('blocked-')) {
            continue;
          }
          const isAllowed = isDateInWorkingHours(doctor, eventRecord.startDate);
          if (!isAllowed) {
            console.log(`[Bryntum] Blocked event drop at ${eventRecord.startDate.toISOString()} - outside working hours for ${doctor.display_name || doctor.nombre}`);
            context.valid = false;
            return;
          }
        }
      },

      // Drag & Drop
      eventDrop: onEventDrop
        ? async ({ context, eventRecord, newResource }: { context: { async: boolean; finalize: (success: boolean) => void }; eventRecord: { id: string; startDate: Date; resourceId: string }; newResource?: { id: string } }) => {
            context.async = true;
            try {
              await onEventDrop({
                appointment_id: eventRecord.id,
                scheduled_at: eventRecord.startDate.toISOString(),
                doctor_id: newResource?.id || eventRecord.resourceId,
              });
              context.finalize(true);
            } catch (error) {
              console.error('[Bryntum] Drop failed:', error);
              context.finalize(false);
            }
          }
        : undefined,

      // Resize
      eventResizeEnd: onEventResize
        ? async ({ context, eventRecord }: { context: { async: boolean; finalize: (success: boolean) => void }; eventRecord: { id: string; startDate: Date; endDate: Date } }) => {
            context.async = true;
            try {
              await onEventResize({
                appointment_id: eventRecord.id,
                estimated_duration: getDurationMinutes(eventRecord.startDate, eventRecord.endDate),
              });
              context.finalize(true);
            } catch (error) {
              console.error('[Bryntum] Resize failed:', error);
              context.finalize(false);
            }
          }
        : undefined,

      // Edit (via custom modal, not Bryntum editor)
      afterEventEdit: onEventEdit
        ? async ({ eventRecord }: { eventRecord: unknown }) => {
            const record = eventRecord as { id: string; startDate?: Date; endDate?: Date; resourceId: string };
            try {
              await onEventEdit({
                appointment_id: record.id,
                scheduled_at: record.startDate?.toISOString(),
                estimated_duration: record.startDate && record.endDate
                  ? getDurationMinutes(record.startDate, record.endDate)
                  : 0,
                doctor_id: record.resourceId,
              });
            } catch (error) {
              console.error('[Bryntum] Edit failed:', error);
            }
          }
        : undefined,

      // Click (open custom modal)
      eventClick: onEventClick
        ? ({ eventRecord }: { eventRecord: { data: Record<string, unknown> } }) => {
            const data = eventRecord.data;

            // Skip blocked time events (non-working hours)
            if (isBlockedTimeEvent(data)) {
              return;
            }

            // Find original appointment data
            const appointment = appointments.find(
              (apt) => apt.appointment_id === (data as { id: string }).id
            );

            if (appointment) {
              onEventClick(appointment);
            }
          }
        : undefined,

      // Schedule click (create new appointment at clicked time/doctor)
      scheduleClick: onScheduleClick
        ? ({ date, resourceRecord }: { date: Date; resourceRecord: unknown }) => {
            const resource = resourceRecord as { id: string };
            if (!resource || !date) return;

            // Block clicks on non-working hours (gray zones)
            const doctor = doctors.find((d) => d.doctor_id === resource.id);
            if (!doctor) return;

            const isAllowed = isDateInWorkingHours(doctor, date);
            if (!isAllowed) {
              if (IS_DEV) {
                console.log(`[Bryntum] Blocked schedule click at ${date.toISOString()} - outside working hours`);
              }
              return; // Don't open modal for non-working hours
            }

            // Simple click: no end date (user will set duration manually)
            onScheduleClick(date, resource.id, null);
          }
        : undefined,
    // Type assertion: Bryntum's SchedulerListeners doesn't include all valid events like dragCreateEnd
    } as Record<string, unknown>,
  };
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Generate non-working time ranges for each doctor based on their work hours
 * 
 * Creates time range records that mark hours outside work_start_time and work_end_time
 * as disabled/non-working in the scheduler.
 * 
 * @param doctors - Array of doctors with work hours
 * @param startDate - Scheduler start date
 * @param endDate - Scheduler end date
 * @returns Array of Bryntum resourceTimeRange records
 */
export interface NonWorkingTimeRange {
  id: string;
  resourceId: string;
  startDate: Date;
  endDate: Date;
  name: string;
  cls: string;
  style: string;  // Inline CSS for guaranteed rendering
}

function generateNonWorkingTimeRanges(
  doctors: Doctor[],
  startDate: Date,
  endDate: Date
): NonWorkingTimeRange[] {
  const ranges: NonWorkingTimeRange[] = [];
  const timeZone = getClinicTimeZone();
  // Use ZonedDateTime for calendar-aware date arithmetic (Instant doesn't support days)
  const startZoned = Temporal.Instant.from(startDate.toISOString()).toZonedDateTimeISO(timeZone);
  const endZoned = Temporal.Instant.from(endDate.toISOString()).toZonedDateTimeISO(timeZone);

  doctors.forEach((doctor) => {
    let cursor = startZoned;
    let spillover: ReturnType<typeof resolveWorkingDay>['spilloverNext'] = [];

    while (Temporal.ZonedDateTime.compare(cursor, endZoned) <= 0) {
      const date = cursor.toPlainDate();
      const resolution = resolveWorkingDay(doctor, date, timeZone, spillover);

      resolution.nonWorking.forEach((window, index) => {
        ranges.push({
          id: `${doctor.doctor_id}-nw-${resolution.dateISO}-${index}`,
          resourceId: doctor.doctor_id,
          startDate: zonedToDate(window.start),
          endDate: zonedToDate(window.end),
          name: 'No disponible',
          cls: 'non-working-time',
          // Inline style ensures visibility even if CSS file not loaded
          style: 'background: rgba(100, 116, 139, 0.4); background-image: repeating-linear-gradient(45deg, transparent, transparent 5px, rgba(148, 163, 184, 0.3) 5px, rgba(148, 163, 184, 0.3) 10px);',
        });
      });

      spillover = resolution.spilloverNext;
      cursor = cursor.add({ days: 1 });
    }
  });

  return ranges;
}

// ============================================================================
// Exports
// ============================================================================

export type {
  TimelineSchedulerParams,
  AppointmentSchedulerParams,
};
