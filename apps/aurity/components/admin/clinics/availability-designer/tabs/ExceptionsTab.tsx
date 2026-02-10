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
      <div className="avail-tab-header">
        <div className="avail-icon-wrap-orange">
          <CalendarOff className="avail-icon-orange" />
        </div>
        <div>
          <h3 className="avail-tab-header-title">Excepciones</h3>
          <p className="avail-tab-header-desc">
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
        <div className="avail-add-form">
          <div>
            <label className="avail-label-sm">
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
                  ? 'avail-override-error'
                  : isPast
                  ? 'avail-override-past'
                  : 'avail-override-normal'
              }`}
            >
              {/* Date header */}
              <div className="avail-override-header">
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
                  className="avail-override-delete-btn"
                  aria-label="Eliminar excepción"
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>

              {/* Day off toggle */}
              <div className="avail-override-toggle-row">
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
                  <label className="avail-label">
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
                <label className="avail-label">
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
                      className={`avail-reason-chip ${
                        override.reason === reason
                          ? 'avail-chip-active'
                          : 'avail-chip-inactive'
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
                <div className="avail-override-error-msg">
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
        <div className="avail-empty">
          <CalendarOff className="avail-empty-icon" />
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
