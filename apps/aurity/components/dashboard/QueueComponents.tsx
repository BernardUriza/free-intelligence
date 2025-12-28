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
        className="flex items-center gap-3 sm:gap-4 md:gap-5 px-4 sm:px-5 md:px-6 lg:px-8 py-2 sm:py-3 md:py-4 bg-emerald-500/20 border-2 border-emerald-500/50 rounded-xl sm:rounded-2xl shadow-lg shadow-emerald-500/20 animate-pulse"
        role="status"
        aria-live="assertive"
        aria-label={`Turno actual: ${calledPatient.ticketNumber}`}
        id="current-ticket"
        tabIndex={-1}
      >
        <Bell
          className="fi-text-success flex-shrink-0"
          style={{ width: 'clamp(1.5rem, 4vw, 3rem)', height: 'clamp(1.5rem, 4vw, 3rem)' }}
          aria-hidden="true"
        />
        <div>
          <p
            className="fi-text-success/80 font-bold tracking-widest"
            style={{ fontSize: 'clamp(0.6rem, 1vw, 0.875rem)' }}
          >
            TURNO ACTUAL
          </p>
          <p
            className="font-black text-emerald-300 tracking-wider leading-none"
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
      className="flex items-center gap-3 sm:gap-4 px-4 sm:px-5 md:px-6 py-2 sm:py-3 md:py-4 bg-slate-800/60 border-2 border-slate-700 rounded-xl sm:rounded-2xl"
      role="status"
      aria-live="polite"
      aria-label="Sin turno activo actualmente"
    >
      <Timer
        className="text-slate-500 flex-shrink-0"
        style={{ width: 'clamp(1.5rem, 4vw, 3rem)', height: 'clamp(1.5rem, 4vw, 3rem)' }}
        aria-hidden="true"
      />
      <div>
        <p
          className="text-slate-500 font-bold tracking-widest"
          style={{ fontSize: 'clamp(0.6rem, 1vw, 0.875rem)' }}
        >
          TURNO ACTUAL
        </p>
        <p
          className="font-medium text-slate-400"
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
      className="flex items-center justify-center gap-4 sm:gap-6 md:gap-8 lg:gap-10"
      role="region"
      aria-label="Estadísticas de la cola"
    >
      {/* Waiting Count */}
      <div className="text-center">
        <div className="flex items-center justify-center gap-1 sm:gap-2 mb-1">
          <Users
            className="fi-text-primary"
            style={{ width: 'clamp(0.875rem, 1.5vw, 1.25rem)', height: 'clamp(0.875rem, 1.5vw, 1.25rem)' }}
            aria-hidden="true"
          />
        </div>
        <p
          className="font-bold text-blue-300"
          style={{ fontSize: 'clamp(1.5rem, 4vw, 3.5rem)' }}
          aria-label={`${waitingCount} pacientes en espera`}
        >
          {waitingCount}
        </p>
      </div>

      <div
        className="bg-slate-700"
        style={{ width: '1px', height: 'clamp(2rem, 5vw, 4rem)' }}
        aria-hidden="true"
      />

      {/* In Progress Count */}
      <div className="text-center">
        <div className="flex items-center justify-center gap-1 sm:gap-2 mb-1">
          <Activity
            className="fi-text-purple"
            style={{ width: 'clamp(0.875rem, 1.5vw, 1.25rem)', height: 'clamp(0.875rem, 1.5vw, 1.25rem)' }}
            aria-hidden="true"
          />
        </div>
        <p
          className="font-bold text-purple-300"
          style={{ fontSize: 'clamp(1.5rem, 4vw, 3.5rem)' }}
          aria-label={`${inProgressCount} en consulta`}
        >
          {inProgressCount}
        </p>
      </div>

      <div
        className="bg-slate-700"
        style={{ width: '1px', height: 'clamp(2rem, 5vw, 4rem)' }}
        aria-hidden="true"
      />

      {/* Estimated Wait Time */}
      <div className="text-center">
        <div className="flex items-center justify-center gap-1 sm:gap-2 mb-1">
          <Clock
            className="fi-text-warning"
            style={{ width: 'clamp(0.875rem, 1.5vw, 1.25rem)', height: 'clamp(0.875rem, 1.5vw, 1.25rem)' }}
            aria-hidden="true"
          />
        </div>
        <p
          className="font-bold text-amber-300"
          style={{ fontSize: 'clamp(1.5rem, 4vw, 3.5rem)' }}
          aria-label={`Tiempo estimado de espera: ${estimatedWaitTime} minutos`}
        >
          {estimatedWaitTime}
          <span
            className="fi-text-warning/60 ml-1"
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
      className="hidden md:flex items-center gap-2 sm:gap-3"
      role="list"
      aria-label="Próximos turnos"
    >
      <p
        className="text-slate-500"
        style={{ fontSize: 'clamp(0.6rem, 1vw, 0.875rem)' }}
      >
        Próximos:
      </p>
      <div className="flex items-center gap-1 sm:gap-2">
        {waitingPatients.slice(0, NEXT_PATIENTS_PREVIEW_COUNT).map((p, i) => (
          <span
            key={p.ticketNumber}
            role="listitem"
            className={`font-mono font-medium ${
              i === 0
                ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                : 'bg-slate-800 text-slate-400 border border-slate-700'
            }`}
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
            className="text-slate-500"
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
      className="bg-slate-900/90 backdrop-blur-sm fi-border-bottom/50"
      role="region"
      aria-label="Estado de la cola de pacientes"
    >
      <div className="w-full px-3 sm:px-4 md:px-6 lg:px-8 py-2 sm:py-3 md:py-4">
        <div className="flex flex-col xl:flex-row items-center justify-between gap-3 sm:gap-4 md:gap-6">
          {/* Giant Turno Display */}
          <div className="flex justify-center sm:justify-start">
            <TurnoActual calledPatient={calledPatient} />
          </div>

          {/* Queue Statistics */}
          <QueueStats waitingCount={waitingCount} inProgressCount={inProgressCount} />

          {/* Next in Queue Preview */}
          <NextInQueue patients={patients} />

          {/* Right-side info: Doctors availability + Clinic card */}
          {(doctors?.length || clinic) && (
            <div className="w-full xl:w-auto flex items-stretch gap-3 sm:gap-4">
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
      className={`
        bg-slate-800/50 border border-slate-700 rounded-xl p-4
        transition-all duration-200
        ${onClick ? 'cursor-pointer hover:scale-[1.02] hover:bg-slate-800/70 hover:border-slate-600 active:scale-[0.98]' : ''}
        ${highlight ? 'ring-2 ring-emerald-500/50' : ''}
      `}
      aria-label={`${label}: ${value}${suffix || ''}`}
    >
      <div className="flex items-center gap-2 mb-2">
        <Icon className={`w-4 h-4 ${iconColor}`} aria-hidden="true" />
        <span className="fi-text-xs">{label}</span>
      </div>
      <p className="fi-title-2xl">
        {value}
        {suffix && <span className="fi-subtitle ml-1">{suffix}</span>}
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
      className={`inline-block w-2 h-2 rounded-full ${online ? 'bg-emerald-500' : 'bg-slate-500'}`}
      aria-hidden="true"
    />
  );
}

export function DoctorAvailabilityList({ doctors }: { doctors: DoctorInfo[] }) {
  return (
    <div
      className="flex-1 xl:flex-none min-w-[240px] bg-slate-800/50 border border-slate-700 rounded-xl px-3 py-2"
      role="region"
      aria-label="Doctores disponibles"
    >
      <div className="fi-text-xs mb-1">Doctores disponibles</div>
      <ul className="space-y-1">
        {doctors.slice(0, 4).map((d) => (
          <li key={d.id} className="flex items-center gap-2 text-sm">
            <AvailabilityDot online={d.available} />
            <span className={`text-slate-200 ${!d.available ? 'opacity-60' : ''}`}>{d.name}</span>
            {d.specialty && (
              <span className="text-slate-500 text-xs truncate">· {d.specialty}</span>
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
      className="flex-1 xl:flex-none min-w-[220px] bg-slate-800/50 border border-slate-700 rounded-xl px-3 py-2"
      role="region"
      aria-label="Clinica actual"
    >
      <div className="fi-text-xs mb-1">Clínica</div>
      <div className="text-sm text-white font-semibold">{clinic.name}</div>
      {clinic.location && (
        <div className="fi-text-xs">{clinic.location}</div>
      )}
      {clinic.phone && (
        <div className="fi-text-xs-muted mt-1">Tel: {clinic.phone}</div>
      )}
    </div>
  );
}
