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
      <div className="flex items-start gap-3 p-3 bg-slate-800/30 rounded-lg">
        <div className="p-2 bg-purple-500/20 rounded-lg">
          <Settings className="w-5 h-5 text-purple-400" />
        </div>
        <div>
          <h3 className="font-medium text-white">Reglas de Agenda</h3>
          <p className="text-sm text-slate-400 mt-1">
            Configura descansos automáticos, capacidad y restricciones de
            duración para tus citas.
          </p>
        </div>
      </div>

      {/* Break section */}
      <div className="p-4 rounded-lg border border-slate-700 bg-slate-800/20">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-amber-500/20 rounded-lg">
            <Coffee className="w-4 h-4 text-amber-400" />
          </div>
          <div className="flex-1">
            <h4 className="font-medium text-white">Descanso Diario</h4>
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
      <div className="p-4 rounded-lg border border-slate-700 bg-slate-800/20">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-blue-500/20 rounded-lg">
            <Users className="w-4 h-4 text-blue-400" />
          </div>
          <div>
            <h4 className="font-medium text-white">Capacidad</h4>
            <p className="text-xs text-slate-400">
              Limita el número de citas simultáneas
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 pl-11">
          <div>
            <label className="block text-xs text-slate-500 mb-1">
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
            <label className="block text-xs text-slate-500 mb-1">
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
      <div className="p-4 rounded-lg border border-slate-700 bg-slate-800/20">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-green-500/20 rounded-lg">
            <Clock className="w-4 h-4 text-green-400" />
          </div>
          <div>
            <h4 className="font-medium text-white">Duración de Citas</h4>
            <p className="text-xs text-slate-400">
              Restricciones de tiempo para las citas
            </p>
          </div>
        </div>

        <div className="pl-11">
          <div>
            <label className="block text-xs text-slate-500 mb-1">
              Duración mínima (minutos)
            </label>
            <div className="flex gap-2">
              {[15, 20, 30, 45, 60].map((duration) => (
                <button
                  key={duration}
                  type="button"
                  onClick={() => onUpdateRules({ minSlotDuration: duration })}
                  disabled={disabled}
                  className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                    rules.minSlotDuration === duration
                      ? 'bg-indigo-500/30 text-indigo-300 border border-indigo-500/50'
                      : 'bg-slate-800 text-slate-400 border border-slate-700 hover:border-slate-600'
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
      <div className="p-3 bg-slate-800/30 rounded-lg text-xs text-slate-400">
        <p>
          <strong className="text-slate-300">Nota:</strong> Estas reglas son
          sugerencias y pueden ser sobrescritas al crear citas manualmente.
        </p>
      </div>
    </div>
  );
}

export default RulesTab;
