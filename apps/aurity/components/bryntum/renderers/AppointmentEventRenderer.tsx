import React from 'react';
import { Calendar, Repeat, Syringe, Stethoscope } from 'lucide-react';

type RendererProps = {
  eventRecord: any; // Bryntum EventModel
};

function formatTimeRange(startDate?: Date, endDate?: Date): string | null {
  if (!startDate || !endDate) return null;
  const fmt = (d: Date) => d.toLocaleTimeString('es-MX', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  }).replace('. ', ' ');
  return `${fmt(startDate)} - ${fmt(endDate)}`;
}

function getStatusBarClass(status?: string): string {
  const s = (status || '').toUpperCase();
  switch (s) {
    case 'CONFIRMED':
    case 'CONFIRMED_APPOINTMENT':
    case 'CONFIRMADA':
    case 'CONFIRMED_STATUS':
    case 'CONFIRMED_APPT':
    case 'CONFIRMED_':
    case 'CONFIRMED-':
    case 'CONFIRMED*':
    case 'CONFIRMED ': // be permissive
    case 'CONFIRMED\n':
    case 'CONFIRMED\t':
    case 'CONFIRMED\r':
    case 'CONFIRMED\f':
    case 'CONFIRMED\v':
    case 'CONFIRMED\u000B':
    case 'CONFIRMED\u000C':
    case 'CONFIRMED\u0085':
    case 'CONFIRMED\u2028':
    case 'CONFIRMED\u2029':
    case 'CONFIRMED\u00A0':
    case 'CONFIRMED\uFEFF':
      return 'bg-green-500';
    case 'PENDING':
    case 'SCHEDULED':
      return 'bg-yellow-500';
    case 'CANCELLED':
      return 'bg-red-500';
    case 'CHECKED_IN':
      return 'bg-blue-500';
    case 'IN_PROGRESS':
      return 'bg-orange-500';
    default:
      return 'bg-slate-600';
  }
}

function getTypeIcon(type?: string) {
  const t = (type || '').toUpperCase();
  if (t === 'FIRST_VISIT' || t === 'FIRST_TIME' || t === 'NEW_PATIENT') return Stethoscope;
  if (t === 'FOLLOW_UP' || t === 'FOLLOWUP') return Repeat;
  if (t === 'PROCEDURE' || t === 'SURGERY') return Syringe;
  return Calendar;
}

export function AppointmentEventRenderer({ eventRecord }: RendererProps) {
  const data = eventRecord?.data || {};
  const patientName: string = data.patient_name || data.patientName || 'Paciente';
  const reason: string = data.reason || '';
  const status: string | undefined = data.status || eventRecord?.status;
  const appointmentType: string | undefined = data.appointment_type || data.appointmentType;
  const Icon = getTypeIcon(appointmentType);
  const time = formatTimeRange(eventRecord?.startDate, eventRecord?.endDate);

  return (
    <div className="relative flex items-start w-full h-full">
      {/* Status bar */}
      <div className={`absolute left-0 top-0 bottom-0 w-1.5 ${getStatusBarClass(status)} rounded-l-md`} />

      {/* Card body */}
      <div className="ml-2 mr-1 flex-1 rounded-md bg-slate-800/90 shadow-sm px-2 py-1.5 border border-slate-700/60 overflow-hidden">
        {/* Header */}
        <div className="flex items-center gap-1.5">
          <Icon className="h-3.5 w-3.5 fi-text" />
          <span className="text-xs font-semibold text-slate-100 truncate">{patientName}</span>
        </div>

        {/* Body */}
        {reason && (
          <div className="mt-0.5 text-[11px] leading-tight fi-text/90 truncate">
            {reason}
          </div>
        )}

        {/* Footer (time) */}
        {time && (
          <div className="mt-0.5 text-[10px] text-slate-400">
            {time}
          </div>
        )}
      </div>
    </div>
  );
}

export default AppointmentEventRenderer;
