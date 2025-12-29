/**
 * License Generation API Client
 *
 * API client for superadmin license generation endpoints.
 * Requires FI-superadmin role.
 */

import { getBackendUrl } from './client';

// ============================================================================
// Types
// ============================================================================

export interface LicenseGenerationRequest {
  clinic_id: string;
  clinic_name?: string;
  auth0_domain: string;
  auth0_client_id: string;
  auth0_audience?: string;
  features?: string[];
  expires_days?: number;
}

export interface LicenseGenerationResponse {
  license_id: string;
  license_key: string;
  clinic_id: string;
  clinic_name: string;
  auth0_domain: string;
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
// Token Management
// ============================================================================

let _licenseToken: string | null = null;

export function setLicenseToken(token: string | null): void {
  _licenseToken = token;
}

function getAuthHeaders(): HeadersInit {
  const headers: HeadersInit = { 'Content-Type': 'application/json' };
  if (_licenseToken) {
    headers['Authorization'] = `Bearer ${_licenseToken}`;
  }
  return headers;
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
    const baseUrl = getBackendUrl();
    const response = await fetch(`${baseUrl}/api/admin/licenses/generate`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  },

  /**
   * Get list of available features.
   * Requires FI-superadmin role.
   */
  getFeatures: async (): Promise<FeaturesResponse> => {
    const baseUrl = getBackendUrl();
    const response = await fetch(`${baseUrl}/api/admin/licenses/features`, {
      method: 'GET',
      headers: getAuthHeaders(),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  },
};

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
