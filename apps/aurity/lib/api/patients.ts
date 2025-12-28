/**
 * Patient API Client
 *
 * Type-safe client for PostgreSQL patient management
 * Connects to FastAPI backend (/api/patients)
 *
 * P1 FIX: Uses centralized API client instead of hardcoded fetch
 */

import { api } from './client';

// Backend API types (matching backend/api/public/patients.py schemas)
export interface PatientCreate {
  nombre: string;
  apellido: string;
  fecha_nacimiento: string; // ISO date string "YYYY-MM-DD"
  curp?: string | null;
}

export interface PatientUpdate {
  nombre?: string;
  apellido?: string;
  fecha_nacimiento?: string;
  curp?: string | null;
}

export interface PatientResponse {
  patient_id: string; // UUID
  nombre: string;
  apellido: string;
  fecha_nacimiento: string;
  curp: string | null;
  created_at: string;
  updated_at: string | null;
}

// Frontend Patient type (converted from backend)
export interface Patient {
  id: string;
  name: string;
  age: number;
  gender: 'Masculino' | 'Femenino' | 'Otro';
  medicalHistory?: string[];
  allergies?: string[];
  chronicConditions?: string[];
  currentMedications?: string[];
  // Backend fields
  curp?: string | null;
  fechaNacimiento: string; // ISO date string "YYYY-MM-DD" - for edit operations
  createdAt: string;
  updatedAt?: string | null;
}

/**
 * Convert backend PatientResponse to frontend Patient type
 */
function toFrontendPatient(p: PatientResponse): Patient {
  const birthDate = new Date(p.fecha_nacimiento);
  const age = Math.floor((Date.now() - birthDate.getTime()) / (365.25 * 24 * 60 * 60 * 1000));

  return {
    id: p.patient_id,
    name: `${p.nombre} ${p.apellido}`,
    age,
    gender: 'Otro', // TODO: Add gender field to backend schema
    curp: p.curp,
    fechaNacimiento: p.fecha_nacimiento,
    createdAt: p.created_at,
    updatedAt: p.updated_at || undefined,
    medicalHistory: [], // TODO: Implement in future
    allergies: [], // TODO: Implement in future
    chronicConditions: [], // TODO: Implement in future
    currentMedications: [], // TODO: Implement in future
  };
}

/**
 * Fetch all patients with optional search
 */
export async function fetchPatients(params?: {
  search?: string;
  limit?: number;
  offset?: number;
}): Promise<Patient[]> {
  const queryParams = new URLSearchParams();
  if (params?.search) queryParams.set('search', params.search);
  if (params?.limit) queryParams.set('limit', params.limit.toString());
  if (params?.offset) queryParams.set('offset', params.offset.toString());

  // P1 FIX: Use API client instead of hardcoded fetch
  const query = queryParams.toString();
  const data = await api.get<PatientResponse[]>(`/api/patients/${query ? `?${query}` : ''}`);
  return data.map(toFrontendPatient);
}

/**
 * Fetch single patient by ID
 */
export async function fetchPatient(patientId: string): Promise<Patient> {
  // P1 FIX: Use API client instead of hardcoded fetch
  try {
    const data = await api.get<PatientResponse>(`/api/patients/${patientId}`);
    return toFrontendPatient(data);
  } catch (error: any) {
    if (error?.status === 404) {
      throw new Error('Patient not found');
    }
    throw error;
  }
}

/**
 * Create new patient
 */
export async function createPatient(patient: PatientCreate): Promise<Patient> {
  try {
    const data = await api.post<PatientResponse>('/api/patients/', patient);
    return toFrontendPatient(data);
  } catch (error: unknown) {
    // Parse backend error message for user-friendly display
    if (error && typeof error === 'object' && 'message' in error) {
      const msg = (error as { message: string }).message;
      try {
        const parsed = JSON.parse(msg);
        if (parsed.detail) {
          throw new Error(typeof parsed.detail === 'string' ? parsed.detail : JSON.stringify(parsed.detail));
        }
      } catch {
        // Not JSON, use as-is
      }
    }
    throw error;
  }
}

/**
 * Update existing patient
 */
export async function updatePatient(patientId: string, updates: PatientUpdate): Promise<Patient> {
  // P1 FIX: Use API client instead of hardcoded fetch
  const data = await api.put<PatientResponse>(`/api/patients/${patientId}`, updates);
  return toFrontendPatient(data);
}

/**
 * Delete patient
 */
export async function deletePatient(patientId: string): Promise<void> {
  // P1 FIX: Use API client instead of hardcoded fetch
  await api.delete(`/api/patients/${patientId}`);
}
