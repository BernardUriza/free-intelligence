'use client';

/**
 * PatientSearchField Component
 *
 * Patient search input with dropdown results and inline creation.
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
          // Show search input
          <>
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
          </>
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

          {/* Create new patient button */}
          <button
            type="button"
            onMouseDown={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onOpenCreateForm();
            }}
            className="w-full px-4 py-3 text-left hover:bg-emerald-900/20 transition-colors fi-border-top flex items-center gap-2 fi-text-success"
          >
            <Plus className="fi-icon-sm" />
            <span>Crear nuevo paciente</span>
          </button>
        </div>
      )}

      {/* No results */}
      {showDropdown && !loading && results.length === 0 && search.length >= 2 && (
        <div className="fi-dropdown">
          <div className="fi-dropdown-message">No se encontraron pacientes</div>
          <button
            type="button"
            onClick={onOpenCreateForm}
            className="w-full px-4 py-3 text-left hover:bg-emerald-900/20 transition-colors fi-border-top flex items-center gap-2 fi-text-success"
          >
            <Plus className="fi-icon-sm" />
            <span>Crear nuevo paciente</span>
          </button>
        </div>
      )}

      {/* Create patient form */}
      {showCreateForm && (
        <div className="mt-3 p-4 bg-slate-800/50 border border-emerald-500/30 rounded-lg space-y-3">
          <div className="flex items-center justify-between mb-2">
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

          <input
            type="text"
            placeholder="Nombre *"
            value={newPatient.nombre}
            onChange={(e) => onNewPatientChange({ ...newPatient, nombre: e.target.value })}
            className="fi-input-sm"
          />

          <input
            type="text"
            placeholder="Apellido *"
            value={newPatient.apellido}
            onChange={(e) => onNewPatientChange({ ...newPatient, apellido: e.target.value })}
            className="fi-input-sm"
          />

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
