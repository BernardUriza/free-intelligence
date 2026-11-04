import { describe, expect, it } from 'vitest';
import { mapFormToCreateRequest } from './mappers';
import { generateIdFromName } from './PersonaForm';
import { DEFAULT_PERSONA_VALUES, validatePersonaCreate, validatePersonaUpdate } from './schema';

const valid = {
  ...DEFAULT_PERSONA_VALUES,
  id: 'nutrition_assistant',
  name: 'Asistente de Nutrición',
  description: 'Orienta sobre alimentación vegana.',
  system_prompt: 'Eres un asistente especializado en nutrición vegana.',
};

describe('persona schema', () => {
  it('accepts a complete persona and fills examples with []', () => {
    const { examples: _omit, ...withoutExamples } = valid;
    const result = validatePersonaCreate(withoutExamples);
    expect(result.success).toBe(true);
    expect(result.data?.examples).toEqual([]);
  });

  it('rejects an id that does not start with a lowercase letter, keyed by field', () => {
    const result = validatePersonaCreate({ ...valid, id: '1_persona' });
    expect(result.success).toBe(false);
    expect(Object.keys(result.errors ?? {})).toEqual(['id']);
  });

  it('resists injection-shaped ids and out-of-range numbers', () => {
    const result = validatePersonaCreate({ ...valid, id: 'a/../b', temperature: 1.5, max_tokens: 2.5 });
    expect(result.success).toBe(false);
    expect(Object.keys(result.errors ?? {}).sort()).toEqual(['id', 'max_tokens', 'temperature']);
  });

  it('flags an empty example input on the update path', () => {
    const result = validatePersonaUpdate({ examples: [{ input: '', output: 'x' }] });
    expect(result.errors?.['examples.0.input']).toBeTruthy();
  });

  it('derives a valid id from an accented name', () => {
    const id = generateIdFromName('  Médico General 2 ');
    expect(id).toBe('medico_general_2');
    expect(validatePersonaCreate({ ...valid, id }).success).toBe(true);
  });

  it('drops hidden fields from the create request', () => {
    const request = mapFormToCreateRequest(valid, ['voice', 'temperature']);
    expect(request).not.toHaveProperty('voice');
    expect(request).not.toHaveProperty('temperature');
    expect(request.max_tokens).toBe(2048);
  });
});
