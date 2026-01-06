/**
 * Select Component Configuration Types
 *
 * Shared types and utilities for rich select dropdowns with icons, badges, descriptions.
 * Used across PersonaSelectorPanel, ConfigTab, and other components.
 */

import type { LucideIcon } from 'lucide-react';
import {
  Brain,
  Stethoscope,
  FileEdit,
  Microscope,
  Compass,
  Network,
  Shield,
  TrendingUp,
  Activity,
} from 'lucide-react';

// Badge color variants
export type BadgeVariant = 'purple' | 'violet' | 'blue' | 'emerald' | 'green' | 'slate';

// Rich select item configuration
export interface SelectItemConfig {
  value: string;
  label: string;
  icon?: LucideIcon;
  description?: string;
  badge?: {
    text: string;
    variant: BadgeVariant;
  };
  metadata?: Record<string, string | number>;
  disabled?: boolean;
}

/**
 * @deprecated Use getPersonaIcon from '@/components/ui/message/styles/persona-styles' instead.
 * This mapping will be removed in a future version.
 */
export const PERSONA_ICONS: Record<string, LucideIcon> = {
  general_assistant: Stethoscope,
  soap_editor: FileEdit,
  clinical_advisor: Microscope,
  onboarding_guide: Compass,
  pattern_weaver: Network,
  sovereignty_guide: Shield,
  growth_mirror: TrendingUp,
  honest_limiter: Activity,
  default: Brain,
};

// Model badge colors (by model ID)
export const MODEL_BADGE_COLORS: Record<string, BadgeVariant> = {
  'qwen3:1.7b': 'purple',
  'qwen3:4b': 'violet',
  'llama3:8b': 'blue',
  'gpt-4o-mini': 'emerald',
  'gpt-4o': 'green',
};

// Provider badge colors
export const PROVIDER_BADGE_COLORS: Record<string, BadgeVariant> = {
  ollama: 'purple',
  openai: 'emerald',
  anthropic: 'blue',
  azure: 'slate',
};

// Badge color classes
export const BADGE_STYLES: Record<BadgeVariant, { bg: string; text: string; border: string }> = {
  purple: {
    bg: 'bg-purple-500/20',
    text: 'text-purple-300',
    border: 'border-purple-500/30',
  },
  violet: {
    bg: 'bg-violet-500/20',
    text: 'text-violet-300',
    border: 'border-violet-500/30',
  },
  blue: {
    bg: 'bg-blue-500/20',
    text: 'text-blue-300',
    border: 'border-blue-500/30',
  },
  emerald: {
    bg: 'bg-emerald-500/20',
    text: 'text-emerald-300',
    border: 'border-emerald-500/30',
  },
  green: {
    bg: 'bg-green-500/20',
    text: 'text-green-300',
    border: 'border-green-500/30',
  },
  slate: {
    bg: 'bg-slate-500/20',
    text: 'text-slate-300',
    border: 'border-slate-500/30',
  },
};

/**
 * Get badge variant for a model ID
 */
export function getModelBadgeVariant(modelId?: string): BadgeVariant {
  if (!modelId) return 'slate';
  return MODEL_BADGE_COLORS[modelId] || 'slate';
}

/**
 * Get badge variant for a provider
 */
export function getProviderBadgeVariant(provider?: string): BadgeVariant {
  if (!provider) return 'slate';
  return PROVIDER_BADGE_COLORS[provider.toLowerCase()] || 'slate';
}

/**
 * Get icon for a persona ID
 * @deprecated Use getPersonaIcon from '@/components/ui/message/styles/persona-styles' instead.
 */
export function getPersonaIcon(personaId?: string): LucideIcon {
  if (!personaId) return PERSONA_ICONS.default;
  return PERSONA_ICONS[personaId] || PERSONA_ICONS.default;
}

/**
 * Get provider name from model ID
 */
export function getProviderFromModel(modelId?: string): string {
  if (!modelId) return 'unknown';
  if (modelId.startsWith('gpt-')) return 'openai';
  if (modelId.startsWith('claude-')) return 'anthropic';
  if (modelId.startsWith('qwen') || modelId.startsWith('llama')) return 'ollama';
  return 'unknown';
}
