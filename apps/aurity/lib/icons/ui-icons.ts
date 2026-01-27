/**
 * UI/General Icons Mapping
 *
 * Lucide icons for general UI contexts.
 * Used in surveys, onboarding, and general components.
 */

import {
  UserRound,
  Stethoscope,
  Syringe,
  ClipboardList,
  Building2,
  Landmark,
  RefreshCw,
  Circle,
  Sprout,
  TreeDeciduous,
  TreePine,
  Target,
  Mic,
  Library,
  CheckCircle,
  Inbox,
  Settings,
  Home,
  Sparkles,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

/**
 * User role icons - used in SurveyStep
 */
export const USER_ROLE_ICONS: Record<string, LucideIcon> = {
  medico_general: UserRound,
  especialista: Stethoscope,
  enfermera: Syringe,
  administrador: ClipboardList,
} as const;

/**
 * Clinic type icons - used in SurveyStep
 */
export const CLINIC_TYPE_ICONS: Record<string, LucideIcon> = {
  privada: Building2,
  publica: Landmark,
  mixta: RefreshCw,
} as const;

/**
 * Consultas per day icons (volume indicators)
 */
export const VOLUME_ICONS: Record<string, LucideIcon> = {
  low: Circle,
  medium: Circle,
  high: Circle,
  very_high: Circle,
  '1-5': Circle,
  '6-15': Circle,
  '16-30': Circle,
  '31+': Circle,
} as const;

/**
 * AI experience level icons
 */
export const EXPERIENCE_ICONS: Record<string, LucideIcon> = {
  ninguna: Sprout,
  basica: TreeDeciduous,
  avanzada: TreePine,
  none: Sprout,
  basic: TreeDeciduous,
  advanced: TreePine,
} as const;

/**
 * Voice/audio icons
 */
export const VOICE_ICONS: Record<string, LucideIcon> = {
  precision: Target,
  target: Target,
  mic: Mic,
  microphone: Mic,
} as const;

/**
 * Filter/catalog icons
 */
export const FILTER_ICONS: Record<string, LucideIcon> = {
  all: Library,
  todos: Library,
  installed: CheckCircle,
  instalados: CheckCircle,
  empty: Inbox,
  vacio: Inbox,
} as const;

/**
 * Persona/chat icons
 */
export const PERSONA_ICONS: Record<string, LucideIcon> = {
  onboarding_guide: Home,
  general_assistant: Sparkles,
  clinical_advisor: Stethoscope,
  soap_editor: ClipboardList,
  waiting_room_host: UserRound,
  fi_receptionist: Building2,
  system: Settings,
  default: Sparkles,
} as const;

/**
 * Get user role icon
 */
export function getUserRoleIcon(role: string): LucideIcon {
  return USER_ROLE_ICONS[role.toLowerCase()] || UserRound;
}

/**
 * Get clinic type icon
 */
export function getClinicTypeIcon(type: string): LucideIcon {
  return CLINIC_TYPE_ICONS[type.toLowerCase()] || Building2;
}

/**
 * Get experience level icon
 */
export function getExperienceIcon(level: string): LucideIcon {
  return EXPERIENCE_ICONS[level.toLowerCase()] || Sprout;
}

/**
 * Get persona icon
 */
export function getPersonaIcon(persona: string): LucideIcon {
  return PERSONA_ICONS[persona.toLowerCase()] || PERSONA_ICONS.default;
}

/**
 * Get filter icon
 */
export function getFilterIcon(filter: string): LucideIcon {
  return FILTER_ICONS[filter.toLowerCase()] || Library;
}
