import type { PersonaOption } from 'fi-glass/persona-admin';
import type { LLMModel } from '@aurity-standalone/types/llm';
import { VOICE_GROUPS } from '@aurity-standalone/types/voices';

export const PERSONA_MODEL_FALLBACK: PersonaOption[] = [
  { value: 'qwen3:1.7b', label: 'Qwen3 1.7B (Local, rápido)' },
  { value: 'qwen3:8b', label: 'Qwen3 8B (Local, balanced)' },
  { value: 'gpt-4o-mini', label: 'GPT-4o Mini (Cloud, económico)' },
  { value: 'gpt-4o', label: 'GPT-4o (Cloud, preciso)' },
  { value: 'claude-3-5-sonnet-20241022', label: 'Claude 3.5 Sonnet (Cloud)' },
];

export const PERSONA_VOICE_OPTIONS: PersonaOption[] = VOICE_GROUPS.flatMap((group) =>
  group.voices.map((voice) => ({
    value: voice.value,
    label: voice.description ? `${voice.label} · ${voice.description}` : voice.label,
    group: group.label,
  })),
);

export function modelOptionsFrom(models: LLMModel[]): PersonaOption[] {
  return models.length > 0 ? models.map((m) => ({ value: m.id, label: m.label })) : PERSONA_MODEL_FALLBACK;
}

export const PROTECTED_PERSONAS = new Set(['general_assistant', 'soap_editor']);

export const PERSONA_ACCENTS: Record<string, string> = {
  soap_editor: '#34d399',
  clinical_advisor: '#60a5fa',
  general_assistant: '#c084fc',
  onboarding_guide: '#fb7185',
};

export const personaDeleteMessage = (name: string) =>
  `¿Estás seguro de eliminar la persona "${name}"?\n\n` +
  'Esta acción eliminará:\n' +
  '• El template de la persona\n' +
  '• Todas las configuraciones de usuario asociadas\n\n' +
  'Esta acción no se puede deshacer.';
