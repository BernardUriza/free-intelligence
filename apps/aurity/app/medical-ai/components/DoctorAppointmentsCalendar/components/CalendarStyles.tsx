/**
 * CalendarStyles
 *
 * Global CSS overrides for FullCalendar's dark theme.
 * Extracted so the main component stays declarative.
 */

'use client';

import type { CalendarThemeConfig } from '@/components/fullcalendar/types/calendar.types';

interface CalendarStylesProps {
  theme: CalendarThemeConfig;
}

export function CalendarStyles({ theme }: CalendarStylesProps) {
  return (
    <style jsx global>{`
      .fc-dark-theme {
        --fc-border-color: ${theme.borderColor};
        --fc-page-bg-color: ${theme.pageBgColor};
        --fc-neutral-bg-color: ${theme.neutralBgColor};
        --fc-today-bg-color: ${theme.todayBgColor};
        --fc-now-indicator-color: ${theme.nowIndicatorColor};
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

      /* Non-business hours - diagonal stripe pattern */
      .fc-dark-theme .fc-non-business {
        background: repeating-linear-gradient(
          -45deg,
          rgba(100, 116, 139, 0.08),
          rgba(100, 116, 139, 0.08) 4px,
          rgba(100, 116, 139, 0.15) 4px,
          rgba(100, 116, 139, 0.15) 8px
        ) !important;
      }

      /* Closed-day background events */
      .fc-dark-theme .fc-bg-event {
        opacity: 1;
      }
    `}</style>
  );
}
