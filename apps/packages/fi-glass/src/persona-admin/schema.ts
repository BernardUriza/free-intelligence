import { z } from 'zod';

export const PERSONA_ID_PATTERN = /^[a-z][a-z0-9_]*$/;

export const personaExampleSchema = z.object({
  input: z.string().min(1, { message: 'Input is required' }),
  output: z.union([z.string(), z.record(z.string(), z.unknown())]),
});

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
  model: z.string().min(1, 'El modelo es requerido'),
  voice: z.string().nullable().optional(),
  temperature: z
    .number()
    .min(0, 'La temperatura debe ser al menos 0')
    .max(1, 'La temperatura no puede exceder 1'),
  max_tokens: z
    .number()
    .int('Max tokens debe ser un número entero')
    .min(1, 'Max tokens debe ser al menos 1')
    .max(8192, 'Max tokens no puede exceder 8192'),
  examples: z.array(personaExampleSchema).optional().default([]),
});

export const personaCreateSchema = basePersonaSchema.extend({
  id: z
    .string()
    .min(1, 'El ID es requerido')
    .max(64, 'El ID no puede exceder 64 caracteres')
    .regex(
      PERSONA_ID_PATTERN,
      'El ID debe empezar con letra minúscula y solo contener letras, números y guiones bajos',
    ),
});

export const personaUpdateSchema = basePersonaSchema.partial();

export type PersonaCreateFormValues = z.infer<typeof personaCreateSchema>;
export type PersonaUpdateFormValues = z.infer<typeof personaUpdateSchema>;
export type PersonaFormValues = PersonaCreateFormValues | PersonaUpdateFormValues;

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

export const PERSONA_FIELD_CONSTRAINTS = {
  name: { min: 1, max: 100 },
  description: { min: 10, max: 500 },
  system_prompt: { min: 20, max: 10000 },
  id: { min: 1, max: 64, pattern: PERSONA_ID_PATTERN },
  temperature: { min: 0, max: 1, step: 0.05 },
  max_tokens: { min: 1, max: 8192, step: 256 },
} as const;

export interface PersonaValidation<T> {
  success: boolean;
  data?: T;
  errors?: Record<string, string>;
}

function toResult<T>(result: z.ZodSafeParseResult<T>): PersonaValidation<T> {
  if (result.success) return { success: true, data: result.data };
  const errors: Record<string, string> = {};
  for (const issue of result.error.issues) {
    const path = issue.path.join('.') || 'root';
    if (!(path in errors)) errors[path] = issue.message;
  }
  return { success: false, errors };
}

export function validatePersonaCreate(data: unknown): PersonaValidation<PersonaCreateFormValues> {
  return toResult(personaCreateSchema.safeParse(data));
}

export function validatePersonaUpdate(data: unknown): PersonaValidation<PersonaUpdateFormValues> {
  return toResult(personaUpdateSchema.safeParse(data));
}
