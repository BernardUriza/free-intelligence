/**
 * PatientFormFields Component
 *
 * Reusable patient form fields with two variants:
 * - 'full': With icons, labels, and full styling (for modals/pages)
 * - 'compact': Minimal styling (for inline creation)
 *
 * @example
 * // Full variant
 * <PatientFormFields
 *   variant="full"
 *   data={formData}
 *   errors={getFieldError}
 *   onChange={handleChange}
 *   onBlur={handleBlur}
 *   showCurp
 * />
 *
 * // Compact variant (inline)
 * <PatientFormFields
 *   variant="compact"
 *   data={formData}
 *   errors={getFieldError}
 *   onChange={handleChange}
 *   onBlur={handleBlur}
 * />
 */

import { User, Calendar, Hash, Users, Loader2 } from 'lucide-react';
import type { PatientFormData, PatientFormField } from './usePatientFormValidation';
import type { Gender } from '@/lib/api/patients';

// Gender options for select
const GENDER_OPTIONS: { value: Gender; label: string }[] = [
  { value: 'MASCULINO', label: 'Masculino' },
  { value: 'FEMENINO', label: 'Femenino' },
  { value: 'OTRO', label: 'Otro' },
  { value: 'NO_ESPECIFICADO', label: 'No especificado' },
];

// ============================================================================
// Types
// ============================================================================

export interface PatientFormFieldsProps {
  /** Display variant */
  variant: 'full' | 'compact';
  /** Form data */
  data: PatientFormData;
  /** Get error message for a field */
  errors: (field: PatientFormField) => string | undefined;
  /** Handle field change */
  onChange: (field: PatientFormField, value: string) => void;
  /** Handle field blur */
  onBlur: (field: PatientFormField) => void;
  /** Show gender field */
  showGender?: boolean;
  /** Show CURP field (only for full variant) */
  showCurp?: boolean;
  /** Disable all fields */
  disabled?: boolean;
  /** Whether CURP is being validated async */
  isValidatingCurp?: boolean;
  /** Async CURP change handler (for debounced validation) */
  onCurpChange?: (value: string) => void;
}

// ============================================================================
// Subcomponents
// ============================================================================

interface FieldWrapperProps {
  children: React.ReactNode;
  error?: string;
  variant: 'full' | 'compact';
}

function FieldWrapper({ children, error, variant }: FieldWrapperProps) {
  return (
    <div>
      {children}
      {error && (
        <p
          className={
            variant === 'full'
              ? 'fi-text-error text-sm mt-1'
              : 'text-xs text-red-400 mt-1'
          }
        >
          {error}
        </p>
      )}
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function PatientFormFields({
  variant,
  data,
  errors,
  onChange,
  onBlur,
  showGender = false,
  showCurp = false,
  disabled = false,
  isValidatingCurp = false,
  onCurpChange,
}: PatientFormFieldsProps) {
  const isCompact = variant === 'compact';

  // Handle CURP change with optional async validation
  const handleCurpChange = (value: string) => {
    const upperValue = value.toUpperCase();
    onChange('curp', upperValue);
    // Trigger async validation if handler provided
    onCurpChange?.(upperValue);
  };

  // Input class based on variant and error state
  const getInputClass = (field: PatientFormField, extraClass?: string) => {
    const hasError = !!errors(field);

    if (isCompact) {
      return `fi-input-sm ${hasError ? 'border-red-500 focus:border-red-500' : ''} ${
        disabled ? 'opacity-50 cursor-not-allowed' : ''
      }`;
    }

    // Full variant
    const baseClass = extraClass ?? 'fi-form-input';
    return `${hasError ? 'fi-form-input-error' : baseClass} ${
      disabled ? 'fi-form-disabled' : ''
    }`;
  };

  return (
    <div className={isCompact ? 'space-y-3' : 'space-y-4'}>
      {/* Nombre */}
      <FieldWrapper error={errors('nombre')} variant={variant}>
        {!isCompact && (
          <label htmlFor="patient-nombre" className="fi-label">
            <div className="fi-flex-gap">
              <User className="h-4 w-4 fi-text-success" />
              Nombre(s) <span className="fi-text-error">*</span>
            </div>
          </label>
        )}
        <input
          id="patient-nombre"
          type="text"
          value={data.nombre}
          onChange={(e) => onChange('nombre', e.target.value)}
          onBlur={() => onBlur('nombre')}
          disabled={disabled}
          placeholder={isCompact ? 'Nombre *' : 'María'}
          className={getInputClass('nombre')}
        />
      </FieldWrapper>

      {/* Apellido */}
      <FieldWrapper error={errors('apellido')} variant={variant}>
        {!isCompact && (
          <label htmlFor="patient-apellido" className="fi-label">
            <div className="fi-flex-gap">
              <User className="h-4 w-4 fi-text-success" />
              Apellido(s) <span className="fi-text-error">*</span>
            </div>
          </label>
        )}
        <input
          id="patient-apellido"
          type="text"
          value={data.apellido}
          onChange={(e) => onChange('apellido', e.target.value)}
          onBlur={() => onBlur('apellido')}
          disabled={disabled}
          placeholder={isCompact ? 'Apellido *' : 'García López'}
          className={getInputClass('apellido')}
        />
      </FieldWrapper>

      {/* Fecha de Nacimiento */}
      <FieldWrapper error={errors('fecha_nacimiento')} variant={variant}>
        {!isCompact ? (
          <label htmlFor="patient-fecha" className="fi-label">
            <div className="fi-flex-gap">
              <Calendar className="h-4 w-4 fi-text-info" />
              Fecha de Nacimiento <span className="fi-text-error">*</span>
            </div>
          </label>
        ) : (
          <label className="text-xs text-slate-400 mb-1 block">
            Fecha de Nacimiento *
          </label>
        )}
        <input
          id="patient-fecha"
          type="date"
          value={data.fecha_nacimiento}
          onChange={(e) => onChange('fecha_nacimiento', e.target.value)}
          onBlur={() => onBlur('fecha_nacimiento')}
          disabled={disabled}
          max={new Date().toISOString().split('T')[0]}
          className={getInputClass('fecha_nacimiento', 'fi-form-input-cyan')}
        />
      </FieldWrapper>

      {/* Género */}
      {showGender && (
        <FieldWrapper error={errors('genero')} variant={variant}>
          {!isCompact ? (
            <label htmlFor="patient-genero" className="fi-label">
              <div className="fi-flex-gap">
                <Users className="h-4 w-4 fi-text-cyan" />
                Género <span className="text-slate-500 text-xs">(opcional)</span>
              </div>
            </label>
          ) : (
            <label className="text-xs text-slate-400 mb-1 block">Género</label>
          )}
          <select
            id="patient-genero"
            value={data.genero || ''}
            onChange={(e) => onChange('genero', e.target.value)}
            onBlur={() => onBlur('genero')}
            disabled={disabled}
            className={getInputClass('genero', 'fi-form-input-cyan')}
          >
            <option value="">Seleccionar...</option>
            {GENDER_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </FieldWrapper>
      )}

      {/* CURP (solo en full variant) */}
      {!isCompact && showCurp && (
        <FieldWrapper error={errors('curp')} variant={variant}>
          <label htmlFor="patient-curp" className="fi-label">
            <div className="fi-flex-gap">
              <Hash className="h-4 w-4 fi-text-purple" />
              CURP <span className="text-slate-500 text-xs">(opcional)</span>
              {isValidatingCurp && (
                <Loader2 className="h-3 w-3 animate-spin text-slate-400" />
              )}
            </div>
          </label>
          <div className="relative">
            <input
              id="patient-curp"
              type="text"
              value={data.curp || ''}
              onChange={(e) => handleCurpChange(e.target.value)}
              onBlur={() => onBlur('curp')}
              disabled={disabled}
              placeholder="GAML800101HDFRRS09"
              maxLength={18}
              className={getInputClass('curp', 'fi-form-input-mono')}
            />
            {isValidatingCurp && (
              <div className="absolute right-3 top-1/2 -translate-y-1/2">
                <Loader2 className="h-4 w-4 animate-spin text-slate-400" />
              </div>
            )}
          </div>
          <p className="fi-text-xs-muted mt-1">
            18 caracteres: 4 letras + 6 dígitos + 8 caracteres
          </p>
        </FieldWrapper>
      )}
    </div>
  );
}
