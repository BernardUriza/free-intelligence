/**
 * PreviewTab - Visual schedule preview with FullCalendar
 *
 * Tab showing a professional calendar view of the schedule
 * using the reusable CalendarCore component
 */

'use client';

import { Eye, ChevronLeft, ChevronRight, Calendar, RotateCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { CalendarCore, useFullCalendar } from '@/components/fullcalendar';
import type { DoctorAvailability } from '../types';
import { calculateWeeklyHours, getWorkingDays } from '../utils/transform';

interface PreviewTabProps {
  availability: DoctorAvailability;
}

export function PreviewTab({ availability }: PreviewTabProps) {
  // Use the combined hook for events + navigation
  const { events, calendarRef, navigation } = useFullCalendar(availability, {
    daysToGenerate: 70,
    availableLabel: 'Disponible',
    overrideLabel: 'Horario especial',
  });

  const workingHours = calculateWeeklyHours(availability);
  const workingDays = getWorkingDays(availability);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="avail-tab-header">
        <div className="avail-icon-wrap-cyan">
          <Eye className="avail-icon-cyan" />
        </div>
        <div>
          <h3 className="avail-tab-header-title">Vista Previa</h3>
          <p className="avail-tab-header-desc">
            Visualiza cómo se verá tu disponibilidad en el calendario.
          </p>
        </div>
      </div>

      {/* Navigation buttons */}
      <div className="flex items-center justify-between">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={navigation.goToPrev}
          className="avail-nav-btn"
        >
          <ChevronLeft className="w-4 h-4 mr-1" />
          Anterior
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={navigation.goToToday}
          className="avail-nav-btn"
        >
          <RotateCcw className="w-4 h-4 mr-1" />
          Hoy
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={navigation.goToNext}
          className="avail-nav-btn"
        >
          Siguiente
          <ChevronRight className="w-4 h-4 ml-1" />
        </Button>
      </div>

      {/* FullCalendar via CalendarCore */}
      <div className="avail-calendar-wrap">
        <CalendarCore
          ref={calendarRef}
          events={events}
          height={420}
          locale="es"
          theme="dark"
          timePreset="business"
          nowIndicator={true}
          allDaySlot={false}
        />
      </div>

      {/* Legend & Summary */}
      <div className="avail-legend">
        <div className="avail-summary-row">
          <div className="flex items-center gap-2">
            <div className="avail-legend-swatch-indigo" />
            <span className="text-slate-400">Disponible</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="avail-legend-swatch-orange" />
            <span className="text-slate-400">Excepción</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="avail-legend-swatch-slate" />
            <span className="text-slate-400">Día libre</span>
          </div>
        </div>
        <div className="text-sm text-slate-400">
          <span className="text-white font-medium">{workingHours}h</span>/semana ·{' '}
          <span className="text-white font-medium">{workingDays.length}</span> días
        </div>
      </div>

      {/* Empty state */}
      {availability.weeklySchedule.length === 0 && (
        <div className="avail-empty-bordered">
          <Calendar className="avail-empty-icon" />
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
