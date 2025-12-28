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

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:7001';

/**
 * Fetch all personas
 */
export async function fetchPersonas(): Promise<Persona[]> {
  const response = await fetch(`${BACKEND_URL}/api/admin/personas`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch personas: ${response.statusText}`);
  }

  const data = await response.json();
  return data.personas;
}

/**
 * Fetch a specific persona by ID
 */
export async function fetchPersona(personaId: string): Promise<Persona> {
  const response = await fetch(`${BACKEND_URL}/api/admin/personas/${personaId}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch persona ${personaId}: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Update a persona configuration
 */
export async function updatePersona(
  personaId: string,
  updates: PersonaUpdateRequest
): Promise<Persona> {
  const response = await fetch(`${BACKEND_URL}/api/admin/personas/${personaId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(updates),
  });

  if (!response.ok) {
    throw new Error(`Failed to update persona ${personaId}: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Test a persona with sample input
 */
export async function testPersona(
  personaId: string,
  testRequest: PersonaTestRequest
): Promise<PersonaTestResponse> {
  const response = await fetch(`${BACKEND_URL}/api/admin/personas/${personaId}/test`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(testRequest),
  });

  if (!response.ok) {
    throw new Error(`Failed to test persona ${personaId}: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Create a new persona (FI-superadmin only)
 *
 * @param data - New persona configuration
 * @param authToken - Auth0 JWT token for authentication
 * @returns Created persona
 * @throws Error if creation fails (403 if not superadmin, 409 if ID exists)
 */
export async function createPersona(
  data: PersonaCreateRequest,
  authToken: string
): Promise<Persona> {
  const response = await fetch(`${BACKEND_URL}/api/admin/personas`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${authToken}`,
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `Failed to create persona: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Delete a persona (FI-superadmin only)
 *
 * Deletes the persona template and all user overrides.
 * Some personas (general_assistant, soap_editor) are protected and cannot be deleted.
 *
 * @param personaId - Persona identifier to delete
 * @param authToken - Auth0 JWT token for authentication
 * @throws Error if deletion fails (400 if protected, 403 if not superadmin, 404 if not found)
 */
export async function deletePersona(
  personaId: string,
  authToken: string
): Promise<void> {
  const response = await fetch(`${BACKEND_URL}/api/admin/personas/${personaId}`, {
    method: 'DELETE',
    headers: {
      Authorization: `Bearer ${authToken}`,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `Failed to delete persona ${personaId}: ${response.statusText}`);
  }
}
