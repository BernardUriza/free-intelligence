/**
 * ProviderRegistry - Single source of truth for TTS providers
 *
 * Formal registry of TTS providers with priority ordering and capability metadata.
 * Supports OpenAI Steerable (accent control) and OpenAI Standard (general purpose).
 *
 * Selection logic:
 * 1. Spanish text + steerable voice → OpenAI Steerable (Mexican accent)
 * 2. Otherwise → OpenAI Standard
 *
 * @module ProviderRegistry
 * @see /apps/aurity/docs/audio/PROVIDER_MATRIX.md
 */

export interface TTSProvider {
  id: 'openai' | 'openai-steerable';
  name: string;
  priority: number; // 1 = highest
  defaultVoice: string;
  capabilities: {
    accentControl: boolean;
    neuralVoices: boolean;
    streaming: boolean;
    maxChars: number;
  };
  locales: {
    primary: string;
    secondary: string[];
    fallback: string;
  };
}

/**
 * Formal provider registry ordered by priority
 *
 * Priority 1 (OpenAI Steerable): Spanish with accent control (Mexican, Castilian, Argentine)
 * Priority 2 (OpenAI Standard): General purpose, 11 voices
 */
export const PROVIDER_REGISTRY: TTSProvider[] = [
  {
    id: 'openai-steerable',
    name: 'OpenAI Steerable TTS',
    priority: 1,
    defaultVoice: 'alloy',
    capabilities: {
      accentControl: true, // Mexican Spanish, Castilian Spanish, etc.
      neuralVoices: true,
      streaming: false,
      maxChars: 4096,
    },
    locales: {
      primary: 'es-MX',
      secondary: ['en-US', 'es-ES'],
      fallback: 'en-US',
    },
  },
  {
    id: 'openai',
    name: 'OpenAI TTS Standard',
    priority: 2,
    defaultVoice: 'nova',
    capabilities: {
      accentControl: false,
      neuralVoices: true,
      streaming: false,
      maxChars: 4096,
    },
    locales: {
      primary: 'en-US',
      secondary: ['es-MX', 'es-ES'],
      fallback: 'en-US',
    },
  },
];

/**
 * Get provider by voice ID
 *
 * Auto-selects provider based on voice string:
 * - "alloy" → OpenAI Steerable
 * - "nova" → OpenAI Standard
 *
 * @param voice - Voice identifier (e.g., "alloy", "nova")
 * @returns Matching TTSProvider
 */
export function getProviderByVoice(voice: string): TTSProvider {
  // OpenAI Steerable voices
  if (['alloy', 'echo', 'shimmer'].includes(voice)) {
    return PROVIDER_REGISTRY[0]; // OpenAI Steerable
  }

  // Default to OpenAI Standard
  return PROVIDER_REGISTRY[1]; // OpenAI Standard
}

/**
 * Get default provider
 *
 * Returns OpenAI Steerable with alloy (default)
 *
 * @returns Default TTSProvider (OpenAI Steerable)
 */
export function getDefaultProvider(): TTSProvider {
  return PROVIDER_REGISTRY[0]; // OpenAI Steerable
}

/**
 * Get provider by ID
 *
 * @param id - Provider ID ('openai', 'openai-steerable')
 * @returns Matching TTSProvider or default
 */
export function getProviderById(id: string): TTSProvider {
  return PROVIDER_REGISTRY.find(p => p.id === id) || getDefaultProvider();
}
