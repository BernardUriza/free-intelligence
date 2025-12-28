/**
 * Persona Service
 *
 * Centralized API layer for Persona management.
 * Single Responsibility: Only handles HTTP communication.
 * All methods include proper error handling and auth token support.
 *
 * @module services/persona
 */

import type {
  Persona,
  PersonaCreateRequest,
  PersonaUpdateRequest,
  PersonaTestResponse,
} from '@/components/admin/persona/types';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:7001';
const BASE_PATH = '/api/admin/personas';

/**
 * Error thrown by persona service operations
 */
export class PersonaServiceError extends Error {
  constructor(
    message: string,
    public readonly statusCode?: number,
    public readonly detail?: string
  ) {
    super(message);
    this.name = 'PersonaServiceError';
  }
}

/**
 * Parse error response from API
 */
async function parseErrorResponse(response: Response): Promise<string> {
  try {
    const data = await response.json();
    return data.detail || data.message || response.statusText;
  } catch {
    return response.statusText;
  }
}

/**
 * Build headers with optional auth token
 */
function buildHeaders(authToken?: string): HeadersInit {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };

  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }

  return headers;
}

/**
 * Persona Service - All API operations for Persona management
 */
export const personaService = {
  /**
   * List all personas
   */
  async list(): Promise<Persona[]> {
    const response = await fetch(`${BACKEND_URL}${BASE_PATH}`, {
      method: 'GET',
      headers: buildHeaders(),
    });

    if (!response.ok) {
      const detail = await parseErrorResponse(response);
      throw new PersonaServiceError(
        `Failed to fetch personas: ${detail}`,
        response.status,
        detail
      );
    }

    const data = await response.json();
    return data.personas;
  },

  /**
   * Get a single persona by ID
   */
  async get(personaId: string): Promise<Persona> {
    const response = await fetch(`${BACKEND_URL}${BASE_PATH}/${personaId}`, {
      method: 'GET',
      headers: buildHeaders(),
    });

    if (!response.ok) {
      const detail = await parseErrorResponse(response);
      throw new PersonaServiceError(
        `Failed to fetch persona ${personaId}: ${detail}`,
        response.status,
        detail
      );
    }

    return response.json();
  },

  /**
   * Create a new persona (requires FI-superadmin role)
   */
  async create(data: PersonaCreateRequest, authToken: string): Promise<Persona> {
    const response = await fetch(`${BACKEND_URL}${BASE_PATH}`, {
      method: 'POST',
      headers: buildHeaders(authToken),
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const detail = await parseErrorResponse(response);

      // Provide user-friendly error messages
      if (response.status === 403) {
        throw new PersonaServiceError(
          'No tienes permisos para crear personas',
          403,
          detail
        );
      }
      if (response.status === 409) {
        throw new PersonaServiceError(
          `Ya existe una persona con el ID "${data.id}"`,
          409,
          detail
        );
      }

      throw new PersonaServiceError(
        `Error al crear la persona: ${detail}`,
        response.status,
        detail
      );
    }

    return response.json();
  },

  /**
   * Update an existing persona
   */
  async update(
    personaId: string,
    updates: PersonaUpdateRequest,
    authToken?: string
  ): Promise<Persona> {
    const response = await fetch(`${BACKEND_URL}${BASE_PATH}/${personaId}`, {
      method: 'PUT',
      headers: buildHeaders(authToken),
      body: JSON.stringify(updates),
    });

    if (!response.ok) {
      const detail = await parseErrorResponse(response);

      if (response.status === 403) {
        throw new PersonaServiceError(
          'No tienes permisos para modificar esta persona',
          403,
          detail
        );
      }
      if (response.status === 404) {
        throw new PersonaServiceError(
          `Persona "${personaId}" no encontrada`,
          404,
          detail
        );
      }

      throw new PersonaServiceError(
        `Error al actualizar la persona: ${detail}`,
        response.status,
        detail
      );
    }

    return response.json();
  },

  /**
   * Delete a persona (requires FI-superadmin role)
   */
  async delete(personaId: string, authToken: string): Promise<void> {
    const response = await fetch(`${BACKEND_URL}${BASE_PATH}/${personaId}`, {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${authToken}`,
      },
    });

    if (!response.ok) {
      const detail = await parseErrorResponse(response);

      if (response.status === 400) {
        throw new PersonaServiceError(
          `No se puede eliminar la persona "${personaId}" (protegida)`,
          400,
          detail
        );
      }
      if (response.status === 403) {
        throw new PersonaServiceError(
          'No tienes permisos para eliminar personas',
          403,
          detail
        );
      }
      if (response.status === 404) {
        throw new PersonaServiceError(
          `Persona "${personaId}" no encontrada`,
          404,
          detail
        );
      }

      throw new PersonaServiceError(
        `Error al eliminar la persona: ${detail}`,
        response.status,
        detail
      );
    }
  },

  /**
   * Test a persona with sample input
   */
  async test(
    personaId: string,
    input: string,
    userId?: string
  ): Promise<PersonaTestResponse> {
    const url = new URL(`${BACKEND_URL}${BASE_PATH}/${personaId}/test`);
    if (userId) {
      url.searchParams.set('user_id', userId);
    }

    const response = await fetch(url.toString(), {
      method: 'POST',
      headers: buildHeaders(),
      body: JSON.stringify({ input }),
    });

    if (!response.ok) {
      const detail = await parseErrorResponse(response);
      throw new PersonaServiceError(
        `Error al probar la persona: ${detail}`,
        response.status,
        detail
      );
    }

    return response.json();
  },
};

export default personaService;
