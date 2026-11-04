import type { PersonaCreateFormValues, PersonaUpdateFormValues } from './schema';
import type {
  Persona,
  PersonaCreateRequest,
  PersonaHideableField,
  PersonaUpdateRequest,
} from './types';

function omitHidden<T extends object>(request: T, hiddenFields: readonly PersonaHideableField[]): T {
  if (hiddenFields.length === 0) return request;
  const copy = { ...request } as Record<string, unknown>;
  for (const field of hiddenFields) delete copy[field];
  return copy as T;
}

export function mapFormToCreateRequest(
  form: PersonaCreateFormValues,
  hiddenFields: readonly PersonaHideableField[] = [],
): PersonaCreateRequest {
  return omitHidden(
    {
      id: form.id,
      name: form.name,
      description: form.description,
      system_prompt: form.system_prompt,
      model: form.model,
      voice: form.voice,
      temperature: form.temperature,
      max_tokens: form.max_tokens,
      examples: form.examples,
    },
    hiddenFields,
  );
}

export function mapFormToUpdateRequest(
  form: PersonaUpdateFormValues,
  hiddenFields: readonly PersonaHideableField[] = [],
): PersonaUpdateRequest {
  const request: PersonaUpdateRequest = {};
  if (form.name !== undefined) request.name = form.name;
  if (form.description !== undefined) request.description = form.description;
  if (form.system_prompt !== undefined) request.system_prompt = form.system_prompt;
  if (form.model !== undefined) request.model = form.model;
  if (form.voice !== undefined) request.voice = form.voice;
  if (form.temperature !== undefined) request.temperature = form.temperature;
  if (form.max_tokens !== undefined) request.max_tokens = form.max_tokens;
  if (form.examples !== undefined) request.examples = form.examples;
  return omitHidden(request, hiddenFields);
}

export function mapPersonaToFormValues(persona: Persona): PersonaUpdateFormValues {
  return {
    name: persona.name,
    description: persona.description,
    system_prompt: persona.system_prompt,
    model: persona.model,
    voice: persona.voice ?? null,
    temperature: persona.temperature,
    max_tokens: persona.max_tokens,
    examples: persona.examples,
  };
}
