/**
 * TemplatesTab - Quick-start presets
 *
 * Tab for applying predefined schedule templates
 */

'use client';

import { useState } from 'react';
import { Zap, Copy, Check, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { AVAILABILITY_TEMPLATES, DAYS_OF_WEEK } from '../constants';
import type { DoctorAvailability, AvailabilityTemplate } from '../types';
import { calculateWeeklyHours, getWorkingDays } from '../utils/transform';

interface TemplatesTabProps {
  currentAvailability: DoctorAvailability;
  onApplyTemplate: (availability: DoctorAvailability) => void;
  disabled?: boolean;
}

export function TemplatesTab({
  currentAvailability,
  onApplyTemplate,
  disabled = false,
}: TemplatesTabProps) {
  const [confirmTemplate, setConfirmTemplate] = useState<AvailabilityTemplate | null>(
    null
  );

  const hasExistingSchedule = currentAvailability.weeklySchedule.length > 0;

  const handleApply = (template: AvailabilityTemplate) => {
    if (hasExistingSchedule) {
      setConfirmTemplate(template);
    } else {
      onApplyTemplate(template.availability);
    }
  };

  const confirmApply = () => {
    if (confirmTemplate) {
      onApplyTemplate(confirmTemplate.availability);
      setConfirmTemplate(null);
    }
  };

  const formatWorkingDays = (availability: DoctorAvailability) => {
    const days = getWorkingDays(availability);
    return days.map((d) => DAYS_OF_WEEK[d]?.abbr || d).join('-');
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="avail-tab-header">
        <div className="avail-icon-wrap-emerald">
          <Zap className="avail-icon-emerald" />
        </div>
        <div>
          <h3 className="avail-tab-header-title">Plantillas Rápidas</h3>
          <p className="avail-tab-header-desc">
            Aplica un horario predefinido para empezar rápidamente. Puedes
            modificarlo después.
          </p>
        </div>
      </div>

      {/* Confirmation dialog */}
      {confirmTemplate && (
        <div className="avail-confirm-dialog">
          <div className="flex items-start gap-3">
            <AlertTriangle className="avail-confirm-icon" />
            <div className="flex-1">
              <p className="text-sm text-yellow-300">
                <strong>¿Reemplazar horario actual?</strong>
              </p>
              <p className="text-xs text-yellow-400/80 mt-1">
                Aplicar &quot;{confirmTemplate.name}&quot; sobrescribirá tu configuración
                actual.
              </p>
              <div className="flex gap-2 mt-3">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setConfirmTemplate(null)}
                >
                  Cancelar
                </Button>
                <Button
                  type="button"
                  variant="primary"
                  size="sm"
                  onClick={confirmApply}
                  className="bg-yellow-600 hover:bg-yellow-700"
                >
                  Sí, reemplazar
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Templates grid */}
      <div className="grid gap-3">
        {AVAILABILITY_TEMPLATES.map((template) => {
          const hours = calculateWeeklyHours(template.availability);
          const days = formatWorkingDays(template.availability);

          return (
            <div
              key={template.id}
              className="avail-section-card-hover"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h4 className="avail-tab-header-title">{template.name}</h4>
                  <p className="avail-tab-header-desc">
                    {template.description}
                  </p>
                  <div className="avail-template-meta">
                    <span>Días: {days}</span>
                    <span>{hours}h/semana</span>
                  </div>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => handleApply(template)}
                  disabled={disabled || confirmTemplate !== null}
                  className="ml-4"
                >
                  <Copy className="w-4 h-4 mr-1" />
                  Aplicar
                </Button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Current schedule summary */}
      {hasExistingSchedule && (
        <div className="avail-info-box">
          <div className="avail-schedule-summary">
            <Check className="w-4 h-4 text-green-400" />
            <span>
              Horario actual: {formatWorkingDays(currentAvailability)} (
              {calculateWeeklyHours(currentAvailability)}h/semana)
            </span>
          </div>
        </div>
      )}

      {/* Info */}
      <div className="avail-info-box">
        <p>
          <strong className="text-slate-300">Tip:</strong> Las plantillas solo
          configuran el horario semanal. Las excepciones y reglas se mantienen.
        </p>
      </div>
    </div>
  );
}

export default TemplatesTab;
