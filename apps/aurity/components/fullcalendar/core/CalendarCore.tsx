/**
 * CalendarCore - Reusable FullCalendar Component
 *
 * A pre-configured FullCalendar component with dark theme support
 * and sensible defaults for the Aurity design system.
 */

'use client';

import { forwardRef, useMemo } from 'react';
import FullCalendar from '@fullcalendar/react';
import timeGridPlugin from '@fullcalendar/timegrid';
import dayGridPlugin from '@fullcalendar/daygrid';
import type { CalendarCoreProps, CalendarEvent } from '../types/calendar.types';
import {
  TIME_SLOT_PRESETS,
  THEME_PRESETS,
  TIME_FORMAT,
  DAY_HEADER_FORMAT,
  SLOT_LABEL_FORMAT,
} from '../config/calendar-presets.config';

// ============================================================================
// Component Props with Defaults
// ============================================================================

interface CalendarCoreFullProps extends CalendarCoreProps {
  /** Theme preset name */
  theme?: 'dark' | 'light';
  /** Time slot preset name */
  timePreset?: 'business' | 'extended' | 'compact' | 'clinic';
}

// ============================================================================
// CalendarCore Component
// ============================================================================

/**
 * CalendarCore - Pre-styled FullCalendar component
 *
 * @example
 * ```tsx
 * <CalendarCore
 *   events={events}
 *   height={420}
 *   locale="es"
 *   theme="dark"
 * />
 * ```
 */
export const CalendarCore = forwardRef<FullCalendar, CalendarCoreFullProps>(
  function CalendarCore(
    {
      events = [],
      height = 420,
      initialView = 'timeGridWeek',
      locale = 'es',
      slotMinTime,
      slotMaxTime,
      nowIndicator = true,
      allDaySlot = false,
      className = '',
      onViewChange,
      onDatesSet,
      theme = 'dark',
      timePreset = 'business',
    },
    ref
  ) {
    // Get time slot config from preset or use custom values
    const timeConfig = useMemo(() => {
      const preset = TIME_SLOT_PRESETS[timePreset];
      return {
        minTime: slotMinTime ?? preset.minTime,
        maxTime: slotMaxTime ?? preset.maxTime,
        duration: preset.slotDuration,
        interval: preset.slotLabelInterval,
      };
    }, [timePreset, slotMinTime, slotMaxTime]);

    // Theme CSS variables
    const themeConfig = THEME_PRESETS[theme];

    // Container class name
    const containerClassName = `fc-${theme}-theme ${className}`.trim();

    return (
      <div className={containerClassName}>
        <FullCalendar
          ref={ref}
          plugins={[timeGridPlugin, dayGridPlugin]}
          initialView={initialView}
          locale={locale}
          headerToolbar={false}
          height={height}
          slotMinTime={timeConfig.minTime}
          slotMaxTime={timeConfig.maxTime}
          slotDuration={timeConfig.duration}
          slotLabelInterval={timeConfig.interval}
          slotLabelFormat={SLOT_LABEL_FORMAT.simple}
          dayHeaderFormat={DAY_HEADER_FORMAT.medium}
          allDaySlot={allDaySlot}
          nowIndicator={nowIndicator}
          events={events as CalendarEvent[]}
          eventDisplay="block"
          displayEventTime={true}
          displayEventEnd={false}
          eventTimeFormat={TIME_FORMAT.h24}
          datesSet={(dateInfo) => {
            onDatesSet?.(dateInfo.start, dateInfo.end);
          }}
          viewDidMount={(info) => {
            onViewChange?.(info.view.type);
          }}
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

          .fc-light-theme {
            --fc-border-color: ${THEME_PRESETS.light.borderColor};
            --fc-page-bg-color: ${THEME_PRESETS.light.pageBgColor};
            --fc-neutral-bg-color: ${THEME_PRESETS.light.neutralBgColor};
            --fc-today-bg-color: ${THEME_PRESETS.light.todayBgColor};
            --fc-now-indicator-color: ${THEME_PRESETS.light.nowIndicatorColor};
          }

          .fc-dark-theme .fc-scrollgrid,
          .fc-light-theme .fc-scrollgrid {
            border-color: var(--fc-border-color);
          }

          .fc-dark-theme .fc-col-header-cell {
            background: rgb(30 41 59 / 0.5);
            border-color: var(--fc-border-color);
            padding: 8px 4px;
          }

          .fc-light-theme .fc-col-header-cell {
            background: rgb(248 250 252);
            border-color: var(--fc-border-color);
            padding: 8px 4px;
          }

          .fc-dark-theme .fc-col-header-cell-cushion {
            color: rgb(148 163 184);
            font-weight: 500;
            font-size: 0.75rem;
          }

          .fc-light-theme .fc-col-header-cell-cushion {
            color: rgb(71 85 105);
            font-weight: 500;
            font-size: 0.75rem;
          }

          .fc-dark-theme .fc-day-today .fc-col-header-cell-cushion {
            color: rgb(165 180 252);
          }

          .fc-light-theme .fc-day-today .fc-col-header-cell-cushion {
            color: rgb(99 102 241);
          }

          .fc-dark-theme .fc-timegrid-slot,
          .fc-light-theme .fc-timegrid-slot {
            border-color: var(--fc-border-color);
            height: 24px;
          }

          .fc-dark-theme .fc-timegrid-slot-label-cushion {
            color: rgb(100 116 139);
            font-size: 0.7rem;
          }

          .fc-light-theme .fc-timegrid-slot-label-cushion {
            color: rgb(148 163 184);
            font-size: 0.7rem;
          }

          .fc-dark-theme .fc-timegrid-col,
          .fc-light-theme .fc-timegrid-col {
            border-color: var(--fc-border-color);
          }

          .fc-dark-theme .fc-timegrid-now-indicator-line,
          .fc-light-theme .fc-timegrid-now-indicator-line {
            border-color: var(--fc-now-indicator-color);
            border-width: 2px;
          }

          .fc-dark-theme .fc-timegrid-now-indicator-arrow,
          .fc-light-theme .fc-timegrid-now-indicator-arrow {
            border-color: var(--fc-now-indicator-color);
            border-top-color: transparent;
            border-bottom-color: transparent;
          }

          .fc-dark-theme .fc-event,
          .fc-light-theme .fc-event {
            border-radius: 4px;
            font-size: 0.75rem;
            padding: 2px 4px;
          }

          .fc-dark-theme .fc-event-title,
          .fc-light-theme .fc-event-title {
            font-weight: 500;
          }

          .fc-dark-theme .fc-timegrid-event-harness,
          .fc-light-theme .fc-timegrid-event-harness {
            margin: 0 2px;
          }

          .fc-dark-theme .fc-day-today,
          .fc-light-theme .fc-day-today {
            background: var(--fc-today-bg-color) !important;
          }

          .fc-dark-theme .fc-scrollgrid-sync-inner,
          .fc-light-theme .fc-scrollgrid-sync-inner {
            padding: 4px;
          }
        `}</style>
      </div>
    );
  }
);

export default CalendarCore;
