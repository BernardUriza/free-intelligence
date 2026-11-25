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
import { X, Stethoscope, Clock, AlertCircle } from 'lucide-react';
import { DAYS_OF_WEEK, weeklyHours, workingDays, type DoctorAvailability } from '@free-intelligence/core/availability';
import { AvailabilityEditor, useAvailabilityForm } from 'fi-glass/calendar';
import { Button } from '@/components/ui/button';
import { availabilityFromWorkTimes, commonWorkTimes } from './workingHours';

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
  const [isSaving, setIsSaving] = useState(false);

  const displayName = doctor.display_name || doctor.name || 'Doctor';
  const specialty = doctor.especialidad || doctor.specialty || 'General';
  const isEditMode = mode === 'edit' && onSave;

  // Initialize form with existing data
  const form = useAvailabilityForm(
    doctor.working_hours ?? availabilityFromWorkTimes(doctor.work_start_time, doctor.work_end_time),
  );

  // Handle save
  const handleSave = useCallback(async () => {
    if (!onSave || !form.isValid) return;

    setIsSaving(true);
    try {
      const common = commonWorkTimes(form.availability);

      await onSave({
        work_start_time: common.start,
        work_end_time: common.end,
        working_hours: form.availability,
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

  return (
    <div
      className="doc-modal-overlay"
      onClick={handleClose}
    >
      <div
        className={isEditMode ? 'doc-modal-container-edit' : 'doc-modal-container-view'}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
      >
        {/* Header */}
        <div className="doc-header">
          <div className="doc-header-info">
            <div
              className="doc-header-icon-wrap"
              style={{
                backgroundColor: doctor.eventColor
                  ? `${doctor.eventColor}20`
                  : 'rgb(99 102 241 / 0.2)',
              }}
            >
              <Stethoscope
                className="doc-header-icon"
                style={{
                  color: doctor.eventColor || 'rgb(129 140 248)',
                }}
              />
            </div>
            <div>
              <h2 id="modal-title" className="doc-header-title">
                {displayName}
              </h2>
              <p className="doc-header-specialty">{specialty}</p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="doc-header-close"
            aria-label="Cerrar"
          >
            <X className="doc-header-icon" />
          </button>
        </div>

        {/* Content */}
        <div className="doc-content">
          {isEditMode ? (
            <div className="doc-edit-wrapper">
              <div className="doc-tab-scroll-area">
                <AvailabilityEditor form={form} disabled={isSaving} />
              </div>
            </div>
          ) : (
            // View mode: Simple info display
            <div className="doc-view-body">
              {/* Doctor Info */}
              <div className="doc-info-card">
                {doctor.email && (
                  <p className="doc-info-row">
                    <span className="doc-info-label">Email:</span>{' '}
                    <span className="doc-info-value">{doctor.email}</span>
                  </p>
                )}
                {doctor.cedula_profesional && (
                  <p className="doc-info-row">
                    <span className="doc-info-label">Cédula:</span>{' '}
                    <span className="doc-info-value">{doctor.cedula_profesional}</span>
                  </p>
                )}
                {doctor.eventColor && (
                  <p className="doc-info-row-flex">
                    <span className="doc-info-label">Color:</span>
                    <span
                      className="doc-color-swatch"
                      style={{ backgroundColor: doctor.eventColor }}
                    />
                  </p>
                )}
                {(doctor.id || doctor.doctor_id) && (
                  <p className="doc-info-row">
                    <span className="doc-info-label">ID:</span>{' '}
                    <span className="doc-info-id">
                      {doctor.id || doctor.doctor_id}
                    </span>
                  </p>
                )}
              </div>

              {/* Schedule Summary */}
              <div className="doc-schedule-card">
                <div className="doc-schedule-header">
                  <Clock className="doc-schedule-icon" />
                  <span>Disponibilidad</span>
                </div>
                {form.availability.weeklySchedule.length > 0 ? (
                  <div className="doc-schedule-days-list">
                    <p className="doc-schedule-days-text">
                      {workingDays(form.availability).map((d) => DAYS_OF_WEEK[d]?.short).join(', ')}
                    </p>
                    <p className="doc-schedule-meta">
                      {weeklyHours(form.availability)}h/semana · {form.overrides.length} excepciones
                    </p>
                  </div>
                ) : (
                  <p className="doc-schedule-legacy">
                    {doctor.work_start_time || '09:00'} - {doctor.work_end_time || '18:00'}
                  </p>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="doc-footer">
          {/* Status */}
          <div className="doc-footer-status">
            {!form.isValid && (
              <div className="doc-footer-error">
                <AlertCircle className="doc-footer-error-icon" />
                <span>Hay errores en el formulario</span>
              </div>
            )}
            {form.isDirty && form.isValid && (
              <div className="doc-footer-dirty">Cambios sin guardar</div>
            )}
          </div>

          {/* Actions */}
          <div className="doc-footer-actions">
            <Button onClick={handleClose} variant="outline" disabled={isSaving}>
              {isEditMode ? 'Cancelar' : 'Cerrar'}
            </Button>
            {isEditMode && (
              <Button
                onClick={handleSave}
                variant="indigo"
                disabled={isSaving || !form.isValid}
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
