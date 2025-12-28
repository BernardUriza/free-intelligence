/**
 * Persona Form Schema
 *
 * Zod validation schema for Persona forms (create/edit).
 * Single Responsibility: Only handles validation logic.
 *
 * @module components/admin/persona/schema
 */

import { z } from 'zod';

/**
 * Persona ID validation pattern
 * - Must start with lowercase letter
 * - Only lowercase letters, numbers, underscores allowed
 */
const PERSONA_ID_PATTERN = /^[a-z][a-z0-9_]*$/;

/**
 * Example schema for few-shot learning
 */
export const personaExampleSchema = z.object({
  input: z.string().min(1, { message: 'Input is required' }),
  output: z.union([z.string(), z.record(z.string(), z.any())]),
});

/**
 * Base persona form schema (shared between create and edit)
 */
const basePersonaSchema = z.object({
  name: z
    .string()
    .min(1, 'El nombre es requerido')
    .max(100, 'El nombre no puede exceder 100 caracteres'),

  description: z
    .string()
    .min(10, 'La descripción debe tener al menos 10 caracteres')
    .max(500, 'La descripción no puede exceder 500 caracteres'),

  system_prompt: z
    .string()
    .min(20, 'El prompt del sistema debe tener al menos 20 caracteres')
    .max(10000, 'El prompt del sistema no puede exceder 10,000 caracteres'),

  model: z
    .string()
    .min(1, 'El modelo es requerido'),

  voice: z
    .string()
    .nullable()
    .optional(),

  temperature: z
    .number()
    .min(0, 'La temperatura debe ser al menos 0')
    .max(1, 'La temperatura no puede exceder 1'),

  max_tokens: z
    .number()
    .int('Max tokens debe ser un número entero')
    .min(1, 'Max tokens debe ser al menos 1')
    .max(8192, 'Max tokens no puede exceder 8192'),

  examples: z
    .array(personaExampleSchema)
    .optional()
    .default([]),
});

/**
 * Schema for creating a new persona (requires ID)
 */
export const personaCreateSchema = basePersonaSchema.extend({
  id: z
    .string()
    .min(1, 'El ID es requerido')
    .max(64, 'El ID no puede exceder 64 caracteres')
    .regex(
      PERSONA_ID_PATTERN,
      'El ID debe empezar con letra minúscula y solo contener letras, números y guiones bajos'
    ),
});

/**
 * Schema for updating an existing persona (ID is optional/readonly)
 */
export const personaUpdateSchema = basePersonaSchema.partial();

/**
 * Type inference from schemas
 */
export type PersonaCreateFormValues = z.infer<typeof personaCreateSchema>;
export type PersonaUpdateFormValues = z.infer<typeof personaUpdateSchema>;
export type PersonaExample = z.infer<typeof personaExampleSchema>;

/**
 * Default values for new persona form
 */
export const DEFAULT_PERSONA_VALUES: PersonaCreateFormValues = {
  id: '',
  name: '',
  description: '',
  system_prompt: '',
  model: 'qwen3:1.7b',
  voice: 'nova',
  temperature: 0.7,
  max_tokens: 2048,
  examples: [],
};

/**
 * Field constraints for UI components
 */
export const PERSONA_FIELD_CONSTRAINTS = {
  name: { min: 1, max: 100 },
  description: { min: 10, max: 500 },
  system_prompt: { min: 20, max: 10000 },
  id: { min: 1, max: 64, pattern: PERSONA_ID_PATTERN },
  temperature: { min: 0, max: 1, step: 0.1 },
  max_tokens: { min: 1, max: 8192, step: 256 },
} as const;

/**
 * Validate persona create form
 */
export function validatePersonaCreate(data: unknown): {
  success: boolean;
  data?: PersonaCreateFormValues;
  errors?: Record<string, string>;
} {
  const result = personaCreateSchema.safeParse(data);
  if (result.success) {
    return { success: true, data: result.data };
  }

  const errors: Record<string, string> = {};
  for (const issue of result.error.issues) {
    const path = issue.path.join('.') || 'root';
    errors[path] = issue.message;
  }

  return { success: false, errors };
}

/**
 * Validate persona update form
 */
export function validatePersonaUpdate(data: unknown): {
  success: boolean;
  data?: PersonaUpdateFormValues;
  errors?: Record<string, string>;
} {
  const result = personaUpdateSchema.safeParse(data);
  if (result.success) {
    return { success: true, data: result.data };
  }

  const errors: Record<string, string> = {};
  for (const issue of result.error.issues) {
    const path = issue.path.join('.') || 'root';
    errors[path] = issue.message;
  }

  return { success: false, errors };
}
