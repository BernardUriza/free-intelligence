/**
 * PatientModal Component
 *
 * Modal wrapper for creating/editing patients
 * Handles API calls and state management
 *
 * @example
 * <PatientModal
 *   isOpen={showModal}
 *   onClose={() => setShowModal(false)}
 *   onSuccess={(patient) => console.log('Created:', patient)}
 * />
 */

import React, { useState } from 'react';
import { X, UserPlus, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { PatientForm } from './PatientForm';
import { createPatient, updatePatient, type PatientCreate, type Patient } from '@/lib/api/patients';
import { createLogger } from '@/lib/internal/logger';

const log = createLogger('PatientModal');

export interface PatientModalProps {
  /** Whether modal is open */
  isOpen: boolean;
  /** Callback when modal should close */
  onClose: () => void;
  /** Callback when patient is successfully created/updated */
  onSuccess: (patient: Patient) => void;
  /** Patient to edit (when in edit mode) */
  patient?: Patient;
  /** Initial data for edit mode */
  initialData?: Partial<PatientCreate>;
  /** Modal mode */
  mode?: 'create' | 'edit';
}

export const PatientModal: React.FC<PatientModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  patient,
  initialData,
  mode = 'create',
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (data: PatientCreate) => {
    setLoading(true);
    setError(null);

    try {
      let result: Patient;

      if (mode === 'edit' && patient) {
        // Update existing patient
        result = await updatePatient(patient.id, data);
      } else {
        // Create new patient
        result = await createPatient(data);
      }

      onSuccess(result);
      onClose();
    } catch (err) {
      log.error(`Failed to ${mode} patient`, { error: String(err) });
      setError(err instanceof Error ? err.message : `Error al ${mode === 'edit' ? 'actualizar' : 'crear'} paciente`);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    if (!loading) {
      setError(null);
      onClose();
    }
  };

  return (
    <div className="fi-modal-backdrop">
      <div className="bg-slate-800 border border-slate-700 rounded-2xl max-w-lg w-full shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-6 fi-border-bottom/50">
          <div className="fi-flex-gap-md">
            <div className="fi-icon-gradient-emerald">
              <UserPlus className="h-6 w-6 fi-text-success" />
            </div>
            <div>
              <h2 className="fi-title-xl">
                {mode === 'create' ? 'Nuevo Paciente' : 'Editar Paciente'}
              </h2>
              <p className="fi-subtitle">
                {mode === 'create' ? 'Registra un nuevo paciente' : 'Actualiza información del paciente'}
              </p>
            </div>
          </div>
          <Button
            onClick={handleClose}
            disabled={loading}
            variant="ghost"
            size="sm"
            icon={X}
            aria-label="Cerrar"
          />
        </div>

        {/* Error Alert */}
        {error && (
          <div className="pat-error-alert">
            <AlertCircle className="h-5 w-5 fi-text-error flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-medium text-red-300">Error</p>
              <p className="text-sm fi-text-error mt-1">{error}</p>
            </div>
          </div>
        )}

        {/* Form */}
        <div className="p-6">
          <PatientForm
            onSubmit={handleSubmit}
            onCancel={handleClose}
            initialData={initialData}
            mode={mode}
            loading={loading}
          />
        </div>
      </div>
    </div>
  );
};
