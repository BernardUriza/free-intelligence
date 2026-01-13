/**
 * PatientForm Component
 *
 * Reusable form for creating/editing patients.
 * Uses shared PatientFormFields and validation hook.
 *
 * @example
 * <PatientForm
 *   onSubmit={(data) => createPatient(data)}
 *   initialData={existingPatient}
 *   mode="edit"
 * />
 */

'use client';

import React, { useState, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import type { PatientCreate } from '@/lib/api/patients';
import { PatientFormFields } from './PatientFormFields';
import {
  usePatientFormValidation,
  type PatientFormData,
  type PatientFormField,
} from './usePatientFormValidation';

// ============================================================================
// Types
// ============================================================================

export interface PatientFormProps {
  /** Callback when form is submitted */
  onSubmit: (data: PatientCreate) => Promise<void> | void;
  /** Callback when form is cancelled */
  onCancel?: () => void;
  /** Initial form data (for edit mode) */
  initialData?: Partial<PatientCreate>;
  /** Patient ID for edit mode (used to exclude from CURP uniqueness check) */
  patientId?: string | null;
  /** Form mode */
  mode?: 'create' | 'edit';
  /** Loading state */
  loading?: boolean;
}

// ============================================================================
// Component
// ============================================================================

export const PatientForm: React.FC<PatientFormProps> = ({
  onSubmit,
  onCancel,
  initialData,
  patientId = null,
  mode = 'create',
  loading = false,
}) => {
  // Form data state
  const [formData, setFormData] = useState<PatientFormData>({
    nombre: initialData?.nombre || '',
    apellido: initialData?.apellido || '',
    fecha_nacimiento: initialData?.fecha_nacimiento || '',
    genero: initialData?.genero || null,
    curp: initialData?.curp || null,
  });

  // Validation hook with async CURP validation
  const validation = usePatientFormValidation({ 
    includeCurp: true,
    excludePatientId: patientId,
    enableAsyncCurpValidation: true,
  });

  // Handle field change
  const handleChange = useCallback(
    (field: PatientFormField, value: string) => {
      setFormData((prev) => ({
        ...prev,
        [field]: value || null,
      }));
      // Clear error when user starts typing
      validation.clearFieldError(field);
    },
    [validation]
  );

  // Handle CURP change with async validation
  const handleCurpChange = useCallback(
    (value: string) => {
      // Trigger async validation (debounced)
      validation.validateCurpAsync(value);
    },
    [validation]
  );

  // Handle field blur
  const handleBlur = useCallback(
    (field: PatientFormField) => {
      validation.handleBlur(field, formData[field]);
    },
    [validation, formData]
  );

  // Handle form submit
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Don't submit while CURP is being validated
    if (validation.isValidatingCurp) {
      return;
    }

    const { isValid } = validation.validate(formData);
    if (!isValid) {
      return;
    }

    // Also check for async validation errors
    if (validation.hasErrors) {
      return;
    }

    await onSubmit({
      nombre: formData.nombre,
      apellido: formData.apellido,
      fecha_nacimiento: formData.fecha_nacimiento,
      genero: formData.genero,
      curp: formData.curp,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <PatientFormFields
        variant="full"
        data={formData}
        errors={validation.getFieldError}
        onChange={handleChange}
        onBlur={handleBlur}
        showGender
        showCurp
        disabled={loading}
        isValidatingCurp={validation.isValidatingCurp}
        onCurpChange={handleCurpChange}
      />

      {/* Actions */}
      <div className="flex gap-3 pt-4">
        {onCancel && (
          <Button
            type="button"
            onClick={onCancel}
            disabled={loading}
            variant="secondary"
            fullWidth
            size="lg"
          >
            Cancelar
          </Button>
        )}
        <Button
          type="submit"
          disabled={loading || validation.isValidatingCurp}
          loading={loading}
          fullWidth
          size="lg"
        >
          {loading
            ? 'Guardando...'
            : mode === 'create'
              ? 'Crear Paciente'
              : 'Guardar Cambios'}
        </Button>
      </div>
    </form>
  );
};
