/**
 * DoctorDetailModal - Availability Designer
 *
 * Full-featured modal for viewing/editing doctor availability
 * with tabs: Weekly, Exceptions, Rules, Templates, Preview
 *
 * Modes:
 * - 'view': Read-only, shows doctor info and schedule summary
 * - 'edit': Full availability designer with tabs
 */

'use client';

import { useState, useCallback } from 'react';
import { X, Stethoscope, Clock, Calendar, CalendarOff, Settings, Zap, Eye, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';

// Availability Designer imports
import { useAvailabilityForm } from './availability-designer/hooks/useAvailabilityForm';
import { WeeklyScheduleTab } from './availability-designer/tabs/WeeklyScheduleTab';
import { ExceptionsTab } from './availability-designer/tabs/ExceptionsTab';
import { RulesTab } from './availability-designer/tabs/RulesTab';
import { TemplatesTab } from './availability-designer/tabs/TemplatesTab';
import { PreviewTab } from './availability-designer/tabs/PreviewTab';
import { toWorkingHours, toLegacy, calculateWeeklyHours, getWorkingDays } from './availability-designer/utils/transform';
import { DAYS_OF_WEEK } from './availability-designer/constants';
import type { DoctorAvailability } from './availability-designer/types';

// =============================================================================
// TYPES
// =============================================================================

export interface DoctorForModal {
  id?: string;
  doctor_id?: string;
  name?: string;
  display_name?: string | null;
  specialty?: string;
  especialidad?: string | null;
  eventColor?: string;
  work_start_time?: string | null;
  work_end_time?: string | null;
  working_hours?: DoctorAvailability | null;
  email?: string | null;
  cedula_profesional?: string | null;
}

export interface DoctorSaveData {
  work_start_time: string;
  work_end_time: string;
  working_hours?: DoctorAvailability;
}

interface DoctorDetailModalProps {
  doctor: DoctorForModal;
  onClose: () => void;
  onSave?: (data: DoctorSaveData) => void;
  mode?: 'view' | 'edit';
}

// =============================================================================
// COMPONENT
// =============================================================================

export function DoctorDetailModal({
  doctor,
  onClose,
  onSave,
  mode = 'view'
}: DoctorDetailModalProps) {
  const [activeTab, setActiveTab] = useState('weekly');
  const [isSaving, setIsSaving] = useState(false);

  const displayName = doctor.display_name || doctor.name || 'Doctor';
  const specialty = doctor.especialidad || doctor.specialty || 'General';
  const isEditMode = mode === 'edit' && onSave;

  // Initialize form with existing data
  const form = useAvailabilityForm({
    initialAvailability: doctor.working_hours ?? undefined,
    legacyStartTime: doctor.work_start_time ?? undefined,
    legacyEndTime: doctor.work_end_time ?? undefined,
  });

  // Handle save
  const handleSave = useCallback(async () => {
    if (!onSave || !form.validate()) return;

    setIsSaving(true);
    try {
      const availability = form.getAvailability();
      const legacy = toLegacy(availability);

      await onSave({
        work_start_time: legacy.work_start_time || '09:00',
        work_end_time: legacy.work_end_time || '18:00',
        working_hours: availability,
      });
    } finally {
      setIsSaving(false);
    }
  }, [onSave, form]);

  // Handle close with dirty check
  const handleClose = useCallback(() => {
    if (form.isDirty) {
      const confirmed = window.confirm(
        '¿Descartar cambios? Los cambios no guardados se perderán.'
      );
      if (!confirmed) return;
    }
    onClose();
  }, [form.isDirty, onClose]);

  // Get current availability for preview
  const currentAvailability = form.getAvailability();
  const workingDays = getWorkingDays(currentAvailability);
  const weeklyHours = calculateWeeklyHours(currentAvailability);

  return (
    <div
      className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      onClick={handleClose}
    >
      <div
        className={`bg-slate-900 rounded-xl shadow-2xl w-full ${
          isEditMode ? 'max-w-2xl max-h-[90vh]' : 'max-w-md'
        } flex flex-col`}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
      >
        {/* Header */}
        <div className="flex items-start justify-between p-4 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div
              className="p-2 rounded-lg"
              style={{
                backgroundColor: doctor.eventColor
                  ? `${doctor.eventColor}20`
                  : 'rgb(99 102 241 / 0.2)',
              }}
            >
              <Stethoscope
                className="w-5 h-5"
                style={{
                  color: doctor.eventColor || 'rgb(129 140 248)',
                }}
              />
            </div>
            <div>
              <h2 id="modal-title" className="text-lg font-semibold text-white">
                {displayName}
              </h2>
              <p className="text-sm text-slate-400">{specialty}</p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="text-slate-400 hover:text-white p-1.5 hover:bg-slate-800 rounded-lg transition-colors"
            aria-label="Cerrar"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden">
          {isEditMode ? (
            // Edit mode: Full availability designer with tabs
            <div className="flex flex-col h-full">
              <Tabs
                value={activeTab}
                onValueChange={setActiveTab}
                className="flex flex-col h-full"
              >
                {/* Tab navigation */}
                <div className="px-4 pt-3 border-b border-slate-800">
                  <TabsList className="bg-slate-800/50 p-1 rounded-lg w-full grid grid-cols-5 gap-1">
                    <TabsTrigger
                      value="weekly"
                      className="data-[state=active]:bg-indigo-500/20 data-[state=active]:text-indigo-400 rounded-md py-2 text-xs"
                    >
                      <Calendar className="w-3.5 h-3.5 mr-1.5" />
                      Semanal
                    </TabsTrigger>
                    <TabsTrigger
                      value="exceptions"
                      className="data-[state=active]:bg-orange-500/20 data-[state=active]:text-orange-400 rounded-md py-2 text-xs"
                    >
                      <CalendarOff className="w-3.5 h-3.5 mr-1.5" />
                      Excepciones
                    </TabsTrigger>
                    <TabsTrigger
                      value="rules"
                      className="data-[state=active]:bg-purple-500/20 data-[state=active]:text-purple-400 rounded-md py-2 text-xs"
                    >
                      <Settings className="w-3.5 h-3.5 mr-1.5" />
                      Reglas
                    </TabsTrigger>
                    <TabsTrigger
                      value="templates"
                      className="data-[state=active]:bg-emerald-500/20 data-[state=active]:text-emerald-400 rounded-md py-2 text-xs"
                    >
                      <Zap className="w-3.5 h-3.5 mr-1.5" />
                      Plantillas
                    </TabsTrigger>
                    <TabsTrigger
                      value="preview"
                      className="data-[state=active]:bg-cyan-500/20 data-[state=active]:text-cyan-400 rounded-md py-2 text-xs"
                    >
                      <Eye className="w-3.5 h-3.5 mr-1.5" />
                      Preview
                    </TabsTrigger>
                  </TabsList>
                </div>

                {/* Tab content */}
                <div className="flex-1 overflow-y-auto p-4">
                  <TabsContent value="weekly" className="mt-0">
                    <WeeklyScheduleTab
                      weeklySchedule={form.weeklySchedule}
                      errors={form.errors}
                      onSetDayWorking={form.setDayWorking}
                      onAddSlot={form.addSlot}
                      onRemoveSlot={form.removeSlot}
                      onUpdateSlot={form.updateSlot}
                      disabled={isSaving}
                    />
                  </TabsContent>

                  <TabsContent value="exceptions" className="mt-0">
                    <ExceptionsTab
                      overrides={form.overrides}
                      errors={form.errors}
                      onAddOverride={form.addOverride}
                      onRemoveOverride={form.removeOverride}
                      onUpdateOverride={form.updateOverride}
                      disabled={isSaving}
                    />
                  </TabsContent>

                  <TabsContent value="rules" className="mt-0">
                    <RulesTab
                      rules={form.rules}
                      errors={form.errors}
                      onUpdateRules={form.updateRules}
                      disabled={isSaving}
                    />
                  </TabsContent>

                  <TabsContent value="templates" className="mt-0">
                    <TemplatesTab
                      currentAvailability={currentAvailability}
                      onApplyTemplate={form.applyTemplate}
                      disabled={isSaving}
                    />
                  </TabsContent>

                  <TabsContent value="preview" className="mt-0">
                    <PreviewTab availability={currentAvailability} />
                  </TabsContent>
                </div>
              </Tabs>
            </div>
          ) : (
            // View mode: Simple info display
            <div className="p-4 space-y-4">
              {/* Doctor Info */}
              <div className="p-3 bg-slate-800/50 rounded-lg space-y-2">
                {doctor.email && (
                  <p className="text-sm">
                    <span className="text-slate-500">Email:</span>{' '}
                    <span className="text-slate-300">{doctor.email}</span>
                  </p>
                )}
                {doctor.cedula_profesional && (
                  <p className="text-sm">
                    <span className="text-slate-500">Cédula:</span>{' '}
                    <span className="text-slate-300">{doctor.cedula_profesional}</span>
                  </p>
                )}
                {doctor.eventColor && (
                  <p className="text-sm flex items-center gap-2">
                    <span className="text-slate-500">Color:</span>
                    <span
                      className="w-4 h-4 rounded"
                      style={{ backgroundColor: doctor.eventColor }}
                    />
                  </p>
                )}
                {(doctor.id || doctor.doctor_id) && (
                  <p className="text-sm">
                    <span className="text-slate-500">ID:</span>{' '}
                    <span className="text-slate-400 font-mono text-xs">
                      {doctor.id || doctor.doctor_id}
                    </span>
                  </p>
                )}
              </div>

              {/* Schedule Summary */}
              <div className="p-3 bg-slate-800/50 rounded-lg">
                <div className="flex items-center gap-2 text-slate-400 text-sm mb-2">
                  <Clock className="w-4 h-4" />
                  <span>Disponibilidad</span>
                </div>
                {currentAvailability.weeklySchedule.length > 0 ? (
                  <div className="space-y-1">
                    <p className="text-sm text-white">
                      {workingDays.map((d) => DAYS_OF_WEEK[d]?.short).join(', ')}
                    </p>
                    <p className="text-xs text-slate-500">
                      {weeklyHours}h/semana · {form.overrides.length} excepciones
                    </p>
                  </div>
                ) : (
                  <p className="text-sm text-slate-500">
                    {doctor.work_start_time || '09:00'} - {doctor.work_end_time || '18:00'}
                  </p>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-4 border-t border-slate-800">
          {/* Status */}
          <div className="flex items-center gap-2 text-xs">
            {form.hasValidationErrors && (
              <div className="flex items-center gap-1 text-red-400">
                <AlertCircle className="w-3.5 h-3.5" />
                <span>Hay errores en el formulario</span>
              </div>
            )}
            {form.isDirty && !form.hasValidationErrors && (
              <div className="text-amber-400">Cambios sin guardar</div>
            )}
          </div>

          {/* Actions */}
          <div className="flex gap-3">
            <Button onClick={handleClose} variant="outline" disabled={isSaving}>
              {isEditMode ? 'Cancelar' : 'Cerrar'}
            </Button>
            {isEditMode && (
              <Button
                onClick={handleSave}
                variant="indigo"
                disabled={isSaving || form.hasValidationErrors}
              >
                {isSaving ? 'Guardando...' : 'Guardar'}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default DoctorDetailModal;
