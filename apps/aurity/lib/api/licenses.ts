/**
 * License Generation API Client
 *
 * API client for superadmin license generation endpoints.
 * Requires FI-superadmin role.
 *
 * Updated: 2026-02 - Migrated to centralized api client
 */

import { api } from './client';
import { ROUTES } from './routes';

// ============================================================================
// Types
// ============================================================================

export interface LicenseGenerationRequest {
  max_clinics?: number;       // Default: 1
  license_holder?: string;    // Optional display name
  features?: string[];
  expires_days?: number;
}

export interface LicenseGenerationResponse {
  license_id: string;
  license_key: string;
  max_clinics: number;
  license_holder: string;
  expires_at: string;
  features: string[];
  issued_at: string;
}

export interface FeatureInfo {
  id: string;
  name: string;
  description: string;
}

export interface FeaturesResponse {
  features: FeatureInfo[];
}

// ============================================================================
// API Functions
// ============================================================================

export const licensesApi = {
  /**
   * Generate a new license key.
   * Requires FI-superadmin role.
   */
  generate: async (
    request: LicenseGenerationRequest
  ): Promise<LicenseGenerationResponse> => {
    return api.post<LicenseGenerationResponse>(`${ROUTES.adminLicenses}/generate`, request);
  },

  /**
   * Get list of available features.
   * Requires FI-superadmin role.
   */
  getFeatures: async (): Promise<FeaturesResponse> => {
    return api.get<FeaturesResponse>(`${ROUTES.adminLicenses}/features`);
  },
};

// ============================================================================
// Legacy Token Management (Deprecated)
// ============================================================================

/** @deprecated Token is now handled automatically by api client */
export function setLicenseToken(_token: string | null): void {
  console.warn('[licenses.ts] setLicenseToken is deprecated - token is handled automatically');
}

// ============================================================================
// Default Features (fallback if API unavailable)
// ============================================================================

export const DEFAULT_FEATURES: FeatureInfo[] = [
  { id: 'soap', name: 'SOAP Notes', description: 'Medical SOAP documentation' },
  { id: 'timeline', name: 'Timeline', description: 'Patient visit timeline' },
  { id: 'prescriptions', name: 'Prescriptions', description: 'Prescription generation' },
  { id: 'analytics', name: 'Analytics', description: 'Usage analytics dashboard' },
  { id: 'multi_clinic', name: 'Multi-Clinic', description: 'Support for multiple clinics' },
  { id: 'voice_assistant', name: 'Voice Assistant', description: 'Real-time voice transcription' },
];
