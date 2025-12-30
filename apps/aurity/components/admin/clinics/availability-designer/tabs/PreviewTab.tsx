/**
 * PreviewTab - Visual schedule preview
 *
 * Tab showing a visual representation of the schedule
 */

'use client';

import { useMemo, useState } from 'react';
import { Eye, ChevronLeft, ChevronRight, Calendar } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { DAYS_OF_WEEK } from '../constants';
import type { DoctorAvailability, WeeklySlot, DateOverride } from '../types';
import { timeToMinutes } from '../utils/validation';
import { calculateWeeklyHours, getWorkingDays } from '../utils/transform';

interface PreviewTabProps {
  availability: DoctorAvailability;
}

export function PreviewTab({ availability }: PreviewTabProps) {
  const [weekOffset, setWeekOffset] = useState(0);

  // Calculate week dates
  const weekDates = useMemo(() => {
    const today = new Date();
    const dayOfWeek = today.getDay();
    const startOfWeek = new Date(today);
    startOfWeek.setDate(today.getDate() - dayOfWeek + weekOffset * 7);

    return Array.from({ length: 7 }, (_, i) => {
      const date = new Date(startOfWeek);
      date.setDate(startOfWeek.getDate() + i);
      return date;
    });
  }, [weekOffset]);

  const weekStart = weekDates[0];
  const weekEnd = weekDates[6];

  // Hours to display (7am to 10pm)
  const startHour = 7;
  const endHour = 22;
  const hours = Array.from({ length: endHour - startHour + 1 }, (_, i) => startHour + i);

  // Get slots for a specific date
  const getSlotsForDate = (date: Date): Array<{ start: string; end: string; isOverride?: boolean }> => {
    const dateStr = date.toISOString().split('T')[0];
    const dayOfWeek = date.getDay();

    // Check for date override first
    const override = availability.overrides.find((o) => o.date === dateStr);
    if (override) {
      if (override.fullDayClosed) {
        return [];
      }
      if (override.start && override.end) {
        return [{ start: override.start, end: override.end, isOverride: true }];
      }
    }

    // Get weekly slots
    return availability.weeklySchedule
      .filter((slot) => slot.day === dayOfWeek)
      .map((slot) => ({ start: slot.start, end: slot.end }));
  };

  // Check if date has override
  const hasOverride = (date: Date): boolean => {
    const dateStr = date.toISOString().split('T')[0];
    return availability.overrides.some((o) => o.date === dateStr);
  };

  // Calculate slot position and height
  const getSlotStyle = (slot: { start: string; end: string }) => {
    const startMin = timeToMinutes(slot.start);
    const endMin = timeToMinutes(slot.end);
    const dayStartMin = startHour * 60;
    const dayEndMin = (endHour + 1) * 60;

    const top = ((Math.max(startMin, dayStartMin) - dayStartMin) / (dayEndMin - dayStartMin)) * 100;
    const bottom = ((dayEndMin - Math.min(endMin, dayEndMin)) / (dayEndMin - dayStartMin)) * 100;

    return {
      top: `${top}%`,
      bottom: `${bottom}%`,
    };
  };

  const formatDateHeader = (date: Date) => {
    return date.toLocaleDateString('es-MX', {
      day: 'numeric',
      month: 'short',
    });
  };

  const formatWeekRange = () => {
    return `${weekStart.toLocaleDateString('es-MX', {
      day: 'numeric',
      month: 'short',
    })} - ${weekEnd.toLocaleDateString('es-MX', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    })}`;
  };

  const isToday = (date: Date) => {
    const today = new Date();
    return date.toDateString() === today.toDateString();
  };

  const workingHours = calculateWeeklyHours(availability);
  const workingDays = getWorkingDays(availability);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start gap-3 p-3 bg-slate-800/30 rounded-lg">
        <div className="p-2 bg-cyan-500/20 rounded-lg">
          <Eye className="w-5 h-5 text-cyan-400" />
        </div>
        <div>
          <h3 className="font-medium text-white">Vista Previa</h3>
          <p className="text-sm text-slate-400 mt-1">
            Visualiza cómo se verá tu disponibilidad en el calendario.
          </p>
        </div>
      </div>

      {/* Week navigation */}
      <div className="flex items-center justify-between">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => setWeekOffset((o) => o - 1)}
          className="text-slate-400"
        >
          <ChevronLeft className="w-4 h-4 mr-1" />
          Anterior
        </Button>
        <div className="text-center">
          <span className="text-white font-medium">{formatWeekRange()}</span>
          {weekOffset !== 0 && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setWeekOffset(0)}
              className="ml-2 text-xs text-slate-500 hover:text-slate-300"
            >
              Hoy
            </Button>
          )}
        </div>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => setWeekOffset((o) => o + 1)}
          className="text-slate-400"
        >
          Siguiente
          <ChevronRight className="w-4 h-4 ml-1" />
        </Button>
      </div>

      {/* Calendar grid */}
      <div className="border border-slate-700 rounded-lg overflow-hidden bg-slate-900/50">
        {/* Day headers */}
        <div className="grid grid-cols-8 border-b border-slate-700">
          <div className="p-2 text-xs text-slate-500" /> {/* Time column */}
          {weekDates.map((date, i) => (
            <div
              key={i}
              className={`p-2 text-center border-l border-slate-700 ${
                isToday(date) ? 'bg-indigo-500/10' : ''
              }`}
            >
              <div
                className={`text-xs font-medium ${
                  isToday(date) ? 'text-indigo-400' : 'text-slate-400'
                }`}
              >
                {DAYS_OF_WEEK[date.getDay()]?.short}
              </div>
              <div
                className={`text-sm ${
                  isToday(date) ? 'text-white' : 'text-slate-500'
                }`}
              >
                {formatDateHeader(date)}
              </div>
              {hasOverride(date) && (
                <div className="w-2 h-2 bg-orange-400 rounded-full mx-auto mt-1" />
              )}
            </div>
          ))}
        </div>

        {/* Time grid */}
        <div className="grid grid-cols-8 relative" style={{ height: '400px' }}>
          {/* Time labels */}
          <div className="relative">
            {hours.map((hour) => (
              <div
                key={hour}
                className="absolute left-0 right-0 text-xs text-slate-600 pr-2 text-right"
                style={{
                  top: `${((hour - startHour) / (endHour - startHour + 1)) * 100}%`,
                  transform: 'translateY(-50%)',
                }}
              >
                {hour}:00
              </div>
            ))}
          </div>

          {/* Day columns */}
          {weekDates.map((date, dayIndex) => {
            const slots = getSlotsForDate(date);

            return (
              <div
                key={dayIndex}
                className={`relative border-l border-slate-700 ${
                  isToday(date) ? 'bg-indigo-500/5' : ''
                }`}
              >
                {/* Hour lines */}
                {hours.map((hour) => (
                  <div
                    key={hour}
                    className="absolute left-0 right-0 border-t border-slate-800"
                    style={{
                      top: `${((hour - startHour) / (endHour - startHour + 1)) * 100}%`,
                    }}
                  />
                ))}

                {/* Working slots */}
                {slots.map((slot, slotIndex) => (
                  <div
                    key={slotIndex}
                    className={`absolute left-1 right-1 rounded ${
                      slot.isOverride
                        ? 'bg-orange-500/30 border border-orange-500/50'
                        : 'bg-indigo-500/30 border border-indigo-500/50'
                    }`}
                    style={getSlotStyle(slot)}
                  >
                    <div className="p-1 text-xs text-white truncate">
                      {slot.start}
                    </div>
                  </div>
                ))}

                {/* Day off indicator */}
                {slots.length === 0 && (
                  <div className="absolute inset-1 flex items-center justify-center">
                    <span className="text-xs text-slate-600 -rotate-45">
                      Libre
                    </span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Summary */}
      <div className="flex justify-between items-center p-3 bg-slate-800/30 rounded-lg">
        <div className="flex gap-4 text-sm">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-indigo-500/50 rounded" />
            <span className="text-slate-400">Disponible</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-orange-500/50 rounded" />
            <span className="text-slate-400">Excepción</span>
          </div>
        </div>
        <div className="text-sm text-slate-400">
          <span className="text-white font-medium">{workingHours}h</span>/semana
          · <span className="text-white font-medium">{workingDays.length}</span>{' '}
          días
        </div>
      </div>

      {/* Empty state */}
      {availability.weeklySchedule.length === 0 && (
        <div className="text-center py-8 text-slate-500 border border-dashed border-slate-700 rounded-lg">
          <Calendar className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>No hay horario configurado.</p>
          <p className="text-sm mt-1">
            Ve a la pestaña &quot;Semanal&quot; para agregar disponibilidad.
          </p>
        </div>
      )}
    </div>
  );
}

export default PreviewTab;
