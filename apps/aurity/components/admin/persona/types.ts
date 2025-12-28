/**
 * Persona Types
 *
 * Type definitions separating UI form values from API DTOs.
 * Interface Segregation: Types are split by responsibility.
 *
 * @module components/admin/persona/types
 */

import type { PersonaCreateFormValues, PersonaUpdateFormValues, PersonaExample } from './schema';

// Re-export schema types for convenience
export type { PersonaCreateFormValues, PersonaUpdateFormValues, PersonaExample };

/**
 * Usage statistics from backend
 */
export interface PersonaUsageStats {
  total_invocations: number;
  avg_latency_ms: number;
  avg_cost_usd: number;
}

/**
 * Full Persona entity from API
 */
export interface Persona {
  id: string;
  name: string;
  description: string;
  system_prompt: string;
  model: string;
  voice: string | null;
  temperature: number;
  max_tokens: number;
  examples: PersonaExample[];
  usage_stats: PersonaUsageStats;
  version: number;
  last_updated: string;
  updated_by: string;
}

/**
 * API request for creating a persona
 */
export interface PersonaCreateRequest {
  id: string;
  name: string;
  description: string;
  system_prompt: string;
  model?: string;
  voice?: string | null;
  temperature?: number;
  max_tokens?: number;
  examples?: PersonaExample[];
}

/**
 * API request for updating a persona
 */
export interface PersonaUpdateRequest {
  name?: string;
  description?: string;
  system_prompt?: string;
  model?: string;
  voice?: string | null;
  temperature?: number;
  max_tokens?: number;
  examples?: PersonaExample[];
}

/**
 * API response for persona test
 */
export interface PersonaTestResponse {
  output: string | Record<string, unknown>;
  latency_ms: number;
  tokens_used: number;
  cost_usd: number;
}

/**
 * Mappers: Convert between UI form values and API DTOs
 */

/**
 * Map form values to create request DTO
 */
export function mapFormToCreateRequest(form: PersonaCreateFormValues): PersonaCreateRequest {
  return {
    id: form.id,
    name: form.name,
    description: form.description,
    system_prompt: form.system_prompt,
    model: form.model,
    voice: form.voice,
    temperature: form.temperature,
    max_tokens: form.max_tokens,
    examples: form.examples,
  };
}

/**
 * Map form values to update request DTO
 */
export function mapFormToUpdateRequest(form: PersonaUpdateFormValues): PersonaUpdateRequest {
  const request: PersonaUpdateRequest = {};

  if (form.name !== undefined) request.name = form.name;
  if (form.description !== undefined) request.description = form.description;
  if (form.system_prompt !== undefined) request.system_prompt = form.system_prompt;
  if (form.model !== undefined) request.model = form.model;
  if (form.voice !== undefined) request.voice = form.voice;
  if (form.temperature !== undefined) request.temperature = form.temperature;
  if (form.max_tokens !== undefined) request.max_tokens = form.max_tokens;
  if (form.examples !== undefined) request.examples = form.examples;

  return request;
}

/**
 * Map Persona entity to form values for editing
 */
export function mapPersonaToFormValues(persona: Persona): PersonaUpdateFormValues {
  return {
    name: persona.name,
    description: persona.description,
    system_prompt: persona.system_prompt,
    model: persona.model,
    voice: persona.voice,
    temperature: persona.temperature,
    max_tokens: persona.max_tokens,
    examples: persona.examples,
  };
}

/**
 * Base form values type (union of create and update)
 */
export type PersonaFormValues = PersonaCreateFormValues | PersonaUpdateFormValues;

/**
 * PersonaForm props interface
 * Dependency Inversion: Form receives handlers, doesn't know about persistence
 */
export interface PersonaFormProps {
  /** Current form values */
  value: PersonaFormValues;
  /** Handler for value changes */
  onChange: (values: PersonaFormValues) => void;
  /** Handler for form submission */
  onSubmit: () => void;
  /** Whether form is disabled (e.g., during save) */
  disabled?: boolean;
  /** Validation errors keyed by field name */
  errors?: Record<string, string>;
  /** Mode determines which fields are shown */
  mode: 'create' | 'edit';
  /** Whether to show advanced fields (examples, etc.) */
  showAdvanced?: boolean;
}

/**
 * Available TTS voices
 */
export const VOICE_OPTIONS = [
  { value: 'nova', label: 'Nova (Cálida, femenina)' },
  { value: 'shimmer', label: 'Shimmer (Clara, femenina)' },
  { value: 'alloy', label: 'Alloy (Neutral)' },
  { value: 'echo', label: 'Echo (Profunda, masculina)' },
  { value: 'fable', label: 'Fable (Narrativa)' },
  { value: 'onyx', label: 'Onyx (Grave, masculina)' },
] as const;

/**
 * Available LLM models
 */
export const MODEL_OPTIONS = [
  { value: 'qwen3:1.7b', label: 'Qwen3 1.7B (Local, rápido)' },
  { value: 'qwen3:8b', label: 'Qwen3 8B (Local, balanced)' },
  { value: 'gpt-4o-mini', label: 'GPT-4o Mini (Cloud, económico)' },
  { value: 'gpt-4o', label: 'GPT-4o (Cloud, preciso)' },
  { value: 'claude-3-5-sonnet-20241022', label: 'Claude 3.5 Sonnet (Cloud)' },
] as const;
