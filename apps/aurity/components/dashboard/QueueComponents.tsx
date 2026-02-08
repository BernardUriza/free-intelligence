/**
 * Queue Components - Refactored queue display components
 *
 * Card: FI-UI-REFAC-001
 * Extracted from dashboard/page.tsx for better maintainability.
 * Includes accessibility improvements and performance optimizations.
 */

'use client';

import React, { memo } from 'react';
import { Bell, Timer, Users, Activity, Clock } from 'lucide-react';
import {
  ESTIMATED_MINUTES_PER_PATIENT,
  NEXT_PATIENTS_PREVIEW_COUNT,
  type QueuePatient,
} from '@/lib/dashboard/constants';

// =============================================================================
// TURNO ACTUAL - Giant ticket number display
// =============================================================================

interface TurnoActualProps {
  calledPatient: QueuePatient | undefined;
}

export const TurnoActual = memo(function TurnoActual({ calledPatient }: TurnoActualProps) {
  if (calledPatient) {
    return (
      <div
        className="que-turno-active"
        role="status"
        aria-live="assertive"
        aria-label={`Turno actual: ${calledPatient.ticketNumber}`}
        id="current-ticket"
        tabIndex={-1}
      >
        <Bell
          className="fi-text-success que-turno-icon"
          style={{ width: 'clamp(1.5rem, 4vw, 3rem)', height: 'clamp(1.5rem, 4vw, 3rem)' }}
          aria-hidden="true"
        />
        <div>
          <p
            className="fi-text-success/80 que-turno-label-active"
            style={{ fontSize: 'clamp(0.6rem, 1vw, 0.875rem)' }}
          >
            TURNO ACTUAL
          </p>
          <p
            className="que-turno-number-active"
            style={{ fontSize: 'clamp(2rem, 6vw, 5rem)' }}
          >
            {calledPatient.ticketNumber}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      className="que-turno-idle"
      role="status"
      aria-live="polite"
      aria-label="Sin turno activo actualmente"
    >
      <Timer
        className="que-turno-icon-idle"
        style={{ width: 'clamp(1.5rem, 4vw, 3rem)', height: 'clamp(1.5rem, 4vw, 3rem)' }}
        aria-hidden="true"
      />
      <div>
        <p
          className="que-turno-label-idle"
          style={{ fontSize: 'clamp(0.6rem, 1vw, 0.875rem)' }}
        >
          TURNO ACTUAL
        </p>
        <p
          className="que-turno-text-idle"
          style={{ fontSize: 'clamp(1.25rem, 3vw, 2.5rem)' }}
        >
          En espera...
        </p>
      </div>
    </div>
  );
});

// =============================================================================
// QUEUE STATS - Waiting count, in progress, estimated time
// =============================================================================

interface QueueStatsProps {
  waitingCount: number;
  inProgressCount: number;
}

export const QueueStats = memo(function QueueStats({
  waitingCount,
  inProgressCount,
}: QueueStatsProps) {
  const estimatedWaitTime = waitingCount * ESTIMATED_MINUTES_PER_PATIENT;

  return (
    <div
      className="que-stats-row"
      role="region"
      aria-label="Estadísticas de la cola"
    >
      {/* Waiting Count */}
      <div className="que-stat-cell">
        <div className="que-stat-icon-row">
          <Users
            className="fi-text-primary"
            style={{ width: 'clamp(0.875rem, 1.5vw, 1.25rem)', height: 'clamp(0.875rem, 1.5vw, 1.25rem)' }}
            aria-hidden="true"
          />
        </div>
        <p
          className="que-stat-value-blue"
          style={{ fontSize: 'clamp(1.5rem, 4vw, 3.5rem)' }}
          aria-label={`${waitingCount} pacientes en espera`}
        >
          {waitingCount}
        </p>
      </div>

      <div
        className="que-stat-divider"
        style={{ width: '1px', height: 'clamp(2rem, 5vw, 4rem)' }}
        aria-hidden="true"
      />

      {/* In Progress Count */}
      <div className="que-stat-cell">
        <div className="que-stat-icon-row">
          <Activity
            className="fi-text-purple"
            style={{ width: 'clamp(0.875rem, 1.5vw, 1.25rem)', height: 'clamp(0.875rem, 1.5vw, 1.25rem)' }}
            aria-hidden="true"
          />
        </div>
        <p
          className="que-stat-value-purple"
          style={{ fontSize: 'clamp(1.5rem, 4vw, 3.5rem)' }}
          aria-label={`${inProgressCount} en consulta`}
        >
          {inProgressCount}
        </p>
      </div>

      <div
        className="que-stat-divider"
        style={{ width: '1px', height: 'clamp(2rem, 5vw, 4rem)' }}
        aria-hidden="true"
      />

      {/* Estimated Wait Time */}
      <div className="que-stat-cell">
        <div className="que-stat-icon-row">
          <Clock
            className="fi-text-warning"
            style={{ width: 'clamp(0.875rem, 1.5vw, 1.25rem)', height: 'clamp(0.875rem, 1.5vw, 1.25rem)' }}
            aria-hidden="true"
          />
        </div>
        <p
          className="que-stat-value-amber"
          style={{ fontSize: 'clamp(1.5rem, 4vw, 3.5rem)' }}
          aria-label={`Tiempo estimado de espera: ${estimatedWaitTime} minutos`}
        >
          {estimatedWaitTime}
          <span
            className="fi-text-warning/60 que-stat-suffix"
            style={{ fontSize: 'clamp(0.75rem, 1.5vw, 1.25rem)' }}
          >
            min
          </span>
        </p>
      </div>
    </div>
  );
});

// =============================================================================
// NEXT IN QUEUE - Upcoming patients preview
// =============================================================================

interface NextInQueueProps {
  patients: QueuePatient[];
}

export const NextInQueue = memo(function NextInQueue({ patients }: NextInQueueProps) {
  const waitingPatients = patients.filter(p => p.status === 'waiting');

  if (waitingPatients.length === 0) return null;

  return (
    <div
      className="que-next-row"
      role="list"
      aria-label="Próximos turnos"
    >
      <p
        className="que-next-label"
        style={{ fontSize: 'clamp(0.6rem, 1vw, 0.875rem)' }}
      >
        Próximos:
      </p>
      <div className="que-next-badges">
        {waitingPatients.slice(0, NEXT_PATIENTS_PREVIEW_COUNT).map((p, i) => (
          <span
            key={p.ticketNumber}
            role="listitem"
            className={i === 0 ? 'que-next-badge-first' : 'que-next-badge'}
            style={{
              fontSize: 'clamp(0.75rem, 1.2vw, 1rem)',
              padding: 'clamp(0.25rem, 0.5vw, 0.5rem) clamp(0.5rem, 1vw, 0.75rem)',
              borderRadius: 'clamp(0.25rem, 0.5vw, 0.5rem)',
            }}
          >
            {p.ticketNumber}
          </span>
        ))}
        {waitingPatients.length > NEXT_PATIENTS_PREVIEW_COUNT && (
          <span
            className="que-next-more"
            style={{ fontSize: 'clamp(0.6rem, 1vw, 0.75rem)' }}
          >
            +{waitingPatients.length - NEXT_PATIENTS_PREVIEW_COUNT}
          </span>
        )}
      </div>
    </div>
  );
});

// =============================================================================
// QUEUE STATUS BAR - Complete bar combining all components
// =============================================================================

interface DoctorInfo {
  id: string;
  name: string;
  specialty?: string;
  available: boolean;
}

interface ClinicInfo {
  id: string;
  name: string;
  location?: string;
  phone?: string;
}

interface QueueStatusBarProps {
  patients: QueuePatient[];
  doctors?: DoctorInfo[];
  clinic?: ClinicInfo;
}

export const QueueStatusBar = memo(function QueueStatusBar({ patients, doctors, clinic }: QueueStatusBarProps) {
  const waitingCount = patients.filter(p => p.status === 'waiting').length;
  const calledPatient = patients.find(p => p.status === 'called');
  const inProgressCount = patients.filter(p => p.status === 'in_progress').length;

  return (
    <div
      className="que-statusbar-wrap fi-border-bottom/50"
      role="region"
      aria-label="Estado de la cola de pacientes"
    >
      <div className="que-statusbar-inner">
        <div className="que-statusbar-row">
          {/* Giant Turno Display */}
          <div className="que-statusbar-turno">
            <TurnoActual calledPatient={calledPatient} />
          </div>

          {/* Queue Statistics */}
          <QueueStats waitingCount={waitingCount} inProgressCount={inProgressCount} />

          {/* Next in Queue Preview */}
          <NextInQueue patients={patients} />

          {/* Right-side info: Doctors availability + Clinic card */}
          {(doctors?.length || clinic) && (
            <div className="que-statusbar-right">
              {clinic && <ClinicCard clinic={clinic} />}
              {doctors && doctors.length > 0 && <DoctorAvailabilityList doctors={doctors} />}
            </div>
          )}
        </div>
      </div>
    </div>
  );
});

// =============================================================================
// QUICK STATS CARD - Interactive stat card for control panel
// =============================================================================

interface QuickStatCardProps {
  icon: typeof Users;
  iconColor: string;
  label: string;
  value: number | string;
  suffix?: string;
  onClick?: () => void;
  highlight?: boolean;
}

export const QuickStatCard = memo(function QuickStatCard({
  icon: Icon,
  iconColor,
  label,
  value,
  suffix,
  onClick,
  highlight = false,
}: QuickStatCardProps) {
  const Component = onClick ? 'button' : 'div';

  return (
    <Component
      onClick={onClick}
      className={`que-stat-card ${onClick ? 'que-stat-card-clickable' : ''} ${highlight ? 'que-stat-card-highlight' : ''}`}
      aria-label={`${label}: ${value}${suffix || ''}`}
    >
      <div className="que-stat-header">
        <Icon className={`que-stat-icon ${iconColor}`} aria-hidden="true" />
        <span className="fi-text-xs">{label}</span>
      </div>
      <p className="fi-title-2xl">
        {value}
        {suffix && <span className="fi-subtitle que-stat-suffix">{suffix}</span>}
      </p>
    </Component>
  );
});

// =============================================================================
// DOCTORS + CLINIC - Compact info blocks for the status bar
// =============================================================================

function AvailabilityDot({ online }: { online: boolean }) {
  return (
    <span
      className={`que-avail-dot ${online ? 'que-avail-dot-online' : 'que-avail-dot-offline'}`}
      aria-hidden="true"
    />
  );
}

export function DoctorAvailabilityList({ doctors }: { doctors: DoctorInfo[] }) {
  return (
    <div
      className="que-doctor-list"
      role="region"
      aria-label="Doctores disponibles"
    >
      <div className="fi-text-xs que-doctor-list-label">Doctores disponibles</div>
      <ul className="que-doctor-list-items">
        {doctors.slice(0, 4).map((d) => (
          <li key={d.id} className="que-doctor-item">
            <AvailabilityDot online={d.available} />
            <span className={d.available ? 'que-doctor-name' : 'que-doctor-name-off'}>{d.name}</span>
            {d.specialty && (
              <span className="que-doctor-spec">· {d.specialty}</span>
            )}
          </li>
        ))}
        {doctors.length > 4 && (
          <li className="fi-text-xs-muted">+{doctors.length - 4} más</li>
        )}
      </ul>
    </div>
  );
}

export function ClinicCard({ clinic }: { clinic: ClinicInfo }) {
  return (
    <div
      className="que-clinic-card"
      role="region"
      aria-label="Clinica actual"
    >
      <div className="fi-text-xs que-clinic-label">Clínica</div>
      <div className="que-clinic-name">{clinic.name}</div>
      {clinic.location && (
        <div className="fi-text-xs">{clinic.location}</div>
      )}
      {clinic.phone && (
        <div className="fi-text-xs-muted que-clinic-phone">Tel: {clinic.phone}</div>
      )}
    </div>
  );
}
