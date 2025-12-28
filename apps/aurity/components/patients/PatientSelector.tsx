/**
 * PatientSelector Component
 *
 * SOLID Principles:
 * - Dependency Inversion: Orchestrates PatientList + SessionList without knowing their internals
 * - Open/Closed: Configuration via props, extensible without modification
 * - Single Responsibility: Coordinates patient selection flow
 *
 * This is the MAIN component that combines PatientList and SessionList.
 *
 * @example
 * <PatientSelector
 *   patients={patients}
 *   sessions={sessions}
 *   onSelectPatient={(p) => startConsultation(p)}
 *   onSelectSession={(id) => loadSession(id)}
 * />
 */

import React from 'react';
import { Patient, SessionSummary, SessionTaskStatus } from '@aurity-standalone/types/patient';
import { PatientList } from './PatientList';
import { SessionList } from './SessionList';

export interface PatientSelectorProps {
  /** Available patients for selection */
  patients: Patient[];
  /** Previous sessions to display */
  sessions: SessionSummary[];
  /** Session task statuses (SOAP, Diarization) */
  sessionStatuses: Record<string, SessionTaskStatus>;
  /** Map of patient_id to session count */
  sessionCounts?: Record<string, number>;
  /** Callback when patient is selected for new consultation */
  onSelectPatient: (patient: Patient) => void;
  /** Callback when edit button is clicked */
  onEditPatient?: (patient: Patient) => void;
  /** Callback when existing session is selected */
  onSelectSession: (sessionId: string) => void;
  /** Callback when session is deleted */
  onDeleteSession: (sessionId: string) => void;
  /** Callback when session ID is copied */
  onCopySessionId: (sessionId: string, e: React.MouseEvent) => void;
  /** Currently copied session ID (for UI feedback) */
  copiedSessionId: string | null;
  /** Loading state for sessions */
  loadingSessions?: boolean;
  /** Function to extract medical keywords from session preview */
  extractMedicalInfo: (preview: string) => string[];
  /** Optional callback to add new patient */
  onAddPatient?: () => void;
  /** Optional callback to open session audit panel */
  onAuditSession?: (sessionId: string) => void;
}

export const PatientSelector: React.FC<PatientSelectorProps> = ({
  patients,
  sessions,
  sessionStatuses,
  sessionCounts = {},
  onSelectPatient,
  onEditPatient,
  onSelectSession,
  onDeleteSession,
  onCopySessionId,
  copiedSessionId,
  loadingSessions = false,
  extractMedicalInfo,
  onAddPatient
}) => {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* LEFT: Patient List - 2/3 width */}
      <div className="lg:col-span-2">
        <PatientList
          patients={patients}
          onSelectPatient={onSelectPatient}
          onEditPatient={onEditPatient}
          onAddPatient={onAddPatient}
          sessionCounts={sessionCounts}
        />
      </div>

      {/* RIGHT: Session List - 1/3 width */}
      <div className="lg:col-span-1">
        <SessionList
          sessions={sessions}
          sessionStatuses={sessionStatuses}
          onSelectSession={onSelectSession}
          onDeleteSession={onDeleteSession}
          onCopySessionId={onCopySessionId}
          copiedSessionId={copiedSessionId}
          loading={loadingSessions}
          extractMedicalInfo={extractMedicalInfo}
        />
      </div>
    </div>
  );
};
