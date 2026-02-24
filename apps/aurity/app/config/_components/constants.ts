/**
 * Config Page Constants
 *
 * Static data extracted from the config page render tree.
 * Single source of truth for feature flags, permissions, and system settings.
 */

import type { FeatureFlag, PermissionRow } from './types';

// ---------------------------------------------------------------------------
// Feature Flags
// ---------------------------------------------------------------------------

export const FEATURE_FLAGS: readonly FeatureFlag[] = [
  {
    label: 'Demo Mode',
    description: 'Modo demo con TTS simulado',
    active: true,
  },
  {
    label: 'Timeline View',
    description: 'Vista cronológica de eventos',
    active: true,
  },
  {
    label: 'Advanced Diarization',
    description: 'Separación de voces mejorada',
    active: false,
  },
] as const;

// ---------------------------------------------------------------------------
// Permission Matrix
// ---------------------------------------------------------------------------

export const PERMISSION_MATRIX: readonly PermissionRow[] = [
  { label: 'Gestionar Sistema', superadmin: true, clinician: false },
  { label: 'Ver Logs', superadmin: true, clinician: false },
  { label: 'Gestionar Usuarios', superadmin: true, clinician: false },
  { label: 'Crear Sesión', superadmin: true, clinician: true },
  { label: 'Ver Sesión', superadmin: true, clinician: true },
  { label: 'Exportar Datos', superadmin: true, clinician: true },
  { label: 'Eliminar Sesión', superadmin: true, clinician: false },
] as const;

// ---------------------------------------------------------------------------
// Onboarding localStorage keys to clear
// ---------------------------------------------------------------------------

export const ONBOARDING_STORAGE_KEYS = [
  'fi_onboarding_progress',
  'fi_onboarding_conversation',
  'aurity_onboarding_completed',
  'fi_onboarding_survey',
] as const;
