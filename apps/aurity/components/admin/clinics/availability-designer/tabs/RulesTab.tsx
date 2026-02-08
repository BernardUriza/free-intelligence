/**
 * RulesTab - Scheduling rules and constraints
 *
 * Tab for configuring breaks, capacity, and duration settings
 */

'use client';

import { Settings, Coffee, Users, Clock } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { TimeRangeInput } from '../components/TimeRangeInput';
import type { SchedulingRules, ValidationError } from '../types';

interface RulesTabProps {
  rules: SchedulingRules;
  errors: ValidationError[];
  onUpdateRules: (updates: Partial<SchedulingRules>) => void;
  disabled?: boolean;
}

export function RulesTab({
  rules,
  errors,
  onUpdateRules,
  disabled = false,
}: RulesTabProps) {
  const hasBreak = !!(rules.breakStart && rules.breakEnd);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="avail-tab-header">
        <div className="avail-icon-wrap-purple">
          <Settings className="avail-icon-purple" />
        </div>
        <div>
          <h3 className="avail-tab-header-title">Reglas de Agenda</h3>
          <p className="avail-tab-header-desc">
            Configura descansos automáticos, capacidad y restricciones de
            duración para tus citas.
          </p>
        </div>
      </div>

      {/* Break section */}
      <div className="avail-section-card">
        <div className="avail-section-row">
          <div className="avail-icon-wrap-amber">
            <Coffee className="avail-icon-amber" />
          </div>
          <div className="flex-1">
            <h4 className="avail-tab-header-title">Descanso Diario</h4>
            <p className="text-xs text-slate-400">
              Bloquea automáticamente un período para almuerzo o descanso
            </p>
          </div>
          <Switch
            checked={hasBreak}
            onCheckedChange={(checked) => {
              if (checked) {
                onUpdateRules({
                  breakStart: '13:00',
                  breakEnd: '14:00',
                });
              } else {
                onUpdateRules({
                  breakStart: undefined,
                  breakEnd: undefined,
                });
              }
            }}
            disabled={disabled}
          />
        </div>

        {hasBreak && (
          <div className="pl-11">
            <TimeRangeInput
              startTime={rules.breakStart || '13:00'}
              endTime={rules.breakEnd || '14:00'}
              onStartChange={(breakStart) => onUpdateRules({ breakStart })}
              onEndChange={(breakEnd) => onUpdateRules({ breakEnd })}
              disabled={disabled}
              showLabels
            />
          </div>
        )}
      </div>

      {/* Capacity section */}
      <div className="avail-section-card">
        <div className="avail-section-row">
          <div className="avail-icon-wrap-blue">
            <Users className="avail-icon-blue" />
          </div>
          <div>
            <h4 className="avail-tab-header-title">Capacidad</h4>
            <p className="text-xs text-slate-400">
              Limita el número de citas simultáneas
            </p>
          </div>
        </div>

        <div className="avail-capacity-grid">
          <div>
            <label className="avail-label">
              Máx. pacientes/hora
            </label>
            <Input
              type="number"
              min={1}
              max={20}
              value={rules.maxPatientsPerHour || ''}
              onChange={(e) =>
                onUpdateRules({
                  maxPatientsPerHour: e.target.value
                    ? parseInt(e.target.value)
                    : undefined,
                })
              }
              placeholder="Sin límite"
              disabled={disabled}
              className="w-full"
            />
          </div>
          <div>
            <label className="avail-label">
              Buffer entre citas (min)
            </label>
            <Input
              type="number"
              min={0}
              max={60}
              step={5}
              value={rules.bufferBetweenAppointments || ''}
              onChange={(e) =>
                onUpdateRules({
                  bufferBetweenAppointments: e.target.value
                    ? parseInt(e.target.value)
                    : undefined,
                })
              }
              placeholder="0"
              disabled={disabled}
              className="w-full"
            />
          </div>
        </div>
      </div>

      {/* Duration section */}
      <div className="avail-section-card">
        <div className="avail-section-row">
          <div className="avail-icon-wrap-green">
            <Clock className="avail-icon-green" />
          </div>
          <div>
            <h4 className="avail-tab-header-title">Duración de Citas</h4>
            <p className="text-xs text-slate-400">
              Restricciones de tiempo para las citas
            </p>
          </div>
        </div>

        <div className="pl-11">
          <div>
            <label className="avail-label">
              Duración mínima (minutos)
            </label>
            <div className="flex gap-2">
              {[15, 20, 30, 45, 60].map((duration) => (
                <button
                  key={duration}
                  type="button"
                  onClick={() => onUpdateRules({ minSlotDuration: duration })}
                  disabled={disabled}
                  className={`avail-duration-chip ${
                    rules.minSlotDuration === duration
                      ? 'avail-chip-active'
                      : 'avail-chip-inactive'
                  }`}
                >
                  {duration}
                </button>
              ))}
              <Input
                type="number"
                min={5}
                max={120}
                step={5}
                value={
                  [15, 20, 30, 45, 60].includes(rules.minSlotDuration || 0)
                    ? ''
                    : rules.minSlotDuration || ''
                }
                onChange={(e) =>
                  onUpdateRules({
                    minSlotDuration: e.target.value
                      ? parseInt(e.target.value)
                      : undefined,
                  })
                }
                placeholder="Otro"
                disabled={disabled}
                className="w-20"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Info box */}
      <div className="avail-info-box">
        <p>
          <strong className="text-slate-300">Nota:</strong> Estas reglas son
          sugerencias y pueden ser sobrescritas al crear citas manualmente.
        </p>
      </div>
    </div>
  );
}

export default RulesTab;
