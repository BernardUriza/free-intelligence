/**
 * DoctorAppointmentsCalendar
 *
 * FullCalendar-based component for doctor's appointment view.
 * Supports clicking on appointments and empty slots.
 */

'use client';

import { useRef, useMemo, useCallback } from 'react';
import FullCalendar from '@fullcalendar/react';
import timeGridPlugin from '@fullcalendar/timegrid';
import dayGridPlugin from '@fullcalendar/daygrid';
import interactionPlugin from '@fullcalendar/interaction';
import type { EventClickArg, DateClickArg } from '@fullcalendar/interaction';
import type { Appointment } from '@/types/checkin';
import type { DoctorAvailability } from '@/components/admin/clinics/availability-designer/types';
import { ChevronLeft, ChevronRight, Calendar, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  TIME_SLOT_PRESETS,
  THEME_PRESETS,
  TIME_FORMAT,
  DAY_HEADER_FORMAT,
  SLOT_LABEL_FORMAT,
} from '@/components/fullcalendar/config/calendar-presets.config';

// ============================================================================
// Types
// ============================================================================

interface DoctorAppointmentsCalendarProps {
  appointments: Appointment[];
  currentDate: Date;
  onDateChange: (date: Date) => void;
  onSelectAppointment: (appointment: Appointment) => void;
  onCreateAppointment: (date: Date) => void;
  loading?: boolean;
  /** Doctor's availability - used to show unavailable blocks */
  availability?: DoctorAvailability | null;
}

// Appointment status colors
const STATUS_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  scheduled: {
    bg: 'rgba(59, 130, 246, 0.3)',    // blue
    border: 'rgba(59, 130, 246, 0.6)',
    text: '#93c5fd',
  },
  confirmed: {
    bg: 'rgba(16, 185, 129, 0.3)',    // green
    border: 'rgba(16, 185, 129, 0.6)',
    text: '#6ee7b7',
  },
  checked_in: {
    bg: 'rgba(245, 158, 11, 0.3)',    // amber
    border: 'rgba(245, 158, 11, 0.6)',
    text: '#fcd34d',
  },
  in_progress: {
    bg: 'rgba(139, 92, 246, 0.3)',    // violet
    border: 'rgba(139, 92, 246, 0.6)',
    text: '#c4b5fd',
  },
  completed: {
    bg: 'rgba(100, 116, 139, 0.2)',   // slate
    border: 'rgba(100, 116, 139, 0.4)',
    text: '#94a3b8',
  },
  cancelled: {
    bg: 'rgba(239, 68, 68, 0.2)',     // red
    border: 'rgba(239, 68, 68, 0.4)',
    text: '#fca5a5',
  },
  no_show: {
    bg: 'rgba(239, 68, 68, 0.2)',
    border: 'rgba(239, 68, 68, 0.4)',
    text: '#fca5a5',
  },
};

// ============================================================================
// Component
// ============================================================================

export function DoctorAppointmentsCalendar({
  appointments,
  currentDate,
  onDateChange,
  onSelectAppointment,
  onCreateAppointment,
  loading = false,
  availability,
}: DoctorAppointmentsCalendarProps) {
  const calendarRef = useRef<FullCalendar>(null);

  // Transform weeklySchedule to FullCalendar businessHours format
  const businessHours = useMemo(() => {
    if (!availability?.weeklySchedule?.length) {
      // Default: Mon-Fri 9-18 if no availability defined
      return {
        daysOfWeek: [1, 2, 3, 4, 5],
        startTime: '09:00',
        endTime: '18:00',
      };
    }

    // Group slots by day and create businessHours array
    return availability.weeklySchedule.map((slot) => ({
      daysOfWeek: [slot.day],
      startTime: slot.start,
      endTime: slot.end,
    }));
  }, [availability?.weeklySchedule]);

  // Generate closed day events from overrides
  const closedDayEvents = useMemo(() => {
    if (!availability?.overrides?.length) return [];

    return availability.overrides
      .filter((override) => override.fullDayClosed)
      .map((override) => ({
        id: `closed-${override.date}`,
        start: override.date,
        allDay: true,
        display: 'background' as const,
        backgroundColor: 'rgba(239, 68, 68, 0.15)',
        borderColor: 'transparent',
        extendedProps: {
          type: 'closed',
          reason: override.reason || 'No disponible',
        },
      }));
  }, [availability?.overrides]);

  // Transform appointments to FullCalendar events
  const appointmentEvents = useMemo(() => {
    return appointments.map((apt) => {
      const colors = STATUS_COLORS[apt.status] || STATUS_COLORS.scheduled;
      const startDate = new Date(apt.scheduled_at);
      const endDate = new Date(startDate.getTime() + apt.estimated_duration * 60000);

      return {
        id: apt.appointment_id,
        title: apt.reason || 'Consulta',
        start: startDate,
        end: endDate,
        backgroundColor: colors.bg,
        borderColor: colors.border,
        textColor: colors.text,
        extendedProps: { appointment: apt },
      };
    });
  }, [appointments]);

  // Combine appointment events with closed day events
  const events = useMemo(() => {
    return [...appointmentEvents, ...closedDayEvents];
  }, [appointmentEvents, closedDayEvents]);

  // Navigation handlers
  const goToToday = useCallback(() => {
    calendarRef.current?.getApi().today();
    onDateChange(new Date());
  }, [onDateChange]);

  const goToPrev = useCallback(() => {
    const api = calendarRef.current?.getApi();
    if (api) {
      api.prev();
      onDateChange(api.getDate());
    }
  }, [onDateChange]);

  const goToNext = useCallback(() => {
    const api = calendarRef.current?.getApi();
    if (api) {
      api.next();
      onDateChange(api.getDate());
    }
  }, [onDateChange]);

  // Event click handler
  const handleEventClick = useCallback(
    (info: EventClickArg) => {
      const appointment = info.event.extendedProps.appointment as Appointment;
      if (appointment) {
        onSelectAppointment(appointment);
      }
    },
    [onSelectAppointment]
  );

  // Date click handler (empty slot)
  const handleDateClick = useCallback(
    (info: DateClickArg) => {
      onCreateAppointment(info.date);
    },
    [onCreateAppointment]
  );

  // Theme config
  const themeConfig = THEME_PRESETS.dark;
  const timeConfig = TIME_SLOT_PRESETS.clinic;

  return (
    <div className="flex flex-col h-full">
      {/* Header with navigation */}
      <div className="flex items-center justify-between mb-4 px-2">
        <div className="flex items-center gap-2">
          <Calendar className="w-5 h-5 text-slate-400" />
          <h2 className="text-lg font-semibold text-white">Mis Citas</h2>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={goToPrev}
            disabled={loading}
          >
            <ChevronLeft className="w-4 h-4" />
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={goToToday}
            disabled={loading}
          >
            Hoy
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={goToNext}
            disabled={loading}
          >
            <ChevronRight className="w-4 h-4" />
          </Button>
        </div>

        <Button
          variant="primary"
          size="sm"
          onClick={() => onCreateAppointment(new Date())}
          icon={Plus}
        >
          Nueva Cita
        </Button>
      </div>

      {/* Loading overlay */}
      {loading && (
        <div className="absolute inset-0 bg-slate-900/50 z-10 flex items-center justify-center rounded-lg">
          <div className="animate-spin w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full" />
        </div>
      )}

      {/* Calendar */}
      <div className="flex-1 relative fc-dark-theme">
        <FullCalendar
          ref={calendarRef}
          plugins={[timeGridPlugin, dayGridPlugin, interactionPlugin]}
          initialView="timeGridWeek"
          initialDate={currentDate}
          locale="es"
          headerToolbar={false}
          height="100%"
          slotMinTime={timeConfig.minTime}
          slotMaxTime={timeConfig.maxTime}
          slotDuration={timeConfig.slotDuration}
          slotLabelInterval={timeConfig.slotLabelInterval}
          slotLabelFormat={SLOT_LABEL_FORMAT.simple}
          dayHeaderFormat={DAY_HEADER_FORMAT.medium}
          allDaySlot={false}
          nowIndicator={true}
          events={events}
          eventDisplay="block"
          displayEventTime={true}
          displayEventEnd={false}
          eventTimeFormat={TIME_FORMAT.h24}
          selectable={false}
          editable={false}
          eventClick={handleEventClick}
          dateClick={handleDateClick}
          businessHours={businessHours}
        />

        {/* Theme Styles */}
        <style jsx global>{`
          .fc-dark-theme {
            --fc-border-color: ${themeConfig.borderColor};
            --fc-page-bg-color: ${themeConfig.pageBgColor};
            --fc-neutral-bg-color: ${themeConfig.neutralBgColor};
            --fc-today-bg-color: ${themeConfig.todayBgColor};
            --fc-now-indicator-color: ${themeConfig.nowIndicatorColor};
          }

          .fc-dark-theme .fc-scrollgrid {
            border-color: var(--fc-border-color);
          }

          .fc-dark-theme .fc-col-header-cell {
            background: rgb(30 41 59 / 0.5);
            border-color: var(--fc-border-color);
            padding: 8px 4px;
          }

          .fc-dark-theme .fc-col-header-cell-cushion {
            color: rgb(148 163 184);
            font-weight: 500;
            font-size: 0.75rem;
          }

          .fc-dark-theme .fc-day-today .fc-col-header-cell-cushion {
            color: rgb(165 180 252);
          }

          .fc-dark-theme .fc-timegrid-slot {
            border-color: var(--fc-border-color);
            height: 24px;
          }

          .fc-dark-theme .fc-timegrid-slot-label-cushion {
            color: rgb(100 116 139);
            font-size: 0.7rem;
          }

          .fc-dark-theme .fc-timegrid-col {
            border-color: var(--fc-border-color);
          }

          .fc-dark-theme .fc-timegrid-now-indicator-line {
            border-color: var(--fc-now-indicator-color);
            border-width: 2px;
          }

          .fc-dark-theme .fc-timegrid-now-indicator-arrow {
            border-color: var(--fc-now-indicator-color);
            border-top-color: transparent;
            border-bottom-color: transparent;
          }

          .fc-dark-theme .fc-event {
            border-radius: 4px;
            font-size: 0.75rem;
            padding: 2px 4px;
            cursor: pointer;
          }

          .fc-dark-theme .fc-event:hover {
            opacity: 0.9;
            transform: scale(1.02);
            transition: all 0.15s ease;
          }

          .fc-dark-theme .fc-event-title {
            font-weight: 500;
          }

          .fc-dark-theme .fc-timegrid-event-harness {
            margin: 0 2px;
          }

          .fc-dark-theme .fc-day-today {
            background: var(--fc-today-bg-color) !important;
          }

          .fc-dark-theme .fc-scrollgrid-sync-inner {
            padding: 4px;
          }

          /* Clickable empty slots */
          .fc-dark-theme .fc-timegrid-slot-lane {
            cursor: pointer;
          }

          .fc-dark-theme .fc-timegrid-slot-lane:hover {
            background: rgba(99, 102, 241, 0.1);
          }

          /* Non-business hours (unavailable) - striped pattern */
          .fc-dark-theme .fc-non-business {
            background: repeating-linear-gradient(
              -45deg,
              rgba(100, 116, 139, 0.08),
              rgba(100, 116, 139, 0.08) 4px,
              rgba(100, 116, 139, 0.15) 4px,
              rgba(100, 116, 139, 0.15) 8px
            ) !important;
          }

          /* Closed day background events */
          .fc-dark-theme .fc-bg-event {
            opacity: 1;
          }
        `}</style>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 mt-3 px-2 text-xs text-slate-400 flex-wrap">
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded" style={{ background: STATUS_COLORS.scheduled.bg, border: `1px solid ${STATUS_COLORS.scheduled.border}` }} />
          <span>Programada</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded" style={{ background: STATUS_COLORS.checked_in.bg, border: `1px solid ${STATUS_COLORS.checked_in.border}` }} />
          <span>Check-in</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded" style={{ background: STATUS_COLORS.in_progress.bg, border: `1px solid ${STATUS_COLORS.in_progress.border}` }} />
          <span>En consulta</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded" style={{ background: STATUS_COLORS.completed.bg, border: `1px solid ${STATUS_COLORS.completed.border}` }} />
          <span>Completada</span>
        </div>
        <div className="flex items-center gap-1">
          <div
            className="w-3 h-3 rounded"
            style={{
              background: 'repeating-linear-gradient(-45deg, rgba(100, 116, 139, 0.2), rgba(100, 116, 139, 0.2) 2px, rgba(100, 116, 139, 0.4) 2px, rgba(100, 116, 139, 0.4) 4px)',
              border: '1px solid rgba(100, 116, 139, 0.4)',
            }}
          />
          <span>No disponible</span>
        </div>
      </div>
    </div>
  );
}
