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
      <div className="avail-tab-header">
        <div className="avail-icon-wrap-indigo">
          <Calendar className="avail-icon-indigo" />
        </div>
        <div>
          <h3 className="avail-tab-header-title">Horario Semanal</h3>
          <p className="avail-tab-header-desc">
            Define tu horario recurrente para cada día de la semana. Puedes
            agregar múltiples bloques horarios por día (ej: mañana y tarde).
          </p>
        </div>
      </div>

      {/* Summary */}
      <div className="avail-summary-row">
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
        <div className="avail-gaps-warning">
          <p className="avail-gaps-title">
            <strong>Nota:</strong> Se detectaron espacios entre horarios:
          </p>
          <ul className="avail-gaps-list">
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
        <div className="avail-empty">
          <Calendar className="avail-empty-icon" />
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
