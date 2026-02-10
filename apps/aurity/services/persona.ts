/**
 * Persona Service
 *
 * Centralized API layer for Persona management.
 * Single Responsibility: Only handles HTTP communication.
 *
 * Updated: 2026-02 - Migrated to centralized api client
 *
 * @module services/persona
 */

import type {
  Persona,
  PersonaCreateRequest,
  PersonaUpdateRequest,
  PersonaTestResponse,
} from '@/components/admin/persona/types';
import { api, APIError } from '@/lib/api/client';
import { ROUTES } from '@/lib/api/routes';

const BASE_PATH = ROUTES.adminPersonas;

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
 * Convert APIError to PersonaServiceError with user-friendly messages
 */
function handleError(error: unknown, context: string): never {
  if (error instanceof APIError) {
    throw new PersonaServiceError(
      `${context}: ${error.message}`,
      error.status,
      error.message
    );
  }
  throw new PersonaServiceError(
    error instanceof Error ? error.message : String(error)
  );
}

/**
 * Persona Service - All API operations for Persona management
 */
export const personaService = {
  /**
   * List all personas
   */
  async list(): Promise<Persona[]> {
    try {
      const data = await api.get<{ personas: Persona[] }>(BASE_PATH);
      return data.personas;
    } catch (error) {
      handleError(error, 'Failed to fetch personas');
    }
  },

  /**
   * Get a single persona by ID
   */
  async get(personaId: string): Promise<Persona> {
    try {
      return await api.get<Persona>(`${BASE_PATH}/${personaId}`);
    } catch (error) {
      handleError(error, `Failed to fetch persona ${personaId}`);
    }
  },

  /**
   * Create a new persona (requires FI-superadmin role)
   * Note: Auth token is now handled automatically by api client
   */
  async create(data: PersonaCreateRequest): Promise<Persona> {
    try {
      return await api.post<Persona>(BASE_PATH, data);
    } catch (error) {
      if (error instanceof APIError) {
        if (error.status === 403) {
          throw new PersonaServiceError(
            'No tienes permisos para crear personas',
            403,
            error.message
          );
        }
        if (error.status === 409) {
          throw new PersonaServiceError(
            `Ya existe una persona con el ID "${data.id}"`,
            409,
            error.message
          );
        }
      }
      handleError(error, 'Error al crear la persona');
    }
  },

  /**
   * Update an existing persona
   * Note: Auth token is now handled automatically by api client
   */
  async update(personaId: string, updates: PersonaUpdateRequest): Promise<Persona> {
    try {
      return await api.put<Persona>(`${BASE_PATH}/${personaId}`, updates);
    } catch (error) {
      if (error instanceof APIError) {
        if (error.status === 403) {
          throw new PersonaServiceError(
            'No tienes permisos para modificar esta persona',
            403,
            error.message
          );
        }
        if (error.status === 404) {
          throw new PersonaServiceError(
            `Persona "${personaId}" no encontrada`,
            404,
            error.message
          );
        }
      }
      handleError(error, 'Error al actualizar la persona');
    }
  },

  /**
   * Delete a persona (requires FI-superadmin role)
   * Note: Auth token is now handled automatically by api client
   */
  async delete(personaId: string): Promise<void> {
    try {
      await api.delete(`${BASE_PATH}/${personaId}`);
    } catch (error) {
      if (error instanceof APIError) {
        if (error.status === 400) {
          throw new PersonaServiceError(
            `No se puede eliminar la persona "${personaId}" (protegida)`,
            400,
            error.message
          );
        }
        if (error.status === 403) {
          throw new PersonaServiceError(
            'No tienes permisos para eliminar personas',
            403,
            error.message
          );
        }
        if (error.status === 404) {
          throw new PersonaServiceError(
            `Persona "${personaId}" no encontrada`,
            404,
            error.message
          );
        }
      }
      handleError(error, 'Error al eliminar la persona');
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
    try {
      const queryString = userId ? `?user_id=${encodeURIComponent(userId)}` : '';
      return await api.post<PersonaTestResponse>(
        `${BASE_PATH}/${personaId}/test${queryString}`,
        { input }
      );
    } catch (error) {
      handleError(error, 'Error al probar la persona');
    }
  },
};

export default personaService;
