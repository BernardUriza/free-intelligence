/**
 * ExceptionsTab - Date-specific overrides
 *
 * Tab for managing exceptions to the weekly schedule
 */

'use client';

import { useState } from 'react';
import { CalendarOff, Plus, Trash2, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { TimeRangeInput } from '../components/TimeRangeInput';
import { COMMON_EXCEPTION_REASONS, DEFAULT_WORK_START, DEFAULT_WORK_END } from '../constants';
import type { DateOverride, ValidationError } from '../types';
import { getErrorsForDate } from '../utils/validation';

interface ExceptionsTabProps {
  overrides: DateOverride[];
  errors: ValidationError[];
  onAddOverride: (override: DateOverride) => void;
  onRemoveOverride: (date: string) => void;
  onUpdateOverride: (date: string, updates: Partial<DateOverride>) => void;
  disabled?: boolean;
}

export function ExceptionsTab({
  overrides,
  errors,
  onAddOverride,
  onRemoveOverride,
  onUpdateOverride,
  disabled = false,
}: ExceptionsTabProps) {
  const [newDate, setNewDate] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);

  // Get today's date for min attribute
  const today = new Date().toISOString().split('T')[0];

  // Sort overrides: future first, then past
  const sortedOverrides = [...overrides].sort((a, b) => {
    const aIsPast = a.date < today;
    const bIsPast = b.date < today;
    if (aIsPast !== bIsPast) return aIsPast ? 1 : -1;
    return a.date.localeCompare(b.date);
  });

  const handleAddException = () => {
    if (!newDate) return;

    // Check if date already exists
    if (overrides.some((o) => o.date === newDate)) {
      return;
    }

    onAddOverride({
      date: newDate,
      fullDayClosed: true,
      reason: '',
    });
    setNewDate('');
    setShowAddForm(false);
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr + 'T12:00:00');
    return date.toLocaleDateString('es-MX', {
      weekday: 'short',
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const isPastDate = (dateStr: string) => dateStr < today;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start gap-3 p-3 bg-slate-800/30 rounded-lg">
        <div className="p-2 bg-orange-500/20 rounded-lg">
          <CalendarOff className="w-5 h-5 text-orange-400" />
        </div>
        <div>
          <h3 className="font-medium text-white">Excepciones</h3>
          <p className="text-sm text-slate-400 mt-1">
            Agrega fechas específicas donde tu horario difiere de lo normal.
            Vacaciones, días festivos, o eventos especiales.
          </p>
        </div>
      </div>

      {/* Add button */}
      {!showAddForm && (
        <Button
          type="button"
          variant="outline"
          onClick={() => setShowAddForm(true)}
          disabled={disabled}
          className="w-full border-dashed"
        >
          <Plus className="w-4 h-4 mr-2" />
          Agregar Excepción
        </Button>
      )}

      {/* Add form */}
      {showAddForm && (
        <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700 space-y-3">
          <div>
            <label className="block text-sm text-slate-400 mb-1">
              Fecha
            </label>
            <Input
              type="date"
              value={newDate}
              onChange={(e) => setNewDate(e.target.value)}
              min={today}
              className="w-full"
              autoFocus
            />
          </div>
          <div className="flex gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setShowAddForm(false);
                setNewDate('');
              }}
              className="flex-1"
            >
              Cancelar
            </Button>
            <Button
              type="button"
              variant="indigo"
              onClick={handleAddException}
              disabled={!newDate || overrides.some((o) => o.date === newDate)}
              className="flex-1"
            >
              Agregar
            </Button>
          </div>
          {newDate && overrides.some((o) => o.date === newDate) && (
            <p className="text-xs text-red-400">
              Ya existe una excepción para esta fecha
            </p>
          )}
        </div>
      )}

      {/* Overrides list */}
      <div className="space-y-3">
        {sortedOverrides.map((override) => {
          const overrideErrors = getErrorsForDate(errors, override.date);
          const hasError = overrideErrors.length > 0;
          const isPast = isPastDate(override.date);

          return (
            <div
              key={override.date}
              className={`p-4 rounded-lg border transition-all ${
                hasError
                  ? 'border-red-500/50 bg-red-500/5'
                  : isPast
                  ? 'border-slate-800 bg-slate-900/50 opacity-60'
                  : 'border-slate-700 bg-slate-800/30'
              }`}
            >
              {/* Date header */}
              <div className="flex items-center justify-between mb-3">
                <div>
                  <span
                    className={`font-medium ${
                      isPast ? 'text-slate-500' : 'text-white'
                    }`}
                  >
                    {formatDate(override.date)}
                  </span>
                  {isPast && (
                    <span className="text-xs text-slate-600 ml-2">(pasado)</span>
                  )}
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => onRemoveOverride(override.date)}
                  disabled={disabled}
                  className="text-slate-500 hover:text-red-400 hover:bg-red-500/10 p-1 h-8 w-8"
                  aria-label="Eliminar excepción"
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>

              {/* Day off toggle */}
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm text-slate-400">Día completo libre</span>
                <Switch
                  checked={override.fullDayClosed}
                  onCheckedChange={(checked) =>
                    onUpdateOverride(override.date, {
                      fullDayClosed: checked,
                      start: checked ? undefined : DEFAULT_WORK_START,
                      end: checked ? undefined : DEFAULT_WORK_END,
                    })
                  }
                  disabled={disabled || isPast}
                />
              </div>

              {/* Modified hours */}
              {!override.fullDayClosed && (
                <div className="mb-3">
                  <label className="block text-xs text-slate-500 mb-1">
                    Horario modificado
                  </label>
                  <TimeRangeInput
                    startTime={override.start || DEFAULT_WORK_START}
                    endTime={override.end || DEFAULT_WORK_END}
                    onStartChange={(start) =>
                      onUpdateOverride(override.date, { start })
                    }
                    onEndChange={(end) =>
                      onUpdateOverride(override.date, { end })
                    }
                    disabled={disabled || isPast}
                    showLabels={false}
                    compact
                  />
                </div>
              )}

              {/* Reason */}
              <div>
                <label className="block text-xs text-slate-500 mb-1">
                  Razón (opcional)
                </label>
                <div className="flex gap-2 flex-wrap">
                  {COMMON_EXCEPTION_REASONS.slice(0, 4).map((reason) => (
                    <button
                      key={reason}
                      type="button"
                      onClick={() =>
                        onUpdateOverride(override.date, { reason })
                      }
                      disabled={disabled || isPast}
                      className={`px-2 py-1 text-xs rounded-md transition-colors ${
                        override.reason === reason
                          ? 'bg-indigo-500/30 text-indigo-300 border border-indigo-500/50'
                          : 'bg-slate-800 text-slate-400 border border-slate-700 hover:border-slate-600'
                      }`}
                    >
                      {reason}
                    </button>
                  ))}
                  <Input
                    type="text"
                    placeholder="Otra..."
                    value={
                      COMMON_EXCEPTION_REASONS.includes(override.reason as typeof COMMON_EXCEPTION_REASONS[number])
                        ? ''
                        : override.reason || ''
                    }
                    onChange={(e) =>
                      onUpdateOverride(override.date, { reason: e.target.value })
                    }
                    disabled={disabled || isPast}
                    className="flex-1 min-w-[100px] h-7 text-xs"
                  />
                </div>
              </div>

              {/* Errors */}
              {overrideErrors.length > 0 && (
                <div className="mt-2 flex items-center gap-1 text-xs text-red-400">
                  <AlertCircle className="w-3 h-3" />
                  {overrideErrors[0].message}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Empty state */}
      {overrides.length === 0 && !showAddForm && (
        <div className="text-center py-8 text-slate-500">
          <CalendarOff className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>No hay excepciones configuradas.</p>
          <p className="text-sm mt-1">
            Tu horario semanal aplicará sin cambios.
          </p>
        </div>
      )}
    </div>
  );
}

export default ExceptionsTab;
