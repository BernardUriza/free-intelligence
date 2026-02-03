/**
 * Appointment Service
 *
 * API layer for clinic appointment management.
 * Updated: 2026-02 - Migrated to centralized api client
 */

import { api } from '@/lib/api/client';
import { toastError } from "@/lib/swal";
import type { Appointment, Doctor } from "@/components/bryntum/utils/appointment-transform.utils";

export interface Clinic {
  clinic_id: string;
  name: string;
}

export async function fetchClinicsAPI(): Promise<Clinic[]> {
  try {
    const data = await api.get<{ clinics: Clinic[] }>('/api/clinics');
    return data.clinics || [];
  } catch (error) {
    console.error("Failed to fetch clinics:", error);
    toastError("Failed to fetch clinics");
    return [];
  }
}

export async function fetchDoctorsAPI(clinicId: string): Promise<Doctor[]> {
  try {
    const data = await api.get<{ doctors: Doctor[] }>(`/api/clinics/${clinicId}/doctors`);
    return data.doctors || [];
  } catch (error) {
    console.error("Failed to fetch doctors:", error);
    toastError("Failed to fetch doctors");
    return [];
  }
}

export async function fetchAppointmentsAPI(clinicId: string, date: Date): Promise<Appointment[]> {
  try {
    const dateStr = date.toISOString().split("T")[0];
    const data = await api.get<{ appointments: Appointment[] }>(
      `/api/clinics/${clinicId}/appointments?date=${dateStr}`
    );
    return data.appointments || [];
  } catch (error) {
    console.error("Failed to fetch appointments:", error);
    toastError("Failed to fetch appointments");
    return [];
  }
}

export async function updateAppointmentAPI(
  clinicId: string,
  appointmentId: string,
  data: Partial<Appointment>
): Promise<Appointment> {
  return api.patch<Appointment>(
    `/api/clinics/${clinicId}/appointments/${appointmentId}`,
    data
  );
}

export async function createAppointmentAPI(
  clinicId: string,
  appointmentData: Record<string, unknown>
): Promise<Appointment> {
  // Support both ISO string and Date for scheduled_at
  const scheduledAt = (() => {
    const v = appointmentData.scheduled_at;
    if (!v) return undefined;
    if (typeof v === 'string') return v;
    try { return (v as Date).toISOString(); } catch { return undefined; }
  })();

  const payload = { ...appointmentData, scheduled_at: scheduledAt };

  return api.post<Appointment>(
    `/api/clinics/${clinicId}/appointments`,
    payload
  );
}
