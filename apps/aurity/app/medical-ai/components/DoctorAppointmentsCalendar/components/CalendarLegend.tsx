/**
 * CalendarLegend
 *
 * Colour legend strip rendered below the calendar grid.
 */

'use client';

import { STATUS_COLORS, NON_BUSINESS_PATTERN } from '../constants';

interface LegendItem {
  key: string;
  label: string;
  bg: string;
  border: string;
}

const ITEMS: LegendItem[] = [
  { key: 'scheduled', label: 'Programada', ...STATUS_COLORS.scheduled },
  { key: 'checked_in', label: 'Check-in', ...STATUS_COLORS.checked_in },
  { key: 'in_progress', label: 'En consulta', ...STATUS_COLORS.in_progress },
  { key: 'completed', label: 'Completada', ...STATUS_COLORS.completed },
  {
    key: 'non_business',
    label: 'No disponible',
    bg: NON_BUSINESS_PATTERN.gradient,
    border: NON_BUSINESS_PATTERN.border,
  },
];

export function CalendarLegend() {
  return (
    <div className="flex items-center gap-4 mt-3 px-2 text-xs text-slate-400 flex-wrap">
      {ITEMS.map((item) => (
        <div key={item.key} className="flex items-center gap-1">
          <div
            className="w-3 h-3 rounded"
            style={{ background: item.bg, border: `1px solid ${item.border}` }}
          />
          <span>{item.label}</span>
        </div>
      ))}
    </div>
  );
}
