/**
 * WeeklyScheduleTab - Weekly schedule editor
 *
 * Tab for editing recurring weekly working hours
 */

'use client';

import { Calendar } from 'lucide-react';
import { DayRow } from '../components/DayRow';
import { DAYS_OF_WEEK } from '../constants';
import type { DaySchedule, WeeklySlot, ValidationError } from '../types';
import { detectGaps } from '../utils/validation';

interface WeeklyScheduleTabProps {
  weeklySchedule: Record<number, DaySchedule>;
  errors: ValidationError[];
  onSetDayWorking: (day: number, isWorking: boolean) => void;
  onAddSlot: (day: number) => void;
  onRemoveSlot: (day: number, index: number) => void;
  onUpdateSlot: (day: number, index: number, updates: Partial<WeeklySlot>) => void;
  disabled?: boolean;
}

export function WeeklyScheduleTab({
  weeklySchedule,
  errors,
  onSetDayWorking,
  onAddSlot,
  onRemoveSlot,
  onUpdateSlot,
  disabled = false,
}: WeeklyScheduleTabProps) {
  // Calculate summary stats
  const workingDays = Object.entries(weeklySchedule).filter(
    ([_, schedule]) => schedule.isWorking
  ).length;

  const totalSlots = Object.values(weeklySchedule).reduce(
    (acc, schedule) => acc + (schedule.isWorking ? schedule.slots.length : 0),
    0
  );

  // Detect gaps for informational display
  const allSlots = Object.values(weeklySchedule).flatMap((s) => s.slots);
  const gaps = detectGaps(allSlots);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start gap-3 p-3 bg-slate-800/30 rounded-lg">
        <div className="p-2 bg-indigo-500/20 rounded-lg">
          <Calendar className="w-5 h-5 text-indigo-400" />
        </div>
        <div>
          <h3 className="font-medium text-white">Horario Semanal</h3>
          <p className="text-sm text-slate-400 mt-1">
            Define tu horario recurrente para cada día de la semana. Puedes
            agregar múltiples bloques horarios por día (ej: mañana y tarde).
          </p>
        </div>
      </div>

      {/* Summary */}
      <div className="flex gap-4 text-sm">
        <div className="flex items-center gap-2">
          <span className="text-slate-500">Días activos:</span>
          <span className="text-white font-medium">{workingDays}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-slate-500">Bloques:</span>
          <span className="text-white font-medium">{totalSlots}</span>
        </div>
      </div>

      {/* Days grid */}
      <div className="space-y-3">
        {DAYS_OF_WEEK.map((day) => {
          const schedule = weeklySchedule[day.value] || {
            isWorking: false,
            slots: [],
          };

          return (
            <DayRow
              key={day.value}
              day={day.value}
              schedule={schedule}
              errors={errors}
              onToggleWorking={(isWorking) => onSetDayWorking(day.value, isWorking)}
              onAddSlot={() => onAddSlot(day.value)}
              onRemoveSlot={(index) => onRemoveSlot(day.value, index)}
              onUpdateSlot={(index, updates) =>
                onUpdateSlot(day.value, index, updates)
              }
              disabled={disabled}
            />
          );
        })}
      </div>

      {/* Gaps warning */}
      {gaps.length > 0 && (
        <div className="p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
          <p className="text-sm text-yellow-400">
            <strong>Nota:</strong> Se detectaron espacios entre horarios:
          </p>
          <ul className="mt-1 text-xs text-yellow-400/80 list-disc list-inside">
            {gaps.map((gap, i) => (
              <li key={i}>
                {DAYS_OF_WEEK.find((d) => d.value === gap.day)?.label}: {gap.gap}{' '}
                (¿descanso?)
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Empty state */}
      {workingDays === 0 && (
        <div className="text-center py-8 text-slate-500">
          <Calendar className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>No hay días de trabajo configurados.</p>
          <p className="text-sm mt-1">
            Activa al menos un día para definir tu horario.
          </p>
        </div>
      )}
    </div>
  );
}

export default WeeklyScheduleTab;
