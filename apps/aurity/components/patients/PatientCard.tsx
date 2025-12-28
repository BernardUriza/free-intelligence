/**
 * PatientCard Component
 *
 * SOLID Principle: Single Responsibility
 * - Only responsible for rendering a SINGLE patient card
 * - No business logic, only presentation
 * - Receives patient data and onClick callback (Dependency Inversion)
 *
 * @example
 * <PatientCard
 *   patient={patientData}
 *   onClick={(patient) => handleSelectPatient(patient)}
 * />
 */

import React from 'react';
import { ChevronRight, AlertCircle, Activity, FileText, Edit2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Patient } from '@aurity-standalone/types/patient';

export interface PatientCardProps {
  /** Patient data to display */
  patient: Patient;
  /** Callback when patient card is clicked */
  onClick: (patient: Patient) => void;
  /** Callback when edit button is clicked */
  onEdit?: (patient: Patient) => void;
  /** Number of previous consultations/sessions */
  sessionCount?: number;
  /** Optional custom className for styling extension (Open/Closed) */
  className?: string;
}

export const PatientCard: React.FC<PatientCardProps> = ({
  patient,
  onClick,
  onEdit,
  sessionCount = 0,
  className = ''
}) => {
  const handleEdit = (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent card click
    if (onEdit) {
      onEdit(patient);
    }
  };

  return (
    <div
      onClick={() => onClick(patient)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick(patient);
        }
      }}
      className={`fi-card-interactive-emerald ${className}`}
    >
      <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/5 rounded-full blur-2xl group-hover:bg-emerald-500/10 transition-all -z-10" />

      {/* Patient Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <h3 className="font-semibold text-white group-hover:text-emerald-300 transition-colors">
            {patient.name}
          </h3>
          <div className="flex items-center gap-3 mt-1">
            <span className="fi-subtitle">{patient.age} años</span>
            <span className="fi-text-xs-muted">•</span>
            <span className="fi-subtitle">{patient.gender}</span>

            {/* Session Count Badge */}
            {sessionCount > 0 && (
              <>
                <span className="fi-text-xs-muted">•</span>
                <div className="flex items-center gap-1.5 px-2 py-0.5 bg-cyan-500/10 border border-cyan-500/20 rounded">
                  <FileText className="h-3 w-3 fi-text-info" />
                  <span className="fi-text-xs-medium text-cyan-300">{sessionCount} consulta{sessionCount > 1 ? 's' : ''}</span>
                </div>
              </>
            )}
          </div>
        </div>
        <div className="fi-flex-gap">
          {onEdit && (
            <Button
              onClick={handleEdit}
              variant="ghost"
              size="sm"
              icon={Edit2}
              className="opacity-0 group-hover:opacity-100 bg-slate-700/50 hover:bg-blue-500/20 border border-slate-600/50 hover:border-blue-500/50 text-slate-400 hover:fi-text-primary"
              title="Editar paciente"
              aria-label="Editar paciente"
            />
          )}
          <ChevronRight className="h-5 w-5 text-slate-500 group-hover:fi-text-success group-hover:translate-x-1 transition-all" />
        </div>
      </div>

      {/* Medical Info */}
      {((patient.allergies?.length ?? 0) > 0 || (patient.chronicConditions?.length ?? 0) > 0) && (
        <div className="fi-stack-sm">
          {/* Allergies */}
          {patient.allergies && patient.allergies.length > 0 && (
            <div className="flex items-start gap-2">
              <AlertCircle className="h-4 w-4 fi-text-warning mt-0.5 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="fi-text-xs-muted mb-1">Alergias</p>
                <div className="flex flex-wrap gap-1">
                  {patient.allergies.map((allergy, idx) => (
                    <span
                      key={idx}
                      className="fi-chip-amber"
                    >
                      {allergy}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Chronic Conditions */}
          {patient.chronicConditions && patient.chronicConditions.length > 0 && (
            <div className="flex items-start gap-2">
              <Activity className="h-4 w-4 fi-text-info mt-0.5 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="fi-text-xs-muted mb-1">Condiciones crónicas</p>
                <div className="flex flex-wrap gap-1">
                  {patient.chronicConditions.slice(0, 2).map((condition, idx) => (
                    <span
                      key={idx}
                      className="fi-chip-cyan truncate"
                    >
                      {condition}
                    </span>
                  ))}
                  {patient.chronicConditions.length > 2 && (
                    <span className="inline-block px-2 py-0.5 fi-text-xs">
                      +{patient.chronicConditions.length - 2}
                    </span>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
