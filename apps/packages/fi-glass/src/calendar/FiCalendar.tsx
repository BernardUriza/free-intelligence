'use client';

import { forwardRef } from 'react';
import type { CalendarOptions } from '@fullcalendar/core';
import esLocale from '@fullcalendar/core/locales/es';
import dayGridPlugin from '@fullcalendar/daygrid';
import interactionPlugin from '@fullcalendar/interaction';
import FullCalendar from '@fullcalendar/react';
import timeGridPlugin from '@fullcalendar/timegrid';
import { CALENDAR_DEFAULTS, CALENDAR_HOURS, type CalendarHours } from './presets';

const PLUGINS = [timeGridPlugin, dayGridPlugin, interactionPlugin];
const LOCALES = [esLocale];

export type FiCalendarHandle = FullCalendar;

/** Every FullCalendar option passes through and wins over the house default. */
export interface FiCalendarProps extends CalendarOptions {
  hours?: CalendarHours;
  /** `inherit` takes the tokens of the surface around it. */
  theme?: 'dark' | 'light' | 'inherit';
  className?: string;
}

export const FiCalendar = forwardRef<FiCalendarHandle, FiCalendarProps>(function FiCalendar(
  { hours = 'business', theme = 'dark', className, ...options },
  ref,
) {
  const isClickable = Boolean(options.dateClick || options.selectable);
  return (
    <div
      className={className ? `fi-calendar ${className}` : 'fi-calendar'}
      data-theme={theme}
      data-clickable={isClickable || undefined}
    >
      <FullCalendar
        ref={ref}
        plugins={PLUGINS}
        locales={LOCALES}
        {...CALENDAR_DEFAULTS}
        {...CALENDAR_HOURS[hours]}
        {...options}
      />
    </div>
  );
});
