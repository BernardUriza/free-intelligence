/**
 * Appointments Transform Utilities
 * Card: FI-CHECKIN-005 (Phase 2)
 *
 * Transform medical appointments data to Bryntum format.
 */

import type { BryntumEvent, BryntumResource } from '../types/scheduler.types';
import { getAppointmentColor, getSpecialtyColor } from '../config/appointment-features.config';

/**
 * Doctor availability per day (0 = Sunday)
 */
export interface WorkingHour {
  day?: number;
  start: string; // HH:mm
  end: string;   // HH:mm
  date?: string; // Optional ISO date override (YYYY-MM-DD)
  fullDayClosed?: boolean;
  reason?: string;
  legacyDerived?: boolean;
}

/**
 * Doctor entity from backend
 */
export interface Doctor {
  doctor_id: string;
  nombre: string;
  apellido: string;
  display_name: string | null;
  especialidad: string | null;
  avg_consultation_minutes: number;
  work_start_time: string | null; // e.g., "09:00" (24h format)
  work_end_time: string | null;   // e.g., "18:00" (24h format)
  working_hours?: WorkingHour[];
}

/**
 * Appointment entity from backend
 */
export interface Appointment {
  appointment_id: string;
  clinic_id: string;
  patient_id: string;
  doctor_id: string;
  scheduled_at: string;
  estimated_duration: number;
  appointment_type: string;
  status: string;
  checkin_code: string;
  reason: string | null;
  notes?: string | null; // Optional notes field
  patient_name?: string; // Optional - fetched separately
}

/**
 * Transform Doctor to Bryntum Resource
 * 
 * @param doctor - Doctor entity
 * @returns Bryntum resource configuration with working hours
 */
export function transformDoctor(doctor: Doctor): BryntumResource {
  const resource: BryntumResource = {
    id: doctor.doctor_id,
    name: doctor.display_name || `${doctor.nombre} ${doctor.apellido}`,
    specialty: doctor.especialidad,
    eventColor: getSpecialtyColor(doctor.especialidad),
    // Additional metadata
    avgConsultationMinutes: doctor.avg_consultation_minutes,
  };

  // Store working hours in resource data for resourceTimeRanges
  if (doctor.work_start_time && doctor.work_end_time) {
    resource.workStartTime = doctor.work_start_time;
    resource.workEndTime = doctor.work_end_time;
  }

  if (doctor.working_hours) {
    resource.workingHours = doctor.working_hours;
  }

  return resource;
}

/**
 * Transform Appointment to Bryntum Event
 * 
 * @param appointment - Appointment entity
 * @returns Bryntum event configuration
 */
export function transformAppointment(appointment: Appointment): BryntumEvent {
  // Parse dates with validation
  const startDate = new Date(appointment.scheduled_at);
  
  // Validate date is valid
  if (isNaN(startDate.getTime())) {
    console.error('Invalid scheduled_at date:', appointment.scheduled_at);
    // Fallback to current time
    startDate.setTime(Date.now());
  }
  
  const endDate = new Date(
    startDate.getTime() + (appointment.estimated_duration || 30) * 60000
  );

  return {
    id: appointment.appointment_id,
    resourceId: appointment.doctor_id,
    startDate,
    endDate,
    name: formatAppointmentType(appointment.appointment_type),
    
    // Appointment-specific data
    patient_name: appointment.patient_name || appointment.patient_id,
    patient_id: appointment.patient_id,
    checkin_code: appointment.checkin_code || '',
    reason: appointment.reason || null,
    appointment_type: appointment.appointment_type,
    status: appointment.status,
    clinic_id: appointment.clinic_id,
    
    // Visual properties
    eventColor: getAppointmentColor(appointment.status),
    cls: `appointment-${appointment.status}`, // CSS class for styling
  };
}

/**
 * Transform array of doctors to Bryntum resources
 */
export function transformDoctors(doctors: Doctor[]): BryntumResource[] {
  return doctors.map(transformDoctor);
}

/**
 * Transform array of appointments to Bryntum events
 */
export function transformAppointments(appointments: Appointment[]): BryntumEvent[] {
  if (!Array.isArray(appointments)) {
    console.error('transformAppointments: Expected array, got:', typeof appointments);
    return [];
  }
  
  return appointments
    .filter((apt) => apt && apt.appointment_id) // Filter out invalid appointments
    .map(transformAppointment);
}

/**
 * Format appointment type for display
 */
function formatAppointmentType(type: string): string {
  const labels: Record<string, string> = {
    consulta: 'Consulta',
    seguimiento: 'Seguimiento',
    urgencia: 'Urgencia',
    procedimiento: 'Procedimiento',
    control: 'Control',
  };
  return labels[type] || type;
}

/**
 * Calculate appointment statistics
 */
export function calculateAppointmentStats(appointments: Appointment[]) {
  const total = appointments.length;
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const todayAppointments = appointments.filter((apt) => {
    const aptDate = new Date(apt.scheduled_at);
    aptDate.setHours(0, 0, 0, 0);
    return aptDate.getTime() === today.getTime();
  });

  const byStatus = appointments.reduce(
    (acc, apt) => {
      acc[apt.status] = (acc[apt.status] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  return {
    total,
    today: todayAppointments.length,
    byStatus,
  };
}
