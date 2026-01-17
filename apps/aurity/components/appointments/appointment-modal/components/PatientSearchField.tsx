'use client';

/**
 * PatientSearchField Component
 *
 * Patient search input with dropdown results and inline creation.
 * Uses shared PatientFormFields for inline patient creation.
 */

import { User, Search, X, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { Patient } from '@/lib/api/patients';
import { PatientFormFields } from '@/components/patients/PatientFormFields';
import type {
  PatientFormData,
  PatientFormField,
} from '@/components/patients/usePatientFormValidation';

interface PatientSearchFieldProps {
  // Selected state
  selectedPatientId: string;
  selectedPatientName: string;
  onClear: () => void;

  // Search state
  dropdownRef: React.RefObject<HTMLDivElement>;
  search: string;
  onSearchChange: (value: string) => void;
  onFocus: () => void;

  // Dropdown state
  showDropdown: boolean;
  results: Patient[];
  loading: boolean;
  onSelectPatient: (patient: Patient) => void;
  onOpenCreateForm: () => void;

  // Create patient state
  showCreateForm: boolean;
  newPatient: PatientFormData;
  onNewPatientChange: (field: PatientFormField, value: string) => void;
  onCreatePatient: () => void;
  onCloseCreateForm: () => void;
  creating: boolean;

  // Validation
  getFieldError: (field: PatientFormField) => string | undefined;
  onFieldBlur: (field: PatientFormField) => void;
}

export function PatientSearchField({
  selectedPatientId,
  selectedPatientName,
  onClear,
  dropdownRef,
  search,
  onSearchChange,
  onFocus,
  showDropdown,
  results,
  loading,
  onSelectPatient,
  onOpenCreateForm,
  showCreateForm,
  newPatient,
  onNewPatientChange,
  onCreatePatient,
  onCloseCreateForm,
  creating,
  getFieldError,
  onFieldBlur,
}: PatientSearchFieldProps) {
  return (
    <div className="relative">
      <label className="flex items-center gap-2 fi-label">
        <User className="fi-icon-sm" />
        Paciente
      </label>

      <div className="relative" ref={dropdownRef}>
        {selectedPatientId ? (
          // Show selected patient
          <div className="px-4 py-2 bg-cyan-900/20 border border-cyan-500/30 rounded-lg flex items-center justify-between">
            <span className="text-white">{selectedPatientName || selectedPatientId}</span>
            <Button
              type="button"
              onClick={onClear}
              variant="ghost"
              size="sm"
              icon={X}
              aria-label="Limpiar selección"
            />
          </div>
        ) : (
          // Show search input + create button
          <div className="flex gap-2">
            <div className="relative flex-1">
              <input
                type="text"
                required
                value={search}
                onChange={(e) => onSearchChange(e.target.value)}
                onFocus={onFocus}
                placeholder="Buscar por nombre o ID..."
                className="fi-input-cyan pr-10"
              />
              <Search className="absolute right-3 top-1/2 -translate-y-1/2 fi-icon-sm text-slate-400" />
            </div>
            <Button
              type="button"
              onClick={onOpenCreateForm}
              variant="ghost"
              size="sm"
              className="fi-text-success hover:bg-emerald-900/20 whitespace-nowrap"
            >
              <Plus className="fi-icon-sm mr-1" />
              Nuevo
            </Button>
          </div>
        )}
      </div>

      {/* Dropdown results */}
      {showDropdown && results.length > 0 && (
        <div className="fi-dropdown max-h-64">
          {loading && <div className="fi-dropdown-message">Buscando...</div>}
          {!loading &&
            results.map((patient) => (
              <button
                key={patient.id}
                type="button"
                onMouseDown={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  onSelectPatient(patient);
                }}
                className="w-full px-4 py-3 text-left fi-hover-bg fi-border-bottom last:border-0"
              >
                <div className="font-medium text-white">{patient.name}</div>
                <div className="fi-subtitle">ID: {patient.id}</div>
              </button>
            ))}
        </div>
      )}

      {/* No results */}
      {showDropdown && !loading && results.length === 0 && search.length >= 2 && (
        <div className="fi-dropdown">
          <div className="fi-dropdown-message">
            No se encontraron pacientes. Usa el botón &quot;Nuevo&quot; para crear uno.
          </div>
        </div>
      )}

      {/* Create patient form (using shared PatientFormFields) */}
      {showCreateForm && (
        <div className="mt-3 p-4 bg-slate-800/50 border border-emerald-500/30 rounded-lg">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-medium fi-text-success">Nuevo Paciente</h4>
            <Button
              type="button"
              onClick={onCloseCreateForm}
              variant="ghost"
              size="sm"
              icon={X}
              aria-label="Cancelar"
            />
          </div>

          <PatientFormFields
            variant="compact"
            data={newPatient}
            errors={getFieldError}
            onChange={onNewPatientChange}
            onBlur={onFieldBlur}
            disabled={creating}
          />

          <div className="mt-3">
            <Button
              type="button"
              onClick={onCreatePatient}
              disabled={creating || !newPatient.nombre || !newPatient.apellido || !newPatient.fecha_nacimiento}
              variant="primary"
              fullWidth
              loading={creating}
            >
              {creating ? 'Creando...' : 'Crear Paciente'}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
