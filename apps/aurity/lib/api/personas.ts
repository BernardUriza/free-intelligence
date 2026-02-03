/**
 * Personas API Client
 *
 * Functions for managing AI personas (SOAP Editor, Clinical Advisor, etc.)
 */

import type {
  Persona,
  PersonaCreateRequest,
  PersonaUpdateRequest,
  PersonaTestRequest,
  PersonaTestResponse,
} from '@aurity-standalone/types/persona';
import { api } from './client';

const API_BASE = '/api/admin/personas';

/**
 * Fetch all personas
 */
export async function fetchPersonas(): Promise<Persona[]> {
  const data = await api.get<{ personas: Persona[] }>(API_BASE);
  return data.personas;
}

/**
 * Fetch a specific persona by ID
 */
export async function fetchPersona(personaId: string): Promise<Persona> {
  return api.get<Persona>(`${API_BASE}/${personaId}`);
}

/**
 * Update a persona configuration
 */
export async function updatePersona(
  personaId: string,
  updates: PersonaUpdateRequest
): Promise<Persona> {
  return api.put<Persona>(`${API_BASE}/${personaId}`, updates);
}

/**
 * Test a persona with sample input
 */
export async function testPersona(
  personaId: string,
  testRequest: PersonaTestRequest
): Promise<PersonaTestResponse> {
  return api.post<PersonaTestResponse>(`${API_BASE}/${personaId}/test`, testRequest);
}

/**
 * Create a new persona (FI-superadmin only)
 *
 * Note: Auth token is now handled automatically by api client
 * from Auth0 cache - no need to pass explicitly.
 *
 * @param data - New persona configuration
 * @returns Created persona
 * @throws Error if creation fails (403 if not superadmin, 409 if ID exists)
 */
export async function createPersona(data: PersonaCreateRequest): Promise<Persona> {
  return api.post<Persona>(API_BASE, data);
}

/**
 * Delete a persona (FI-superadmin only)
 *
 * Deletes the persona template and all user overrides.
 * Some personas (general_assistant, soap_editor) are protected and cannot be deleted.
 *
 * Note: Auth token is now handled automatically by api client
 * from Auth0 cache - no need to pass explicitly.
 *
 * @param personaId - Persona identifier to delete
 * @throws Error if deletion fails (400 if protected, 403 if not superadmin, 404 if not found)
 */
export async function deletePersona(personaId: string): Promise<void> {
  await api.delete<void>(`${API_BASE}/${personaId}`);
}
