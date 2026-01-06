/**
 * Persona Styles - Visual theme configuration per persona
 * Extracted from FIMessageBubble for reuse across message variants
 */

import {
  Stethoscope,
  FileEdit,
  Microscope,
  Compass,
  Network,
  Shield,
  TrendingUp,
  Activity,
} from 'lucide-react';
import type { PersonaStyle } from '../types';

/**
 * Persona-based styling configuration
 * Maps backend personas to VISUAL themes ONLY
 *
 * NOTE: Labels are no longer hardcoded here.
 * Persona names come from backend dynamically.
 */
export const PERSONA_STYLES: Record<string, PersonaStyle> = {
  // Onboarding Guide - Sovereignty theme (emerald)
  onboarding_guide: {
    border: 'border-emerald-600/60',
    bg: 'bg-emerald-950/20',
    glow: 'shadow-emerald-500/10',
    Icon: Compass,
    labelColor: 'text-emerald-300',
  },

  // General Assistant - Neutral theme (slate)
  general_assistant: {
    border: 'border-slate-600/60',
    bg: 'bg-slate-900/20',
    glow: 'shadow-slate-500/10',
    Icon: Stethoscope,
    labelColor: 'fi-text',
  },

  // Clinical Advisor - Evidence-based theme (blue)
  clinical_advisor: {
    border: 'border-blue-600/60',
    bg: 'bg-blue-950/20',
    glow: 'shadow-blue-500/10',
    Icon: Microscope,
    labelColor: 'text-blue-300',
  },

  // SOAP Editor - Precision theme (cyan)
  soap_editor: {
    border: 'border-cyan-600/60',
    bg: 'bg-cyan-950/20',
    glow: 'shadow-cyan-500/10',
    Icon: FileEdit,
    labelColor: 'text-cyan-300',
  },

  // Waiting Room Host - Welcoming theme (purple)
  waiting_room_host: {
    border: 'border-purple-600/60',
    bg: 'bg-purple-950/20',
    glow: 'shadow-purple-500/10',
    Icon: Compass,
    labelColor: 'text-purple-300',
  },

  // ==== PHILOSOPHICAL PERSONAS (Free Intelligence Core Principles) ====

  // Pattern Weaver - Memory archaeology theme (violet)
  pattern_weaver: {
    border: 'border-violet-600/60',
    bg: 'bg-violet-950/20',
    glow: 'shadow-violet-500/10',
    Icon: Network,
    labelColor: 'text-violet-300',
  },

  // Sovereignty Guide - Data sovereignty theme (amber)
  sovereignty_guide: {
    border: 'border-amber-600/60',
    bg: 'bg-amber-950/20',
    glow: 'shadow-amber-500/10',
    Icon: Shield,
    labelColor: 'text-amber-300',
  },

  // Growth Mirror - Symbiotic development theme (rose)
  growth_mirror: {
    border: 'border-rose-600/60',
    bg: 'bg-rose-950/20',
    glow: 'shadow-rose-500/10',
    Icon: TrendingUp,
    labelColor: 'text-rose-300',
  },

  // Honest Limiter - Anti-oracle theme (orange)
  honest_limiter: {
    border: 'border-orange-600/60',
    bg: 'bg-orange-950/20',
    glow: 'shadow-orange-500/10',
    Icon: Activity,
    labelColor: 'text-orange-300',
  },
} as const;

/**
 * Fallback style for unknown personas
 */
export const FALLBACK_STYLE: PersonaStyle = {
  border: 'border-slate-600/60',
  bg: 'bg-slate-900/20',
  glow: 'shadow-slate-500/10',
  Icon: Stethoscope,
  labelColor: 'fi-text',
};

/**
 * Get persona style with fallback
 */
export function getPersonaStyle(persona: string | undefined): PersonaStyle {
  if (!persona) return FALLBACK_STYLE;
  return PERSONA_STYLES[persona] || FALLBACK_STYLE;
}

/**
 * Philosophical personas that use short "FI" prefix
 */
const PHILOSOPHICAL_PERSONAS = [
  'pattern_weaver',
  'sovereignty_guide',
  'growth_mirror',
  'honest_limiter',
];

/**
 * Generate label from persona name (backend format → display format)
 * Examples:
 *   "General Assistant" → "FREE-INTELLIGENCE"
 *   "SOAP Editor" → "FREE-INTELLIGENCE · SOAP EDITOR"
 *   "Honest Limiter" → "FI · HONEST LIMITER"
 */
export function generatePersonaLabel(
  personaName: string | undefined,
  personaId?: string
): string {
  if (!personaName) return 'FREE-INTELLIGENCE';

  // Philosophical personas use short "FI" prefix
  const isPhilosophical = personaId
    ? PHILOSOPHICAL_PERSONAS.includes(personaId)
    : false;

  if (personaName === 'General Assistant') {
    return 'FREE-INTELLIGENCE';
  }

  const prefix = isPhilosophical ? 'FI' : 'FREE-INTELLIGENCE';
  const suffix = personaName.toUpperCase();

  return `${prefix} · ${suffix}`;
}
