'use client';

/**
 * DateDivider - Date separator between message groups
 *
 * Minimal: thin gradient lines, small centered label
 */

import { memo } from 'react';
import { format, isToday, isYesterday } from 'date-fns';
import { es } from 'date-fns/locale';
import { messageStyles } from '../config/styles';

export interface DateDividerProps {
  /** Date string (ISO or yyyy-MM-dd) */
  date: string;
}

export const DateDivider = memo(function DateDivider({ date }: DateDividerProps) {
  const d = new Date(date);
  const { dateDivider } = messageStyles;

  // Format label
  let label: string;
  if (isToday(d)) {
    label = 'Hoy';
  } else if (isYesterday(d)) {
    label = 'Ayer';
  } else {
    label = format(d, 'EEEE, d MMM', { locale: es });
  }

  return (
    <div className={dateDivider.container} role="separator" aria-label={`Mensajes del ${label}`}>
      <div className={dateDivider.line} aria-hidden="true" />
      <time className={dateDivider.label} dateTime={date}>
        {label}
      </time>
      <div className={dateDivider.line} aria-hidden="true" />
    </div>
  );
});
