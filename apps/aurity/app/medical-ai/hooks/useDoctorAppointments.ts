/**
 * useDoctorAppointments Hook
 *
 * Manages appointments for the current doctor in medical-ai workflow.
 * Fetches weekly appointments and provides CRUD operations.
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import type { Appointment } from '@/types/checkin';
import {
  fetchAppointmentsAPI,
  createAppointmentAPI,
  updateAppointmentAPI,
} from '@/services/appointmentService';

interface CreateAppointmentData {
  patient_id: string;
  scheduled_at: string | Date;
  appointment_type?: string;
  estimated_duration?: number;
  reason?: string;
  notes?: string;
}

interface UseDoctorAppointmentsResult {
  // Data
  appointments: Appointment[];
  todayAppointments: Appointment[];
  loading: boolean;
  error: string | null;

  // Date navigation
  currentDate: Date;
  setCurrentDate: (date: Date) => void;
  weekRange: { start: Date; end: Date };

  // Actions
  createAppointment: (data: CreateAppointmentData) => Promise<Appointment>;
  startAppointment: (appointmentId: string) => Promise<Appointment>;
  refetch: () => Promise<void>;
}

function getWeekRange(date: Date): { start: Date; end: Date } {
  const start = new Date(date);
  start.setDate(date.getDate() - date.getDay()); // Sunday
  start.setHours(0, 0, 0, 0);

  const end = new Date(start);
  end.setDate(start.getDate() + 6); // Saturday
  end.setHours(23, 59, 59, 999);

  return { start, end };
}

function isToday(date: Date): boolean {
  const today = new Date();
  return (
    date.getDate() === today.getDate() &&
    date.getMonth() === today.getMonth() &&
    date.getFullYear() === today.getFullYear()
  );
}

export function useDoctorAppointments(
  doctorId: string | undefined,
  clinicId: string | undefined
): UseDoctorAppointmentsResult {
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentDate, setCurrentDate] = useState<Date>(new Date());

  const weekRange = useMemo(() => getWeekRange(currentDate), [currentDate]);

  // Filter today's appointments
  const todayAppointments = useMemo(() => {
    return appointments.filter((apt) => {
      const aptDate = new Date(apt.scheduled_at);
      return isToday(aptDate);
    });
  }, [appointments]);

  // Fetch appointments for the week
  const fetchAppointments = useCallback(async () => {
    if (!clinicId || !doctorId) {
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Fetch each day of the week
      const days: Date[] = [];
      const current = new Date(weekRange.start);
      while (current <= weekRange.end) {
        days.push(new Date(current));
        current.setDate(current.getDate() + 1);
      }

      const results = await Promise.all(
        days.map((day) => fetchAppointmentsAPI(clinicId, day))
      );

      // Flatten and filter by doctor
      const allAppointments = results
        .flat()
        .filter((apt) => apt.doctor_id === doctorId);

      // Remove duplicates by appointment_id
      const uniqueAppointments = Array.from(
        new Map(allAppointments.map((apt) => [apt.appointment_id, apt])).values()
      );

      setAppointments(uniqueAppointments);
    } catch (err) {
      console.error('[useDoctorAppointments] Error:', err);
      setError(err instanceof Error ? err.message : 'Error al cargar citas');
    } finally {
      setLoading(false);
    }
  }, [clinicId, doctorId, weekRange.start, weekRange.end]);

  // Fetch on mount and when dependencies change
  useEffect(() => {
    fetchAppointments();
  }, [fetchAppointments]);

  // Create new appointment
  const createAppointment = useCallback(
    async (data: CreateAppointmentData): Promise<Appointment> => {
      if (!clinicId || !doctorId) {
        throw new Error('No clinic or doctor configured');
      }

      const appointmentData = {
        patient_id: data.patient_id,
        doctor_id: doctorId,
        scheduled_at: data.scheduled_at,
        appointment_type: data.appointment_type || 'follow_up',
        estimated_duration: data.estimated_duration || 30,
        reason: data.reason || '',
        notes: data.notes || '',
      };

      const created = await createAppointmentAPI(clinicId, appointmentData);

      // Add to local state
      setAppointments((prev) => [...prev, created]);

      return created;
    },
    [clinicId, doctorId]
  );

  // Start appointment (mark as in_progress)
  const startAppointment = useCallback(
    async (appointmentId: string): Promise<Appointment> => {
      if (!clinicId) {
        throw new Error('No clinic configured');
      }

      const updated = await updateAppointmentAPI(clinicId, appointmentId, {
        status: 'in_progress',
        started_at: new Date().toISOString(),
      });

      // Update local state
      setAppointments((prev) =>
        prev.map((apt) =>
          apt.appointment_id === appointmentId ? updated : apt
        )
      );

      return updated;
    },
    [clinicId]
  );

  return {
    appointments,
    todayAppointments,
    loading,
    error,
    currentDate,
    setCurrentDate,
    weekRange,
    createAppointment,
    startAppointment,
    refetch: fetchAppointments,
  };
}
