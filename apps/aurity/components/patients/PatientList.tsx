/**
 * PatientList Component
 *
 * SOLID Principles:
 * - Single Responsibility: Only manages patient list + search
 * - Open/Closed: Extensible via render props, closed for modification
 * - Dependency Inversion: Depends on Patient interface, not concrete impl
 *
 * @example
 * <PatientList
 *   patients={patientData}
 *   onSelectPatient={(p) => startConsultation(p)}
 *   searchPlaceholder="Buscar paciente..."
 * />
 */

import React, { useState } from 'react';
import { Search, Users, Plus, UserPlus } from 'lucide-react';
import { Patient } from '@aurity-standalone/types/patient';
import { PatientCard } from './PatientCard';

export interface PatientListProps {
  /** List of patients to display */
  patients: Patient[];
  /** Callback when a patient is selected */
  onSelectPatient: (patient: Patient) => void;
  /** Callback when edit button is clicked */
  onEditPatient?: (patient: Patient) => void;
  /** Map of patient_id to session count for displaying consultation badges */
  sessionCounts?: Record<string, number>;
  /** Optional callback to add new patient (Open/Closed) */
  onAddPatient?: () => void;
  /** Optional search placeholder text */
  searchPlaceholder?: string;
  /** Optional title for the section */
  title?: string;
  /** Optional subtitle */
  subtitle?: string;
  /** Optional custom render for empty state (Open/Closed) */
  renderEmpty?: () => React.ReactNode;
  /** Optional custom className */
  className?: string;
}

export const PatientList: React.FC<PatientListProps> = ({
  patients,
  onSelectPatient,
  onEditPatient,
  sessionCounts = {},
  onAddPatient,
  searchPlaceholder = 'Buscar por nombre del paciente...',
  title = 'Nueva Consulta',
  subtitle = 'Busca y selecciona un paciente',
  renderEmpty,
  className = ''
}) => {
  const [searchQuery, setSearchQuery] = useState('');

  // Filter patients by search
  const filteredPatients = patients.filter(p =>
    p.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className={`bg-slate-900/50 backdrop-blur-sm border border-slate-800/50 rounded-2xl p-6 shadow-xl ${className}`}>
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className="fi-icon-gradient-emerald">
          <Plus className="h-6 w-6 fi-text-success" />
        </div>
        <div className="flex-1">
          <h2 className="text-lg font-bold text-white">{title}</h2>
          <p className="fi-subtitle">{subtitle}</p>
        </div>
        <div className="fi-flex-gap">
          <div className="badge-modern bg-emerald-500/10 border-emerald-500/20">
            <Users className="h-4 w-4 fi-text-success" />
            <span className="text-emerald-300 font-semibold">{filteredPatients.length} pacientes</span>
          </div>
          {onAddPatient && (
            <button
              onClick={onAddPatient}
              className="fi-btn-primary-action flex items-center gap-2"
              title="Agregar nuevo paciente"
            >
              <UserPlus className="h-4 w-4" />
              <span className="hidden sm:inline">Nuevo</span>
            </button>
          )}
        </div>
      </div>

      {/* Search Input */}
      <div className="relative mb-4">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400" />
        <input
          type="text"
          placeholder={searchPlaceholder}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="fi-form-input-search"
        />
      </div>

      {/* Patient Cards Grid */}
      <div className="pat-list-grid">
        {filteredPatients.length === 0 ? (
          renderEmpty ? (
            renderEmpty()
          ) : (
            <div className="col-span-2 py-12 text-center">
              <Users className="h-12 w-12 text-slate-600 mx-auto mb-3" />
              <p className="text-slate-400">No se encontraron pacientes</p>
            </div>
          )
        ) : (
          filteredPatients.map((patient) => (
            <PatientCard
              key={patient.id}
              patient={patient}
              onClick={onSelectPatient}
              onEdit={onEditPatient}
              sessionCount={sessionCounts[patient.id] || 0}
            />
          ))
        )}
      </div>
    </div>
  );
};
