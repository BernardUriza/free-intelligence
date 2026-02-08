/**
 * TodayAppointments - Mini agenda del día para el dashboard del doctor
 *
 * Card: FI-CHECKIN-006
 * Shows today's appointments in a compact list with status indicators
 *
 * Features:
 * - Auto-refresh every 30 seconds
 * - Status color coding
 * - Check-in code display
 * - Click to view details
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  Calendar,
  Clock,
  User,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  ChevronRight,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { api } from '@/lib/api/client';

// =============================================================================
// TYPES
// =============================================================================

interface Appointment {
  appointment_id: string;
  clinic_id: string;
  patient_id: string;
  doctor_id: string;
  scheduled_at: string;
  estimated_duration: number;
  appointment_type: string;
  status: AppointmentStatus;
  checkin_code: string;
  reason: string | null;
}

type AppointmentStatus =
  | 'scheduled'
  | 'confirmed'
  | 'checked_in'
  | 'in_progress'
  | 'completed'
  | 'cancelled'
  | 'no_show';

interface TodayAppointmentsProps {
  clinicId: string;
  doctorId?: string;
  onAppointmentClick?: (appointment: Appointment) => void;
  compact?: boolean;
}

// =============================================================================
// STATUS STYLING
// =============================================================================

const STATUS_CONFIG: Record<
  AppointmentStatus,
  { label: string; color: string; bgColor: string; icon: typeof CheckCircle2 }
> = {
  scheduled: {
    label: 'Programada',
    color: 'fi-text-primary',
    bgColor: 'bg-blue-500/20',
    icon: Clock,
  },
  confirmed: {
    label: 'Confirmada',
    color: 'fi-text-green',
    bgColor: 'bg-green-500/20',
    icon: CheckCircle2,
  },
  checked_in: {
    label: 'Check-in',
    color: 'text-teal-400',
    bgColor: 'bg-teal-500/20',
    icon: CheckCircle2,
  },
  in_progress: {
    label: 'En curso',
    color: 'text-orange-400',
    bgColor: 'bg-orange-500/20',
    icon: Clock,
  },
  completed: {
    label: 'Completada',
    color: 'text-slate-400',
    bgColor: 'bg-slate-500/20',
    icon: CheckCircle2,
  },
  cancelled: {
    label: 'Cancelada',
    color: 'fi-text-error',
    bgColor: 'bg-red-500/20',
    icon: AlertCircle,
  },
  no_show: {
    label: 'No asistió',
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-500/20',
    icon: AlertCircle,
  },
};

const APPOINTMENT_TYPE_LABELS: Record<string, string> = {
  first_visit: 'Primera visita',
  follow_up: 'Seguimiento',
  urgent: 'Urgencia',
  procedure: 'Procedimiento',
  telemedicine: 'Telemedicina',
};

// =============================================================================
// COMPONENT
// =============================================================================

export function TodayAppointments({
  clinicId,
  doctorId,
  onAppointmentClick,
  compact = false,
}: TodayAppointmentsProps) {
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const fetchAppointments = useCallback(async () => {
    try {
      setError(null);
      const today = new Date().toISOString().split('T')[0];
      let url = `/api/aurity/clinic/clinics/${clinicId}/appointments?date=${today}`;
      if (doctorId) {
        url += `&doctor_id=${doctorId}`;
      }

      const data = await api.get<{ appointments: Appointment[] }>(url);
      setAppointments(data.appointments || []);
      setLastRefresh(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido');
    } finally {
      setLoading(false);
    }
  }, [clinicId, doctorId]);

  // Initial fetch and auto-refresh
  useEffect(() => {
    fetchAppointments();
    const interval = setInterval(fetchAppointments, 30000); // 30s refresh
    return () => clearInterval(interval);
  }, [fetchAppointments]);

  // Format time
  const formatTime = (isoDate: string) => {
    return new Date(isoDate).toLocaleTimeString('es-MX', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  };

  // Group by status for summary
  const statusCounts = appointments.reduce(
    (acc, apt) => {
      acc[apt.status] = (acc[apt.status] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <RefreshCw className="w-5 h-5 text-slate-400 animate-spin" />
        <span className="ml-2 fi-subtitle">Cargando citas...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-950/20 border border-red-700/30 rounded-lg">
        <div className="flex items-center gap-2 fi-text-error">
          <AlertCircle className="w-4 h-4" />
          <span className="text-sm">{error}</span>
        </div>
        <Button
          onClick={fetchAppointments}
          variant="ghost"
          size="sm"
          className="mt-2 text-red-300 hover:text-red-200"
        >
          Reintentar
        </Button>
      </div>
    );
  }

  return (
    <div className={compact ? '' : 'bg-slate-800/50 border border-slate-700 rounded-lg'}>
      {/* Header */}
      <div className={`flex items-center justify-between ${compact ? 'mb-3' : 'px-4 py-3 fi-border-bottom'}`}>
        <div className="fi-flex-gap">
          <Calendar className="w-4 h-4 fi-text-info" />
          <span className="fi-title-sm-medium">Citas de Hoy</span>
          <span className="fi-text-xs">({appointments.length})</span>
        </div>
        <Button
          onClick={fetchAppointments}
          variant="ghost"
          size="sm"
          icon={RefreshCw}
          aria-label="Actualizar"
        />
      </div>

      {/* Status Summary */}
      {!compact && appointments.length > 0 && (
        <div className="px-4 py-2 bg-slate-900/50 fi-border-bottom flex flex-wrap gap-3">
          {Object.entries(statusCounts).map(([status, count]) => {
            const config = STATUS_CONFIG[status as AppointmentStatus];
            if (!config) return null;
            return (
              <div key={status} className="flex items-center gap-1.5">
                <span className={`w-2 h-2 rounded-full ${config.bgColor}`} />
                <span className="fi-text-xs">
                  {config.label}: <span className="text-slate-200">{count}</span>
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* Appointments List */}
      <div className={`${compact ? '' : 'p-2'} space-y-1 max-h-[400px] overflow-y-auto`}>
        {appointments.length === 0 ? (
          <div className="py-8 text-center">
            <Calendar className="w-10 h-10 text-slate-600 mx-auto mb-2" />
            <p className="fi-subtitle">No hay citas programadas para hoy</p>
          </div>
        ) : (
          appointments.map((apt) => {
            const statusConfig = STATUS_CONFIG[apt.status] || STATUS_CONFIG.scheduled;
            const StatusIcon = statusConfig.icon;

            return (
              <Button
                key={apt.appointment_id}
                onClick={() => onAppointmentClick?.(apt)}
                className="w-full flex items-center gap-3 p-3 bg-slate-900/50 hover:bg-slate-800 border border-slate-700/50 hover:border-slate-600 rounded-lg transition-all text-left group"
                variant="ghost"
                size="sm"
                type="button"
              >
                {/* Time */}
                <div className="flex-shrink-0 w-14 text-center">
                  <span className="fi-title">
                    {formatTime(apt.scheduled_at)}
                  </span>
                </div>

                {/* Status indicator */}
                <div
                  className={`flex-shrink-0 w-8 h-8 rounded-full ${statusConfig.bgColor} flex items-center justify-center`}
                >
                  <StatusIcon className={`w-4 h-4 ${statusConfig.color}`} />
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="fi-flex-gap">
                    <User className="w-3.5 h-3.5 text-slate-500" />
                    <span className="text-sm text-white truncate">
                      Paciente {apt.patient_id.slice(0, 8)}...
                    </span>
                  </div>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className={`text-xs ${statusConfig.color}`}>
                      {statusConfig.label}
                    </span>
                    <span className="text-slate-600">•</span>
                    <span className="fi-text-xs">
                      {APPOINTMENT_TYPE_LABELS[apt.appointment_type] || apt.appointment_type}
                    </span>
                  </div>
                </div>

                {/* Check-in code */}
                <div className="flex-shrink-0 text-right">
                  <div className="text-[10px] text-slate-500 uppercase">Código</div>
                  <div className="font-mono text-sm fi-text-info">{apt.checkin_code}</div>
                </div>

                {/* Arrow */}
                <ChevronRight className="w-4 h-4 text-slate-600 group-hover:text-slate-400 transition-colors" />
              </Button>
            );
          })
        )}
      </div>

      {/* Footer */}
      {!compact && (
        <div className="px-4 py-2 fi-border-top flex items-center justify-between">
          <span className="text-[10px] text-slate-500">
            Actualizado: {lastRefresh.toLocaleTimeString('es-MX')}
          </span>
          <a
            href="/admin/appointments"
            className="text-xs fi-text-info hover:text-cyan-300 flex items-center gap-1"
          >
            Ver agenda completa
            <ChevronRight className="fi-icon-xs" />
          </a>
        </div>
      )}
    </div>
  );
}
