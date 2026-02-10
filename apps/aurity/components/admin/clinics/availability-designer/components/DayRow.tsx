/**
 * DayRow - Single day editor row
 *
 * Row for editing a single day's schedule with toggle and slots
 */

'use client';

import { Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { SlotEditor } from './SlotEditor';
import { DAYS_OF_WEEK } from '../constants';
import type { DaySchedule, WeeklySlot, ValidationError } from '../types';
import { getErrorsForDay } from '../utils/validation';

interface DayRowProps {
  day: number;
  schedule: DaySchedule;
  errors: ValidationError[];
  onToggleWorking: (isWorking: boolean) => void;
  onAddSlot: () => void;
  onRemoveSlot: (index: number) => void;
  onUpdateSlot: (index: number, updates: Partial<WeeklySlot>) => void;
  disabled?: boolean;
}

export function DayRow({
  day,
  schedule,
  errors,
  onToggleWorking,
  onAddSlot,
  onRemoveSlot,
  onUpdateSlot,
  disabled = false,
}: DayRowProps) {
  const dayInfo = DAYS_OF_WEEK.find((d) => d.value === day);
  const dayErrors = getErrorsForDay(errors, day);
  const hasError = dayErrors.length > 0;

  return (
    <div
      className={`border rounded-lg p-3 transition-all ${
        hasError
          ? 'border-red-500/50 bg-red-500/5'
          : schedule.isWorking
          ? 'border-slate-700 bg-slate-800/30'
          : 'border-slate-800 bg-slate-900/50 opacity-60'
      }`}
    >
      {/* Day header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-3">
          {/* Day abbreviation badge */}
          <div
            className={`w-10 h-10 rounded-lg flex items-center justify-center font-semibold text-sm ${
              schedule.isWorking
                ? 'bg-indigo-500/20 text-indigo-400'
                : 'bg-slate-800 text-slate-500'
            }`}
          >
            {dayInfo?.short || day}
          </div>

          {/* Day name */}
          <div>
            <span
              className={`font-medium ${
                schedule.isWorking ? 'text-white' : 'text-slate-500'
              }`}
            >
              {dayInfo?.label || `Día ${day}`}
            </span>
            {!schedule.isWorking && (
              <span className="text-xs text-slate-600 ml-2">Día libre</span>
            )}
          </div>
        </div>

        {/* Toggle */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">
            {schedule.isWorking ? 'Activo' : 'Libre'}
          </span>
          <Switch
            checked={schedule.isWorking}
            onCheckedChange={onToggleWorking}
            disabled={disabled}
            aria-label={`${dayInfo?.label || 'Día'} trabaja`}
          />
        </div>
      </div>

      {/* Slots */}
      {schedule.isWorking && (
        <div className="space-y-2 mt-3">
          {schedule.slots.map((slot, index) => {
            // Find error for this specific slot
            const slotError = dayErrors.find(
              (e) =>
                e.message.includes(slot.start) || e.message.includes(slot.end)
            );

            return (
              <SlotEditor
                key={`${day}-${index}`}
                slot={slot}
                index={index}
                onUpdate={(updates) => onUpdateSlot(index, updates)}
                onRemove={() => onRemoveSlot(index)}
                error={slotError?.message}
                canRemove={schedule.slots.length > 1}
                disabled={disabled}
              />
            );
          })}

          {/* Add slot button */}
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={onAddSlot}
            disabled={disabled}
            className="admin-add-slot-btn"
          >
            <Plus className="w-4 h-4 mr-1" />
            Agregar horario
          </Button>
        </div>
      )}

      {/* Day errors summary */}
      {dayErrors.length > 0 && (
        <div className="mt-2 text-xs text-red-400" role="alert">
          {dayErrors
            .filter((e) => e.type === 'overlap')
            .map((e, i) => (
              <div key={i}>{e.message}</div>
            ))}
        </div>
      )}
    </div>
  );
}

export default DayRow;
