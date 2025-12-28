/**
 * LLM Model Types - AI Model Configuration
 *
 * TypeScript types matching backend API schema for LLM model management.
 */

export type LLMProvider = 'openai' | 'anthropic' | 'azure' | 'ollama';
export type CostTier = 'low' | 'medium' | 'high';

export interface LLMModel {
  id: string;
  label: string;
  provider: LLMProvider;
  cost_tier: CostTier;
  max_tokens: number;
  context_window: number;
  is_active: boolean;
  description?: string | null;
  size_bytes?: number | null;
  ram_required_gb?: number | null;
  created_at: string;
  updated_at: string;
}

export interface LLMModelCreate {
  id: string;
  label: string;
  provider: LLMProvider;
  cost_tier?: CostTier;
  max_tokens?: number;
  context_window?: number;
  is_active?: boolean;
  description?: string | null;
  size_bytes?: number | null;
  ram_required_gb?: number | null;
}

export interface LLMModelUpdate {
  label?: string;
  provider?: LLMProvider;
  cost_tier?: CostTier;
  max_tokens?: number;
  context_window?: number;
  is_active?: boolean;
  description?: string | null;
  size_bytes?: number | null;
  ram_required_gb?: number | null;
}

// Provider display info (icon field is legacy - use ProviderLogo component for SVG)
export const PROVIDER_INFO: Record<LLMProvider, { label: string; icon: string; color: string }> = {
  openai: { label: 'OpenAI', icon: 'openai', color: 'emerald' },
  anthropic: { label: 'Anthropic', icon: 'anthropic', color: 'orange' },
  azure: { label: 'Azure', icon: 'azure', color: 'blue' },
  ollama: { label: 'Ollama (Local)', icon: 'ollama', color: 'slate' },
};

// Cost tier display info
export const COST_TIER_INFO: Record<CostTier, { label: string; icon: string; color: string }> = {
  low: { label: 'Económico', icon: '$', color: 'green' },
  medium: { label: 'Balance', icon: '$$', color: 'yellow' },
  high: { label: 'Premium', icon: '$$$', color: 'red' },
};
