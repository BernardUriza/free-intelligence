/**
 * Patient API Client
 *
 * Type-safe client for PostgreSQL patient management
 * Connects to FastAPI backend (/api/patients)
 *
 * P1 FIX: Uses centralized API client instead of hardcoded fetch
 */

import { api, type RequestOptions } from './client';
import { ROUTES } from './routes';

// Gender enum matching backend
export type Gender = 'MASCULINO' | 'FEMENINO' | 'OTRO' | 'NO_ESPECIFICADO';

// CURP validation types
export interface CurpValidationRequest {
  curp: string;
  exclude_patient_id?: string | null;
}

export interface CurpValidationResponse {
  valid: boolean;
  available: boolean;
  message: string | null;
}

// Backend API types (matching backend/api/public/patients.py schemas)
export interface PatientCreate {
  nombre: string;
  apellido: string;
  fecha_nacimiento: string; // ISO date string "YYYY-MM-DD"
  genero?: Gender | null;
  curp?: string | null;
}

export interface PatientUpdate {
  nombre?: string;
  apellido?: string;
  fecha_nacimiento?: string;
  genero?: Gender | null;
  curp?: string | null;
}

export interface PatientResponse {
  patient_id: string; // UUID
  nombre: string;
  apellido: string;
  fecha_nacimiento: string;
  genero: string | null;
  curp: string | null;
  created_at: string;
  updated_at: string | null;
}

// Frontend Patient type (converted from backend)
export interface Patient {
  id: string;
  name: string;
  age: number;
  gender: 'Masculino' | 'Femenino' | 'Otro' | 'No especificado';
  medicalHistory?: string[];
  allergies?: string[];
  chronicConditions?: string[];
  currentMedications?: string[];
  // Backend fields
  genero?: Gender | null; // Raw backend value
  curp?: string | null;
  fechaNacimiento: string; // ISO date string "YYYY-MM-DD" - for edit operations
  createdAt: string;
  updatedAt?: string | null;
}

/**
 * Map backend gender enum to frontend display value
 */
function mapGenderToDisplay(genero: string | null): Patient['gender'] {
  switch (genero) {
    case 'MASCULINO':
      return 'Masculino';
    case 'FEMENINO':
      return 'Femenino';
    case 'OTRO':
      return 'Otro';
    default:
      return 'No especificado';
  }
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
    gender: mapGenderToDisplay(p.genero),
    genero: p.genero as Gender | null,
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
export async function fetchPatients(
  params?: {
    search?: string;
    limit?: number;
    offset?: number;
  },
  options?: RequestOptions
): Promise<Patient[]> {
  const queryParams = new URLSearchParams();
  if (params?.search) queryParams.set('search', params.search);
  if (params?.limit) queryParams.set('limit', params.limit.toString());
  if (params?.offset) queryParams.set('offset', params.offset.toString());

  // P1 FIX: Use API client instead of hardcoded fetch
  const query = queryParams.toString();
  const data = await api.get<PatientResponse[]>(
    `${ROUTES.patients}/${query ? `?${query}` : ''}`,
    options
  );
  return data.map(toFrontendPatient);
}

/**
 * Fetch single patient by ID
 */
export async function fetchPatient(patientId: string): Promise<Patient> {
  // P1 FIX: Use API client instead of hardcoded fetch
  try {
    const data = await api.get<PatientResponse>(`${ROUTES.patients}/${patientId}`);
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
    const data = await api.post<PatientResponse>(`${ROUTES.patients}/`, patient);
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
  const data = await api.put<PatientResponse>(`${ROUTES.patients}/${patientId}`, updates);
  return toFrontendPatient(data);
}

/**
 * Delete patient
 */
export async function deletePatient(patientId: string): Promise<void> {
  // P1 FIX: Use API client instead of hardcoded fetch
  await api.delete(`${ROUTES.patients}/${patientId}`);
}

/**
 * Validate CURP format and availability
 *
 * Checks:
 * 1. CURP format is valid (18 chars, matches Mexican CURP pattern)
 * 2. CURP is not already in use by another patient
 *
 * @param curp - CURP to validate
 * @param excludePatientId - Patient ID to exclude (for updates)
 * @returns Validation result with availability status
 */
export async function validateCurp(
  curp: string,
  excludePatientId?: string | null
): Promise<CurpValidationResponse> {
  try {
    const request: CurpValidationRequest = {
      curp,
      exclude_patient_id: excludePatientId,
    };
    return await api.post<CurpValidationResponse>(`${ROUTES.patients}/validate-curp`, request);
  } catch {
    // On network error, return a soft failure that doesn't block the form
    return {
      valid: true,
      available: true,
      message: 'No se pudo verificar. Se validará al guardar.',
    };
  }
}
