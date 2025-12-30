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

      {/* Navigation buttons */}
      <div className="flex items-center justify-between">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={navigation.goToPrev}
          className="text-slate-400 hover:text-white"
        >
          <ChevronLeft className="w-4 h-4 mr-1" />
          Anterior
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={navigation.goToToday}
          className="text-slate-400 hover:text-white"
        >
          <RotateCcw className="w-4 h-4 mr-1" />
          Hoy
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={navigation.goToNext}
          className="text-slate-400 hover:text-white"
        >
          Siguiente
          <ChevronRight className="w-4 h-4 ml-1" />
        </Button>
      </div>

      {/* FullCalendar via CalendarCore */}
      <div className="rounded-lg overflow-hidden border border-slate-700">
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
      <div className="flex justify-between items-center p-3 bg-slate-800/30 rounded-lg">
        <div className="flex gap-4 text-sm">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-indigo-500/50 rounded border border-indigo-500/60" />
            <span className="text-slate-400">Disponible</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-orange-500/50 rounded border border-orange-500/60" />
            <span className="text-slate-400">Excepción</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-slate-600/30 rounded border border-slate-600/50" />
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
