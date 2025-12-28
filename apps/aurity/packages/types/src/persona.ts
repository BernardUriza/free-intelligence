/**
 * Persona Types - AI Persona Configuration
 *
 * TypeScript types matching backend API schema for persona management.
 */

export interface PersonaExample {
  input: string;
  output: string | Record<string, any>;
}

export interface PersonaUsageStats {
  total_invocations: number;
  avg_latency_ms: number;
  avg_cost_usd: number;
}

export interface Persona {
  id: string;
  name: string;
  description: string;
  system_prompt: string;
  model: string;
  voice?: string | null;  // TTS voice (e.g., 'nova', 'shimmer')
  temperature: number;
  max_tokens: number;
  examples: PersonaExample[];
  usage_stats: PersonaUsageStats;
  version: number;
  last_updated: string;
  updated_by: string;
}

export interface PersonaUpdateRequest {
  name?: string;
  description?: string;
  system_prompt?: string;
  model?: string;
  voice?: string | null;  // TTS voice
  temperature?: number;
  max_tokens?: number;
  examples?: PersonaExample[];
}

/**
 * Request to create a new persona (FI-superadmin only)
 */
export interface PersonaCreateRequest {
  /** Unique ID (lowercase, underscores, e.g., 'my_persona') */
  id: string;
  /** Display name */
  name: string;
  /** Persona description (min 10 chars) */
  description: string;
  /** System prompt (min 20 chars) */
  system_prompt: string;
  /** LLM model ID (default: 'qwen3:1.7b') */
  model?: string;
  /** TTS voice (default: 'nova') */
  voice?: string | null;
  /** Temperature 0.0-1.0 (default: 0.7) */
  temperature?: number;
  /** Max tokens 1-8192 (default: 2048) */
  max_tokens?: number;
  /** Few-shot examples */
  examples?: PersonaExample[];
}

export interface PersonaTestRequest {
  input: string;
  compare_with_version?: number;
}

export interface PersonaTestResponse {
  output: string | Record<string, any>;
  latency_ms: number;
  tokens_used: number;
  cost_usd: number;
}

// Model options
// @deprecated Use fetchLLMModels() from @/lib/api/llm-models instead
// This is kept as a fallback for when the API is unavailable
export const LLM_MODELS = [
  { value: 'gpt-4o', label: 'GPT-4o (Más preciso, $$$)', cost: 'high' },
  { value: 'gpt-4o-mini', label: 'GPT-4o-mini (Balance, $$)', cost: 'medium' },
  { value: 'claude-3-5-sonnet', label: 'Claude 3.5 Sonnet ($$$)', cost: 'high' },
  { value: 'claude-3-haiku', label: 'Claude 3 Haiku ($)', cost: 'low' },
] as const;

// Persona color schemes
export const PERSONA_COLORS = {
  soap_editor: 'emerald',
  clinical_advisor: 'blue',
  general_assistant: 'purple',
  onboarding_guide: 'rose',
} as const;

export type PersonaId = keyof typeof PERSONA_COLORS;
export type PersonaColor = typeof PERSONA_COLORS[PersonaId];
