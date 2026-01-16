/**
 * Patient Form Validation Hook
 *
 * Centralized validation logic for patient creation/edit forms.
 * Used by both full PatientForm and inline creation in AppointmentModal.
 *
 * Features:
 * - Synchronous field validation (format, required, length)
 * - Async CURP validation (uniqueness check against backend)
 * - Debounced async validation (500ms delay)
 *
 * @example
 * const validation = usePatientFormValidation();
 * validation.validateField('nombre', value);
 * const { isValid, errors } = validation.validate(formData);
 * await validation.validateCurpAsync('CURP123...'); // Check uniqueness
 */

import { useState, useCallback, useRef } from 'react';
import type { Gender } from '@/lib/api/patients';
import { validateCurp as validateCurpApi } from '@/lib/api/patients';

// ============================================================================
// Types
// ============================================================================

export interface PatientFormData {
  nombre: string;
  apellido: string;
  fecha_nacimiento: string;
  genero?: Gender | null;
  curp?: string | null;
}

export interface PatientFormErrors {
  nombre?: string;
  apellido?: string;
  fecha_nacimiento?: string;
  genero?: string;
  curp?: string;
}

export type PatientFormField = keyof PatientFormData;

interface ValidationResult {
  isValid: boolean;
  errors: PatientFormErrors;
}

// ============================================================================
// Constants
// ============================================================================

const MIN_NAME_LENGTH = 2;
const MAX_AGE_YEARS = 150;
const CURP_LENGTH = 18;

// Character pattern for Mexican names (compatible with es5 target)
const NAME_PATTERN = /^[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ\s'-]+$/;

// CURP format: AAAA######AAAAAA## (18 chars)
const CURP_PATTERN = /^[A-Z]{4}\d{6}[HM][A-Z]{5}[0-9A-Z]\d$/;

// ============================================================================
// Static Validators (no React state)
// ============================================================================

/**
 * Validate Mexican CURP format
 */
export function validateCURP(curp: string): boolean {
  if (!curp) return true; // Optional field
  return CURP_PATTERN.test(curp.toUpperCase());
}

/**
 * Validate a single field without state
 */
export function validatePatientField(
  field: PatientFormField,
  value: string | null | undefined
): string | undefined {
  const strValue = value ?? '';

  switch (field) {
    case 'nombre': {
      const trimmed = strValue.trim();
      if (!trimmed) {
        return 'Nombre es requerido';
      }
      if (trimmed.length < MIN_NAME_LENGTH) {
        return `Nombre debe tener al menos ${MIN_NAME_LENGTH} caracteres`;
      }
      if (!NAME_PATTERN.test(trimmed)) {
        return 'Nombre solo puede contener letras';
      }
      return undefined;
    }

    case 'apellido': {
      const trimmed = strValue.trim();
      if (!trimmed) {
        return 'Apellido es requerido';
      }
      if (trimmed.length < MIN_NAME_LENGTH) {
        return `Apellido debe tener al menos ${MIN_NAME_LENGTH} caracteres`;
      }
      if (!NAME_PATTERN.test(trimmed)) {
        return 'Apellido solo puede contener letras';
      }
      return undefined;
    }

    case 'fecha_nacimiento': {
      if (!strValue) {
        return 'Fecha de nacimiento es requerida';
      }

      const birthDate = new Date(strValue);

      if (isNaN(birthDate.getTime())) {
        return 'Fecha no válida';
      }

      const today = new Date();
      today.setHours(0, 0, 0, 0);

      if (birthDate > today) {
        return 'Fecha no puede ser en el futuro';
      }

      const ageMs = today.getTime() - birthDate.getTime();
      const ageYears = ageMs / (365.25 * 24 * 60 * 60 * 1000);

      if (ageYears > MAX_AGE_YEARS) {
        return 'Fecha de nacimiento no válida';
      }

      return undefined;
    }

    case 'curp': {
      if (!strValue) return undefined; // Optional
      if (strValue.length !== CURP_LENGTH) {
        return `CURP debe tener ${CURP_LENGTH} caracteres`;
      }
      if (!validateCURP(strValue)) {
        return 'Formato de CURP inválido';
      }
      return undefined;
    }

    default:
      return undefined;
  }
}

/**
 * Validate entire form without state
 */
export function validatePatientForm(
  data: PatientFormData,
  options?: { includeCurp?: boolean }
): ValidationResult {
  const errors: PatientFormErrors = {};
  const fields: PatientFormField[] = ['nombre', 'apellido', 'fecha_nacimiento'];
  
  if (options?.includeCurp) {
    fields.push('curp');
  }

  for (const field of fields) {
    const error = validatePatientField(field, data[field] as string);
    if (error) {
      errors[field] = error;
    }
  }

  return {
    isValid: Object.keys(errors).length === 0,
    errors,
  };
}

// ============================================================================
// React Hook
// ============================================================================

interface UsePatientFormValidationOptions {
  includeCurp?: boolean;
  /** Patient ID to exclude from CURP uniqueness check (for updates) */
  excludePatientId?: string | null;
  /** Enable async CURP validation against backend (default: true when includeCurp is true) */
  enableAsyncCurpValidation?: boolean;
}

/** Debounce delay for async CURP validation (ms) */
const CURP_VALIDATION_DEBOUNCE_MS = 500;

export function usePatientFormValidation(options?: UsePatientFormValidationOptions) {
  const { 
    includeCurp = false, 
    excludePatientId = null,
    enableAsyncCurpValidation = includeCurp,
  } = options ?? {};

  const [errors, setErrors] = useState<PatientFormErrors>({});
  const [touched, setTouched] = useState<Record<PatientFormField, boolean>>({
    nombre: false,
    apellido: false,
    fecha_nacimiento: false,
    genero: false,
    curp: false,
  });
  const [isValidatingCurp, setIsValidatingCurp] = useState(false);

  // Refs for debounce and abort
  const curpDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const curpAbortRef = useRef<AbortController | null>(null);

  /**
   * Validate CURP async against backend (with debounce)
   * Checks format locally first, then uniqueness on server
   */
  const validateCurpAsync = useCallback(
    async (curp: string): Promise<string | undefined> => {
      // Cancel pending validation
      if (curpDebounceRef.current) {
        clearTimeout(curpDebounceRef.current);
      }
      if (curpAbortRef.current) {
        curpAbortRef.current.abort();
      }

      // Local format validation first
      const formatError = validatePatientField('curp', curp);
      if (formatError) {
        setErrors((prev) => ({ ...prev, curp: formatError }));
        setIsValidatingCurp(false);
        return formatError;
      }

      // Skip API call if CURP is empty or async validation disabled
      if (!curp || !enableAsyncCurpValidation) {
        setErrors((prev) => ({ ...prev, curp: undefined }));
        setIsValidatingCurp(false);
        return undefined;
      }

      setIsValidatingCurp(true);

      return new Promise((resolve) => {
        curpDebounceRef.current = setTimeout(async () => {
          curpAbortRef.current = new AbortController();

          try {
            const result = await validateCurpApi(curp, excludePatientId);

            if (!result.valid) {
              const error = result.message || 'Formato de CURP inválido';
              setErrors((prev) => ({ ...prev, curp: error }));
              resolve(error);
            } else if (!result.available) {
              const error = result.message || 'Este CURP ya está registrado';
              setErrors((prev) => ({ ...prev, curp: error }));
              resolve(error);
            } else {
              setErrors((prev) => ({ ...prev, curp: undefined }));
              resolve(undefined);
            }
          } catch {
            // Network error - don't block form, will validate on submit
            setErrors((prev) => ({ ...prev, curp: undefined }));
            resolve(undefined);
          } finally {
            setIsValidatingCurp(false);
          }
        }, CURP_VALIDATION_DEBOUNCE_MS);
      });
    },
    [excludePatientId, enableAsyncCurpValidation]
  );

  /**
   * Validate a single field and update error state
   */
  const validateField = useCallback(
    (field: PatientFormField, value: string | null | undefined): string | undefined => {
      const error = validatePatientField(field, value);
      setErrors((prev) => ({
        ...prev,
        [field]: error,
      }));
      return error;
    },
    []
  );

  /**
   * Mark a field as touched (for blur events)
   */
  const touchField = useCallback((field: PatientFormField) => {
    setTouched((prev) => ({
      ...prev,
      [field]: true,
    }));
  }, []);

  /**
   * Handle blur: mark as touched and validate
   */
  const handleBlur = useCallback(
    (field: PatientFormField, value: string | null | undefined) => {
      touchField(field);
      validateField(field, value);
    },
    [touchField, validateField]
  );

  /**
   * Validate entire form
   */
  const validate = useCallback(
    (data: PatientFormData): ValidationResult => {
      const result = validatePatientForm(data, { includeCurp });
      setErrors(result.errors);
      // Mark all fields as touched
      setTouched({
        nombre: true,
        apellido: true,
        fecha_nacimiento: true,
        genero: true,
        curp: includeCurp,
      });
      return result;
    },
    [includeCurp]
  );

  /**
   * Clear a specific field error
   */
  const clearFieldError = useCallback((field: PatientFormField) => {
    setErrors((prev) => ({
      ...prev,
      [field]: undefined,
    }));
  }, []);

  /**
   * Reset all errors and touched state
   */
  const reset = useCallback(() => {
    // Cancel any pending CURP validation
    if (curpDebounceRef.current) {
      clearTimeout(curpDebounceRef.current);
    }
    if (curpAbortRef.current) {
      curpAbortRef.current.abort();
    }
    setIsValidatingCurp(false);
    setErrors({});
    setTouched({
      nombre: false,
      apellido: false,
      fecha_nacimiento: false,
      genero: false,
      curp: false,
    });
  }, []);

  /**
   * Get error for a field (only if touched)
   */
  const getFieldError = useCallback(
    (field: PatientFormField): string | undefined => {
      return touched[field] ? errors[field] : undefined;
    },
    [errors, touched]
  );

  /**
   * Check if form has any errors
   */
  const hasErrors = Object.values(errors).some((e) => !!e);

  return {
    errors,
    touched,
    validate,
    validateField,
    validateCurpAsync,
    isValidatingCurp,
    touchField,
    handleBlur,
    clearFieldError,
    reset,
    getFieldError,
    hasErrors,
  };
}
