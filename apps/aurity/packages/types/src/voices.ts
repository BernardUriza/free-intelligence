/**
 * Voice Types and Constants
 *
 * Defines all available TTS voices across providers:
 * - OpenAI TTS (11 voices)
 * - OpenAI Steerable (3 voices with accent control)
 */

export interface VoiceOption {
  value: string;
  label: string;
  provider: 'openai' | 'openai-steerable' | 'azure-openai';
  gender?: 'female' | 'male' | 'neutral';
  description?: string;
  recommended?: boolean;
}

export interface VoiceGroup {
  label: string;
  description: string;
  voices: VoiceOption[];
}

export const VOICE_GROUPS: VoiceGroup[] = [
  {
    label: '🎯 OpenAI Steerable (Acento Mexicano)',
    description: 'Voces con control de acento - Mejor para español',
    voices: [
      {
        value: 'alloy',
        label: 'Alloy (Neutral)',
        provider: 'openai-steerable' as const,
        gender: 'neutral' as const,
        description: 'Versátil con acento mexicano',
        recommended: true,
      },
      {
        value: 'echo',
        label: 'Echo (Male)',
        provider: 'openai-steerable' as const,
        gender: 'male' as const,
        description: 'Voz masculina con acento mexicano',
      },
      {
        value: 'shimmer',
        label: 'Shimmer (Female)',
        provider: 'openai-steerable' as const,
        gender: 'female' as const,
        description: 'Voz femenina clara con acento mexicano',
      },
    ],
  },
  {
    label: '🎙️ OpenAI Standard (Inglés/General)',
    description: 'Voces naturales sin control de acento',
    voices: [
      {
        value: 'nova',
        label: 'Nova (Female, Warm)',
        provider: 'openai' as const,
        gender: 'female' as const,
        description: 'Cálida y expresiva',
        recommended: true,
      },
      {
        value: 'alloy',
        label: 'Alloy (Neutral)',
        provider: 'openai' as const,
        gender: 'neutral' as const,
        description: 'Versátil',
      },
      {
        value: 'shimmer',
        label: 'Shimmer (Female)',
        provider: 'openai' as const,
        gender: 'female' as const,
        description: 'Clara',
      },
      {
        value: 'echo',
        label: 'Echo (Male)',
        provider: 'openai' as const,
        gender: 'male' as const,
        description: 'Masculina',
      },
      {
        value: 'fable',
        label: 'Fable (Male, British)',
        provider: 'openai' as const,
        gender: 'male' as const,
        description: 'Acento británico',
      },
      {
        value: 'onyx',
        label: 'Onyx (Male, Deep)',
        provider: 'openai' as const,
        gender: 'male' as const,
        description: 'Grave y profunda',
      },
      {
        value: 'ash',
        label: 'Ash (New 2025)',
        provider: 'openai' as const,
        description: 'Nueva voz 2025',
      },
      {
        value: 'ballad',
        label: 'Ballad (New 2025)',
        provider: 'openai' as const,
        description: 'Nueva voz 2025',
      },
      {
        value: 'coral',
        label: 'Coral (New 2025)',
        provider: 'openai' as const,
        description: 'Nueva voz 2025',
      },
      {
        value: 'sage',
        label: 'Sage (New 2025)',
        provider: 'openai' as const,
        description: 'Nueva voz 2025',
      },
      {
        value: 'verse',
        label: 'Verse (New 2025)',
        provider: 'openai' as const,
        description: 'Nueva voz 2025',
      },
    ],
  },
];

// Flat list of all voices
export const ALL_VOICES: VoiceOption[] = VOICE_GROUPS.flatMap(group => group.voices);

// Get voice info by value
export function getVoiceInfo(voiceValue: string): VoiceOption | undefined {
  return ALL_VOICES.find(v => v.value === voiceValue);
}

// Get recommended voices
export function getRecommendedVoices(): VoiceOption[] {
  return ALL_VOICES.filter(v => v.recommended);
}
