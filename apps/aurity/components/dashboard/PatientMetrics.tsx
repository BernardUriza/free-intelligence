/**
 * PatientMetrics - Patient-Friendly Dashboard Metrics
 *
 * Card: FI-UI-FEAT-TVD-001
 * Displays simple, understandable metrics for waiting room TV
 * Focus: Patient experience, not technical KPIs
 */

'use client';

import { Users, Clock, ClipboardList } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

interface MetricCardProps {
  icon: LucideIcon;
  label: string;
  value: string;
  sublabel?: string;
  color: 'emerald' | 'blue' | 'purple' | 'orange';
}

function MetricCard({ icon: Icon, label, value, sublabel, color }: MetricCardProps) {
  const colorClasses = {
    emerald: {
      border: 'border-emerald-600/40',
      bg: 'bg-emerald-950/20',
      glow: 'shadow-emerald-500/10',
      text: 'fi-text-success',
      sublabel: 'fi-text-success/60',
    },
    blue: {
      border: 'border-blue-600/40',
      bg: 'bg-blue-950/20',
      glow: 'shadow-blue-500/10',
      text: 'fi-text-primary',
      sublabel: 'fi-text-primary/60',
    },
    purple: {
      border: 'border-purple-600/40',
      bg: 'bg-purple-950/20',
      glow: 'shadow-purple-500/10',
      text: 'fi-text-purple',
      sublabel: 'fi-text-purple/60',
    },
    orange: {
      border: 'border-orange-600/40',
      bg: 'bg-orange-950/20',
      glow: 'shadow-orange-500/10',
      text: 'text-orange-400',
      sublabel: 'text-orange-400/60',
    },
  };

  const theme = colorClasses[color];

  return (
    <div
      className={`
        p-6 rounded-xl
        border ${theme.border}
        ${theme.bg}
        backdrop-blur-sm
        shadow-lg ${theme.glow}
        transition-all duration-300
        hover:shadow-xl
      `}
    >
      {/* Icon + Label */}
      <div className="flex items-center gap-3 mb-4">
        <div className={theme.text}>
          <Icon className="w-10 h-10" strokeWidth={1.5} />
        </div>
        <div className="flex-1">
          <p className="fi-subtitle font-medium">{label}</p>
        </div>
      </div>

      {/* Value */}
      <div className={`text-3xl font-bold ${theme.text} mb-1`}>
        {value}
      </div>

      {/* Sublabel */}
      {sublabel && (
        <p className={`text-xs ${theme.sublabel} font-medium`}>
          {sublabel}
        </p>
      )}
    </div>
  );
}

interface PatientMetricsProps {
  /** Number of patients currently waiting */
  waitingCount?: number;

  /** Average wait time in minutes */
  avgWaitTime?: number;

  /** Patients seen today */
  patientsToday?: number;

  /** Next appointment time (HH:MM format) */
  nextAppointment?: string | null;
}

export function PatientMetrics({
  waitingCount = 0,
  avgWaitTime = 0,
  patientsToday = 0,
  nextAppointment = null,
}: PatientMetricsProps) {
  // Format wait time
  const formatWaitTime = (minutes: number): string => {
    if (minutes < 60) return `${minutes} min`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return mins > 0 ? `${hours}h ${mins}min` : `${hours}h`;
  };

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {/* Patients Waiting */}
      <MetricCard
        icon={Users}
        label="En Sala de Espera"
        value={waitingCount.toString()}
        sublabel={waitingCount === 1 ? 'paciente' : 'pacientes'}
        color="blue"
      />

      {/* Average Wait Time */}
      <MetricCard
        icon={Clock}
        label="Tiempo de Espera"
        value={formatWaitTime(avgWaitTime)}
        sublabel="promedio aproximado"
        color="orange"
      />

      {/* Patients Today */}
      <MetricCard
        icon={ClipboardList}
        label="Consultas Hoy"
        value={patientsToday.toString()}
        sublabel="pacientes atendidos"
        color="emerald"
      />

      {/* Next Appointment */}
      <MetricCard
        icon={Clock}
        label="Próxima Cita"
        value={nextAppointment || '--:--'}
        sublabel={nextAppointment ? 'hora estimada' : 'sin citas pendientes'}
        color="purple"
      />
    </div>
  );
}
