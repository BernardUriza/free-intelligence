"use client";

/**
 * Mini Calendar Preview for Onboarding
 * Card: FI-CHECKIN-005
 *
 * Lightweight calendar preview showing how appointments will look.
 * Uses CSS-only rendering (no Bryntum) for fast loading in onboarding.
 */

import { useState } from "react";
import { Calendar, ChevronLeft, ChevronRight, Clock, User } from "lucide-react";
import { Button } from "@/components/ui/button";

interface DemoAppointment {
  id: string;
  time: string;
  duration: number; // minutes
  patient: string;
  doctor: string;
  type: string;
  status: "scheduled" | "confirmed" | "checked_in" | "in_progress" | "completed";
}

interface DemoDoctor {
  id: string;
  name: string;
  specialty: string;
  color: string;
}

// Demo data for onboarding
const DEMO_DOCTORS: DemoDoctor[] = [
  { id: "doc1", name: "Dr. García", specialty: "Medicina General", color: "blue" },
  { id: "doc2", name: "Dra. Martínez", specialty: "Pediatría", color: "green" },
  { id: "doc3", name: "Dr. López", specialty: "Cardiología", color: "red" },
];

const DEMO_APPOINTMENTS: DemoAppointment[] = [
  { id: "1", time: "09:00", duration: 30, patient: "Juan Pérez", doctor: "doc1", type: "Consulta", status: "completed" },
  { id: "2", time: "09:30", duration: 45, patient: "María García", doctor: "doc2", type: "Control", status: "completed" },
  { id: "3", time: "10:00", duration: 30, patient: "Carlos Ruiz", doctor: "doc1", type: "Seguimiento", status: "in_progress" },
  { id: "4", time: "10:30", duration: 30, patient: "Ana López", doctor: "doc3", type: "Urgencia", status: "checked_in" },
  { id: "5", time: "11:00", duration: 45, patient: "Pedro Sánchez", doctor: "doc2", type: "Consulta", status: "confirmed" },
  { id: "6", time: "11:30", duration: 30, patient: "Laura Torres", doctor: "doc1", type: "Control", status: "scheduled" },
  { id: "7", time: "12:00", duration: 30, patient: "Roberto Díaz", doctor: "doc3", type: "Consulta", status: "scheduled" },
];

const STATUS_COLORS: Record<DemoAppointment["status"], { bg: string; border: string; text: string }> = {
  scheduled: { bg: "bg-blue-500/20", border: "border-blue-500/40", text: "text-blue-300" },
  confirmed: { bg: "bg-green-500/20", border: "border-green-500/40", text: "text-green-300" },
  checked_in: { bg: "bg-teal-500/20", border: "border-teal-500/40", text: "text-teal-300" },
  in_progress: { bg: "bg-orange-500/20", border: "border-orange-500/40", text: "text-orange-300" },
  completed: { bg: "bg-slate-500/20", border: "border-slate-500/40", text: "text-slate-400" },
};

const STATUS_LABELS: Record<DemoAppointment["status"], string> = {
  scheduled: "Programada",
  confirmed: "Confirmada",
  checked_in: "Check-in",
  in_progress: "En curso",
  completed: "Completada",
};

const HOURS = ["09:00", "10:00", "11:00", "12:00", "13:00"];

export function MiniCalendarPreview() {
  const [selectedAppointment, setSelectedAppointment] = useState<DemoAppointment | null>(null);
  const [currentDate] = useState(new Date());

  const getAppointmentsForDoctor = (doctorId: string) => {
    return DEMO_APPOINTMENTS.filter((apt) => apt.doctor === doctorId);
  };

  const getAppointmentStyle = (apt: DemoAppointment) => {
    const startHour = parseInt(apt.time.split(":")[0]);
    const startMinute = parseInt(apt.time.split(":")[1]);
    const top = ((startHour - 9) * 60 + startMinute) * 0.8; // 0.8px per minute
    const height = apt.duration * 0.8;
    return { top: `${top}px`, height: `${height}px` };
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="fi-flex-between">
        <div className="fi-flex-gap">
          <Calendar className="h-5 w-5 fi-text-info" />
          <h3 className="text-lg font-semibold text-slate-200">Agenda de Citas</h3>
        </div>
        <div className="flex items-center gap-2 text-sm">
            <Button className="p-1 hover:bg-slate-700 rounded" variant="ghost" size="sm" title="Anterior">
              <ChevronLeft className="h-4 w-4 text-slate-400" />
            </Button>
          <span className="fi-text font-medium">
            {currentDate.toLocaleDateString("es-MX", { weekday: "short", day: "numeric", month: "short" })}
          </span>
            <Button className="p-1 hover:bg-slate-700 rounded" variant="ghost" size="sm" title="Siguiente">
              <ChevronRight className="h-4 w-4 text-slate-400" />
            </Button>
        </div>
      </div>

      {/* Mini Scheduler Grid */}
      <div className="bg-slate-950/50 rounded-lg border border-slate-700/50 overflow-hidden">
        {/* Doctor Headers */}
        <div className="grid grid-cols-4 fi-border-bottom/50">
          <div className="p-2 fi-text-xs-muted font-medium">Hora</div>
          {DEMO_DOCTORS.map((doc) => (
            <div key={doc.id} className="p-2 border-l border-slate-700/50">
              <p className="text-xs font-semibold fi-text">{doc.name}</p>
              <p className="text-[10px] text-slate-500">{doc.specialty}</p>
            </div>
          ))}
        </div>

        {/* Time Grid */}
        <div className="relative">
          {/* Hour Lines */}
          <div className="grid grid-cols-4">
            <div className="relative">
              {HOURS.map((hour) => (
                <div key={hour} className="h-12 border-b border-slate-800/50 flex items-start">
                  <span className="text-[10px] text-slate-600 px-2 -mt-1">{hour}</span>
                </div>
              ))}
            </div>

            {/* Doctor Columns with Appointments */}
            {DEMO_DOCTORS.map((doc) => (
              <div key={doc.id} className="relative border-l border-slate-700/50">
                {/* Hour grid lines */}
                {HOURS.map((hour) => (
                  <div key={hour} className="h-12 border-b border-slate-800/50" />
                ))}

                {/* Appointments */}
                <div className="absolute inset-0 p-0.5">
                  {getAppointmentsForDoctor(doc.id).map((apt) => {
                    const style = getAppointmentStyle(apt);
                    const colors = STATUS_COLORS[apt.status];
                    return (
                      <div
                        key={apt.id}
                        className={`absolute left-0.5 right-0.5 ${colors.bg} border ${colors.border} rounded cursor-pointer transition-all hover:scale-[1.02] hover:shadow-lg`}
                        style={style}
                        onClick={() => setSelectedAppointment(apt)}
                      >
                        <div className="p-1 overflow-hidden">
                          <p className={`text-[9px] font-semibold ${colors.text} truncate`}>
                            {apt.patient}
                          </p>
                          <p className="text-[8px] text-slate-500 truncate">{apt.type}</p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Status Legend */}
      <div className="flex flex-wrap gap-3 text-[10px]">
        {Object.entries(STATUS_COLORS).map(([status, colors]) => (
          <div key={status} className="fi-flex-gap-sm">
            <span className={`w-2 h-2 rounded-full ${colors.bg} border ${colors.border}`} />
            <span className="text-slate-400">{STATUS_LABELS[status as DemoAppointment["status"]]}</span>
          </div>
        ))}
      </div>

      {/* Selected Appointment Details */}
      {selectedAppointment && (
        <div className="p-3 bg-slate-900/50 border border-slate-700/50 rounded-lg animate-fade-in-up">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <User className="h-4 w-4 fi-text-info" />
                <span className="text-sm font-semibold text-slate-200">{selectedAppointment.patient}</span>
              </div>
              <div className="flex items-center gap-2 fi-text-xs">
                <Clock className="h-3 w-3" />
                <span>{selectedAppointment.time} ({selectedAppointment.duration} min)</span>
                <span>·</span>
                <span>{selectedAppointment.type}</span>
              </div>
            </div>
            <span className={`text-[10px] px-2 py-0.5 rounded ${STATUS_COLORS[selectedAppointment.status].bg} ${STATUS_COLORS[selectedAppointment.status].text}`}>
              {STATUS_LABELS[selectedAppointment.status]}
            </span>
          </div>
          <p className="text-[10px] text-slate-500 mt-2">
            Doctor: {DEMO_DOCTORS.find((d) => d.id === selectedAppointment.doctor)?.name}
          </p>
        </div>
      )}

      {/* Feature Highlights */}
      <div className="grid grid-cols-2 gap-2 mt-4">
        <div className="p-2 bg-emerald-950/20 border border-emerald-700/30 rounded-lg">
          <p className="text-[10px] font-semibold text-emerald-300">Drag & Drop</p>
          <p className="text-[9px] text-slate-400">Arrastra citas entre doctores y horarios</p>
        </div>
        <div className="p-2 bg-cyan-950/20 border border-cyan-700/30 rounded-lg">
          <p className="text-[10px] font-semibold text-cyan-300">Vistas Múltiples</p>
          <p className="text-[9px] text-slate-400">Día, Semana y Mes disponibles</p>
        </div>
        <div className="p-2 bg-purple-950/20 border border-purple-700/30 rounded-lg">
          <p className="text-[10px] font-semibold text-purple-300">Check-in QR</p>
          <p className="text-[9px] text-slate-400">Pacientes confirman con código</p>
        </div>
        <div className="p-2 bg-yellow-950/20 border border-yellow-700/30 rounded-lg">
          <p className="text-[10px] font-semibold text-yellow-300">Notificaciones</p>
          <p className="text-[9px] text-slate-400">SMS y Email automáticos</p>
        </div>
      </div>
    </div>
  );
}
