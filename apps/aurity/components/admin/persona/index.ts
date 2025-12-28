/**
 * Persona Module - Barrel Export
 *
 * Clean exports for all persona-related components, types, and utilities.
 *
 * @module components/admin/persona
 */

// Components
export { PersonaForm } from './PersonaForm';
export { PersonaCreateModal, type PersonaCreateModalProps } from './PersonaCreateModal';

// Schema & Validation
export {
  personaCreateSchema,
  personaUpdateSchema,
  personaExampleSchema,
  validatePersonaCreate,
  validatePersonaUpdate,
  DEFAULT_PERSONA_VALUES,
  PERSONA_FIELD_CONSTRAINTS,
} from './schema';
export type {
  PersonaCreateFormValues,
  PersonaUpdateFormValues,
  PersonaExample,
} from './schema';

// Types
export {
  VOICE_OPTIONS,
  MODEL_OPTIONS,
  mapFormToCreateRequest,
  mapFormToUpdateRequest,
  mapPersonaToFormValues,
} from './types';
export type {
  Persona,
  PersonaCreateRequest,
  PersonaUpdateRequest,
  PersonaTestResponse,
  PersonaUsageStats,
  PersonaFormProps,
} from './types';
