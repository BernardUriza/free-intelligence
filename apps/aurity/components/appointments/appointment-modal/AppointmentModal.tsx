/**
 * AppointmentModal - Unified create/edit modal
 *
 * Mode-driven orchestration with presentational form and basic validation.
 * Consolidates NewAppointmentModal and EditAppointmentModal.
 */

'use client';

import { useCallback, useMemo, useState } from 'react';
import { X, Calendar, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

import type { AppointmentModalProps } from './types';
import { usePatientSearch, useAppointmentForm } from './hooks';
import { PatientSearchField, AppointmentFormFields } from './components';

export function AppointmentModal({
  mode,
  isOpen,
  onClose,
  onCancel,
  onSubmit,
  onDelete,
  doctors,
  initialData,
  prefilledData,
  submitButtonText,
  hideDoctorField = false,
  onAfterSubmit,
}: AppointmentModalProps) {
  const defaultDoctorId = prefilledData?.doctorId || doctors[0]?.doctor_id || '';
  const [patientName, setPatientName] = useState('');

  const {
    form,
    loading,
    deleting,
    setDeleting,
    updateField,
    setPatientId,
    handleSubmit,
  } = useAppointmentForm({
    mode,
    initialData,
    prefilledData,
    defaultDoctorId,
    onSubmit,
    onClose,
    onAfterSubmit,
  });

  const handlePatientSelect = useCallback((id: string, name: string) => {
    setPatientId(id);
    setPatientName(name);
  }, [setPatientId]);

  const patientSearch = usePatientSearch({
    onPatientSelect: handlePatientSelect,
  });

  const handleClearPatient = useCallback(() => {
    setPatientId('');
    setPatientName('');
    patientSearch.clearSearch();
  }, [setPatientId, patientSearch]);

  const handleDelete = useCallback(async () => {
    if (!onDelete || !initialData?.appointment_id) return;
    setDeleting(true);
    try {
      await onDelete(initialData.appointment_id);
      onClose();
    } catch (err) {
      console.error('[AppointmentModal] delete failed:', err);
    } finally {
      setDeleting(false);
    }
  }, [onDelete, initialData?.appointment_id, onClose, setDeleting]);

  const title = useMemo(() => (mode === 'create' ? 'Nueva Cita Médica' : 'Editar Cita Médica'), [mode]);

  if (!isOpen) return null;

  return (
    <div className="fi-modal-backdrop">
      <div className="fi-modal-md overflow-y-auto">
        {/* Header */}
        <div className="fi-modal-header">
          <div className="fi-flex-gap">
            <div className="p-2 bg-cyan-500/10 rounded-lg">
              <Calendar className="h-5 w-5 fi-text-info" />
            </div>
            <h2 className="fi-title-xl">{title}</h2>
          </div>
          <div className="fi-flex-gap">
            {mode === 'edit' && onDelete && (
              <Button
                onClick={handleDelete}
                variant="ghost"
                size="sm"
                icon={Trash2}
                disabled={deleting || loading}
                className="fi-text-error hover:bg-red-900/30"
                title="Eliminar cita"
                aria-label="Eliminar cita"
              />
            )}
            <Button
              onClick={onClose}
              variant="ghost"
              size="sm"
              icon={X}
              disabled={loading || deleting}
              title="Cerrar"
              aria-label="Cerrar"
            />
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Patient Search */}
          <PatientSearchField
            selectedPatientId={form.patient_id}
            selectedPatientName={patientName}
            onClear={handleClearPatient}
            dropdownRef={patientSearch.dropdownRef}
            search={patientSearch.search}
            onSearchChange={patientSearch.setSearch}
            onFocus={patientSearch.handleFocus}
            showDropdown={patientSearch.showDropdown}
            results={patientSearch.results}
            loading={patientSearch.loading}
            onSelectPatient={patientSearch.handleSelectPatient}
            onOpenCreateForm={patientSearch.openCreateForm}
            showCreateForm={patientSearch.showCreateForm}
            newPatient={patientSearch.newPatient}
            onNewPatientChange={patientSearch.setNewPatient}
            onCreatePatient={patientSearch.handleCreatePatient}
            onCloseCreateForm={patientSearch.closeCreateForm}
            creating={patientSearch.creating}
          />

          {/* Form Fields */}
          <AppointmentFormFields
            form={form}
            doctors={doctors}
            onFieldChange={updateField}
            hideDoctorField={hideDoctorField}
          />

          {/* Actions */}
          <div className="fi-modal-footer">
            <Button
              type="button"
              onClick={onCancel}
              disabled={loading || deleting}
              variant="secondary"
              className="flex-1"
            >
              Cancelar
            </Button>
            <Button
              type="submit"
              disabled={loading || deleting}
              variant="cyan"
              loading={loading}
              className="flex-1"
            >
              {loading
                ? mode === 'create'
                  ? 'Creando…'
                  : 'Guardando…'
                : submitButtonText ?? (mode === 'create' ? 'Crear Cita' : 'Guardar Cambios')}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default AppointmentModal;

// Re-export types for backward compatibility
export type { AppointmentId, AppointmentDraft, AppointmentModalProps } from './types';
