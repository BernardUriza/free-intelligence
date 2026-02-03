/**
 * Clinics API Client
 *
 * CRUD operations for clinic and doctor management.
 *
 * File: apps/aurity/lib/api/clinics.ts
 * Card: FI-CHECKIN-002
 * Created: 2025-11-22
 */

import type { DoctorAvailability } from '@/components/admin/clinics/availability-designer/types';
import { api } from './client';

// =============================================================================
// TYPES
// =============================================================================

export interface Clinic {
  clinic_id: string;
  name: string;
  specialty: string;
  timezone: string;
  welcome_message: string | null;
  primary_color: string | null;
  logo_url: string | null;
  checkin_qr_enabled: boolean;
  chat_enabled: boolean;
  payments_enabled: boolean;
  subscription_plan: string;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface ClinicCreate {
  name: string;
  specialty?: string;
  timezone?: string;
  welcome_message?: string;
  primary_color?: string;
  logo_url?: string;
  checkin_qr_enabled?: boolean;
  chat_enabled?: boolean;
  payments_enabled?: boolean;
  subscription_plan?: string;
}

export interface ClinicUpdate {
  name?: string;
  specialty?: string;
  timezone?: string;
  welcome_message?: string;
  primary_color?: string;
  logo_url?: string;
  checkin_qr_enabled?: boolean;
  chat_enabled?: boolean;
  payments_enabled?: boolean;
  subscription_plan?: string;
}

export type ClinicRole = 'OWNER' | 'ADMIN' | 'DOCTOR' | 'STAFF';

export interface Doctor {
  doctor_id: string;
  clinic_id: string;
  auth0_user_id: string | null;
  email: string | null;
  clinic_role: ClinicRole | null;
  nombre: string;
  apellido: string;
  display_name: string | null;
  especialidad: string | null;
  cedula_profesional: string | null;
  phone: string | null;
  avg_consultation_minutes: number;
  work_start_time: string | null;      // Legacy: e.g., "09:00" (24h format)
  work_end_time: string | null;        // Legacy: e.g., "18:00" (24h format)
  working_hours: DoctorAvailability | null; // New: Full availability config
  is_active: boolean;
  is_linked: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface DoctorCreate {
  nombre: string;
  apellido: string;
  display_name?: string;
  especialidad?: string;
  cedula_profesional?: string;
  email?: string;
  phone?: string;
  avg_consultation_minutes?: number;
  work_start_time?: string; // e.g., "09:00"
  work_end_time?: string;   // e.g., "18:00"
}

export interface DoctorUpdate {
  nombre?: string;
  apellido?: string;
  display_name?: string;
  especialidad?: string;
  cedula_profesional?: string;
  email?: string;
  phone?: string;
  avg_consultation_minutes?: number;
  work_start_time?: string;             // Legacy: e.g., "09:00"
  work_end_time?: string;               // Legacy: e.g., "18:00"
  working_hours?: DoctorAvailability;   // New: Full availability config
  is_active?: boolean;
}

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
  checkin_code_expires_at: string;
  reason: string | null;
  notes: string | null;
  created_at: string;
}

export interface AppointmentCreate {
  patient_id: string;
  doctor_id: string;
  scheduled_at: string;
  appointment_type?: string;
  estimated_duration?: number;
  reason?: string;
  notes?: string;
}

// =============================================================================
// CLINIC ENDPOINTS
// =============================================================================

export async function fetchClinics(activeOnly = true): Promise<Clinic[]> {
  const data = await api.get<{ clinics: Clinic[]; total: number }>(
    `/api/clinics?active_only=${activeOnly}`
  );
  return data.clinics;
}

export async function fetchClinic(clinicId: string): Promise<Clinic> {
  return api.get<Clinic>(`/api/clinics/${clinicId}`);
}

export async function createClinic(data: ClinicCreate): Promise<Clinic> {
  return api.post<Clinic>('/api/clinics', data);
}

export async function updateClinic(clinicId: string, data: ClinicUpdate): Promise<Clinic> {
  return api.patch<Clinic>(`/api/clinics/${clinicId}`, data);
}

export async function deleteClinic(clinicId: string): Promise<void> {
  await api.delete<void>(`/api/clinics/${clinicId}`);
}

// =============================================================================
// DOCTOR ENDPOINTS
// =============================================================================

export async function fetchDoctors(clinicId: string, activeOnly = true): Promise<Doctor[]> {
  const data = await api.get<{ doctors: Doctor[]; total: number }>(
    `/api/clinics/${clinicId}/doctors?active_only=${activeOnly}`
  );
  return data.doctors;
}

export async function fetchDoctor(clinicId: string, doctorId: string): Promise<Doctor> {
  return api.get<Doctor>(`/api/clinics/${clinicId}/doctors/${doctorId}`);
}

export async function createDoctor(clinicId: string, data: DoctorCreate): Promise<Doctor> {
  return api.post<Doctor>(`/api/clinics/${clinicId}/doctors`, data);
}

export async function updateDoctor(clinicId: string, doctorId: string, data: DoctorUpdate): Promise<Doctor> {
  return api.patch<Doctor>(`/api/clinics/${clinicId}/doctors/${doctorId}`, data);
}

export async function deleteDoctor(clinicId: string, doctorId: string): Promise<void> {
  await api.delete<void>(`/api/clinics/${clinicId}/doctors/${doctorId}`);
}

// =============================================================================
// APPOINTMENT ENDPOINTS
// =============================================================================

export async function fetchAppointments(
  clinicId: string,
  options?: { date?: string; doctor_id?: string; status?: string }
): Promise<Appointment[]> {
  const params = new URLSearchParams();
  if (options?.date) params.set('date', options.date);
  if (options?.doctor_id) params.set('doctor_id', options.doctor_id);
  if (options?.status) params.set('status', options.status);

  const data = await api.get<{ appointments: Appointment[] }>(
    `/api/clinics/${clinicId}/appointments?${params.toString()}`
  );
  return data.appointments;
}

export async function createAppointment(clinicId: string, data: AppointmentCreate): Promise<Appointment> {
  return api.post<Appointment>(`/api/clinics/${clinicId}/appointments`, data);
}

// =============================================================================
// USER-CLINIC MEMBERSHIP ENDPOINTS
// =============================================================================

export interface ClinicMembership {
  doctor_id: string;
  clinic_id: string;
  clinic_name: string;
  clinic_role: ClinicRole;
  nombre: string;
  apellido: string;
  display_name: string;
  especialidad: string | null;
  email: string | null;
  is_active: boolean;
}

export interface LinkToClinicRequest {
  clinic_id: string;
  role?: ClinicRole;
  nombre: string;
  apellido: string;
  especialidad?: string;
  cedula_profesional?: string;
}

export interface LinkToClinicResponse {
  success: boolean;
  message: string;
  membership: ClinicMembership | null;
}

/**
 * Get current user's clinic membership
 */
export async function getClinicMembership(
  auth0UserId: string,
  email?: string
): Promise<ClinicMembership | null> {
  const params = new URLSearchParams({ auth0_user_id: auth0UserId });
  if (email) params.append('email', email);

  const data = await api.get<ClinicMembership | { linked: false }>(
    `/api/users/me/clinic-membership?${params}`
  );

  // If not linked, data will have { linked: false }
  if ('linked' in data && data.linked === false) {
    return null;
  }

  return data as ClinicMembership;
}

/**
 * Link current user to a clinic (creates doctor record)
 */
export async function linkToClinic(
  auth0UserId: string,
  request: LinkToClinicRequest,
  email?: string
): Promise<LinkToClinicResponse> {
  const params = new URLSearchParams({ auth0_user_id: auth0UserId });
  if (email) params.append('email', email);

  return api.post<LinkToClinicResponse>(`/api/users/me/link-to-clinic?${params}`, request);
}

/**
 * Unlink current user from their clinic
 */
export async function unlinkFromClinic(auth0UserId: string): Promise<{ success: boolean; message: string }> {
  const params = new URLSearchParams({ auth0_user_id: auth0UserId });
  return api.delete<{ success: boolean; message: string }>(`/api/users/me/unlink-from-clinic?${params}`);
}

// =============================================================================
// ADMIN USER-CLINIC ASSIGNMENT ENDPOINTS
// =============================================================================

export interface AdminLinkUserRequest {
  auth0_user_id: string;
  email: string;
  clinic_id: string;
  role?: ClinicRole;
  nombre: string;
  apellido: string;
  especialidad?: string;
}

export interface AdminUserClinicInfo {
  auth0_user_id: string;
  email: string;
  doctor_id: string | null;
  clinic_id: string | null;
  clinic_name: string | null;
  clinic_role: ClinicRole | null;
  nombre: string | null;
  apellido: string | null;
  is_linked: boolean;
}

/**
 * Admin: Assign a user to a clinic
 */
export async function adminAssignUserToClinic(
  request: AdminLinkUserRequest
): Promise<LinkToClinicResponse> {
  return api.post<LinkToClinicResponse>('/api/users/me/admin/assign-to-clinic', request);
}

/**
 * Admin: Unassign a user from their clinic
 */
export async function adminUnassignUserFromClinic(
  auth0UserId: string
): Promise<{ success: boolean; message: string; clinic_id?: string }> {
  return api.delete<{ success: boolean; message: string; clinic_id?: string }>(
    `/api/users/me/admin/unassign-user/${encodeURIComponent(auth0UserId)}`
  );
}

/**
 * Admin: Get user's clinic assignment info
 */
export async function adminGetUserClinicInfo(
  auth0UserId: string
): Promise<AdminUserClinicInfo> {
  return api.get<AdminUserClinicInfo>(
    `/api/users/me/admin/user-clinic-info/${encodeURIComponent(auth0UserId)}`
  );
}

// =============================================================================
// DOCTOR LIMITS ENDPOINTS
// =============================================================================

export interface DoctorLimitInfo {
  current_count: number;
  max_allowed: number | null; // null = unlimited
  can_add: boolean;
  plan_name: string;
  plan_display_name: string;
  has_override: boolean;
}

export interface DoctorLimitError {
  error: 'DOCTOR_LIMIT_EXCEEDED';
  message: string;
  current_count: number;
  max_allowed: number;
  plan_name: string;
}

/**
 * Get doctor limit information for a clinic
 */
export async function fetchDoctorLimits(clinicId: string): Promise<DoctorLimitInfo> {
  return api.get<DoctorLimitInfo>(`/api/clinics/${clinicId}/doctor-limits`);
}

/**
 * Update doctor override for a clinic (superadmin only)
 */
export async function updateDoctorOverride(
  clinicId: string,
  maxDoctorsOverride: number | null
): Promise<Clinic> {
  return api.patch<Clinic>(`/api/clinics/${clinicId}/doctor-override`, {
    max_doctors_override: maxDoctorsOverride,
  });
}

/**
 * Create doctor with limit error handling
 */
export async function createDoctorWithLimitCheck(
  clinicId: string,
  data: DoctorCreate
): Promise<{ success: true; doctor: Doctor } | { success: false; error: DoctorLimitError }> {
  try {
    const doctor = await api.post<Doctor>(`/api/clinics/${clinicId}/doctors`, data);
    return { success: true, doctor };
  } catch (error) {
    // Check if this is a 403 with DOCTOR_LIMIT_EXCEEDED
    if (error instanceof Error && error.message.includes('DOCTOR_LIMIT_EXCEEDED')) {
      // Parse the error message to extract the limit info
      const match = error.message.match(/current_count[:\s]+(\d+)/);
      const maxMatch = error.message.match(/max_allowed[:\s]+(\d+)/);
      const planMatch = error.message.match(/plan_name[:\s]+"?([^",}]+)"?/);

      return {
        success: false,
        error: {
          error: 'DOCTOR_LIMIT_EXCEEDED',
          message: error.message,
          current_count: match ? parseInt(match[1]) : 0,
          max_allowed: maxMatch ? parseInt(maxMatch[1]) : 0,
          plan_name: planMatch ? planMatch[1] : 'unknown',
        },
      };
    }
    throw error;
  }
}
