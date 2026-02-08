'use client';

/**
 * PatientSearchField Component
 *
 * Patient search input with dropdown results and inline creation.
 * Features:
 * - Search existing patients with debounced autocomplete
 * - Quick "Nuevo" button always visible for creating new patients
 * - Inline form for patient creation without leaving the modal
 */

import { User, Search, X, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { Patient } from '@/lib/api/patients';
import type { NewPatientForm } from '../types';

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
  newPatient: NewPatientForm;
  onNewPatientChange: (form: NewPatientForm) => void;
  onCreatePatient: () => void;
  onCloseCreateForm: () => void;
  creating: boolean;

  // Validation
  getFieldError: (fieldName: string) => string | undefined;
  onFieldBlur: (fieldName: string) => void;
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
      <label htmlFor="patient-search" className="apt-field-label">
        <User className="fi-icon-sm" />
        Paciente
      </label>

      <div className="relative" ref={dropdownRef}>
        {selectedPatientId ? (
          // Selected patient display
          <div className="apt-patient-selected">
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
          // Search input + create button
          <div className="flex gap-2">
            <div className="relative flex-1">
              <input
                id="patient-search"
                name="patient-search"
                type="text"
                value={search}
                onChange={(e) => onSearchChange(e.target.value)}
                onFocus={onFocus}
                placeholder="Buscar por nombre..."
                className="fi-input-cyan pr-10 w-full"
                aria-label="Buscar paciente"
              />
              <Search className="apt-search-icon" />
            </div>
            <Button
              type="button"
              onClick={onOpenCreateForm}
              variant="ghost"
              size="sm"
              className="apt-patient-new-btn"
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
                className="apt-patient-dropdown-item"
              >
                <div className="font-medium text-white">{patient.name}</div>
                <div className="fi-subtitle text-xs truncate">ID: {patient.id}</div>
              </button>
            ))}
        </div>
      )}

      {/* No results message */}
      {showDropdown && !loading && results.length === 0 && search.length >= 2 && (
        <div className="fi-dropdown">
          <div className="fi-dropdown-message text-slate-400">
            No se encontraron pacientes. Usa el botón "Nuevo" para crear uno.
          </div>
        </div>
      )}

      {/* Create patient form */}
      {showCreateForm && (
        <div className="apt-patient-create-form">
          <div className="apt-patient-create-header">
            <h4 className="apt-patient-create-title">Nuevo Paciente</h4>
            <Button
              type="button"
              onClick={onCloseCreateForm}
              variant="ghost"
              size="sm"
              icon={X}
              aria-label="Cancelar"
            />
          </div>

          <div>
            <label htmlFor="new-patient-nombre" className="sr-only">
              Nombre
            </label>
            <input
              id="new-patient-nombre"
              name="nombre"
              type="text"
              placeholder="Nombre *"
              value={newPatient.nombre}
              onChange={(e) => onNewPatientChange({ ...newPatient, nombre: e.target.value })}
              className="fi-input-sm"
              autoFocus
              aria-required="true"
            />
          </div>

          <div>
            <label htmlFor="new-patient-apellido" className="sr-only">
              Apellido
            </label>
            <input
              id="new-patient-apellido"
              name="apellido"
              type="text"
              placeholder="Apellido *"
              value={newPatient.apellido}
              onChange={(e) => onNewPatientChange({ ...newPatient, apellido: e.target.value })}
              className="fi-input-sm"
              aria-required="true"
            />
          </div>

          <Button
            type="button"
            onClick={onCreatePatient}
            disabled={creating || !newPatient.nombre || !newPatient.apellido}
            variant="primary"
            fullWidth
            loading={creating}
          >
            {creating ? 'Creando...' : 'Crear Paciente'}
          </Button>
        </div>
      )}
    </div>
  );
}
