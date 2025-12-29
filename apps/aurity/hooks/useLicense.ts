'use client';

/**
 * useLicense - Hook for license management in Aurity Desktop
 *
 * Provides:
 * - License status checking
 * - License activation
 * - Auth0 config from license
 * - Feature checking
 */

import { useState, useEffect, useCallback } from 'react';

// License validation result from Rust backend
export interface LicenseValidationResult {
  status: 'valid' | 'expired' | 'invalid_signature' | 'invalid_format' | 'not_activated';
  is_valid: boolean;
  message: string;
  days_remaining: number | null;
  payload: LicensePayload | null;
}

// License payload structure
export interface LicensePayload {
  license_id: string;
  auth0_domain: string;
  auth0_client_id: string;
  auth0_audience: string;
  clinic_id: string;
  clinic_name: string;
  features: string[];
  issued_at: string;
  expires_at: string;
  version: string;
}

// Auth0 config from license
export interface Auth0Config {
  domain: string;
  client_id: string;
  audience: string;
}

// Renewal status from Rust backend
export interface RenewalStatus {
  needs_renewal: boolean;
  days_until_expiry: number | null;
  renewal_url: string | null;
  warning_message: string | null;
}

// Renewal response from server
export interface RenewalResponse {
  renewed: boolean;
  reason: string | null;
  new_expires_at: string | null;
  new_license_key: string | null;
  renewal_url: string | null;
  message: string;
}

export interface UseLicenseReturn {
  // State
  isLoading: boolean;
  isActivated: boolean;
  isValid: boolean;
  licenseStatus: LicenseValidationResult | null;
  renewalStatus: RenewalStatus | null;
  error: string | null;

  // Actions
  checkLicense: () => Promise<LicenseValidationResult>;
  activateLicense: (key: string) => Promise<LicensePayload>;
  validateKey: (key: string) => Promise<LicenseValidationResult>;
  getAuth0Config: () => Promise<Auth0Config>;
  hasFeature: (feature: string) => Promise<boolean>;
  clearLicense: () => Promise<void>;

  // Renewal actions
  checkRenewalStatus: () => Promise<RenewalStatus>;
  requestRenewal: () => Promise<RenewalResponse>;

  // Derived data
  daysRemaining: number | null;
  clinicName: string | null;
  features: string[];
  needsRenewal: boolean;
}

export function useLicense(): UseLicenseReturn {
  const [isLoading, setIsLoading] = useState(true);
  const [licenseStatus, setLicenseStatus] = useState<LicenseValidationResult | null>(null);
  const [renewalStatus, setRenewalStatus] = useState<RenewalStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Check if running in Tauri
  const isTauri = typeof window !== 'undefined' && '__TAURI__' in window;

  // Import Tauri invoke dynamically
  const getInvoke = useCallback(async () => {
    if (!isTauri) {
      throw new Error('Not running in Tauri environment');
    }
    const { invoke } = await import('@tauri-apps/api/core');
    return invoke;
  }, [isTauri]);

  // Check license status on mount
  useEffect(() => {
    const check = async () => {
      if (!isTauri) {
        setIsLoading(false);
        return;
      }

      try {
        const invoke = await getInvoke();

        // Check license status
        const status = await invoke<LicenseValidationResult>('get_current_license_status');
        setLicenseStatus(status);

        // Also check renewal status if license is valid
        if (status.is_valid) {
          const renewal = await invoke<RenewalStatus>('check_license_renewal_status');
          setRenewalStatus(renewal);
        }

        setError(null);
      } catch (err) {
        console.error('[useLicense] Check error:', err);
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setIsLoading(false);
      }
    };

    check();

    // Check renewal status every 24 hours while app is running
    const intervalId = setInterval(async () => {
      if (!isTauri) return;
      try {
        const invoke = await getInvoke();
        const renewal = await invoke<RenewalStatus>('check_license_renewal_status');
        setRenewalStatus(renewal);
      } catch (err) {
        console.error('[useLicense] Periodic renewal check error:', err);
      }
    }, 24 * 60 * 60 * 1000); // 24 hours

    return () => clearInterval(intervalId);
  }, [isTauri, getInvoke]);

  // Check license status
  const checkLicense = useCallback(async (): Promise<LicenseValidationResult> => {
    const invoke = await getInvoke();
    const status = await invoke<LicenseValidationResult>('get_current_license_status');
    setLicenseStatus(status);
    return status;
  }, [getInvoke]);

  // Validate a license key (without activating)
  const validateKey = useCallback(async (key: string): Promise<LicenseValidationResult> => {
    const invoke = await getInvoke();
    return invoke<LicenseValidationResult>('validate_license_key', { key });
  }, [getInvoke]);

  // Activate a license key
  const activateLicense = useCallback(async (key: string): Promise<LicensePayload> => {
    const invoke = await getInvoke();
    setError(null);

    try {
      const payload = await invoke<LicensePayload>('activate_license_key', { key });

      // Refresh status after activation
      const status = await invoke<LicenseValidationResult>('get_current_license_status');
      setLicenseStatus(status);

      return payload;
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setError(message);
      throw new Error(message);
    }
  }, [getInvoke]);

  // Get Auth0 config from license
  const getAuth0Config = useCallback(async (): Promise<Auth0Config> => {
    const invoke = await getInvoke();
    return invoke<Auth0Config>('get_license_auth0_config');
  }, [getInvoke]);

  // Check if a feature is enabled
  const hasFeature = useCallback(async (feature: string): Promise<boolean> => {
    const invoke = await getInvoke();
    return invoke<boolean>('check_feature_enabled', { feature });
  }, [getInvoke]);

  // Clear license
  const clearLicense = useCallback(async (): Promise<void> => {
    const invoke = await getInvoke();
    await invoke('clear_stored_license');
    setLicenseStatus({
      status: 'not_activated',
      is_valid: false,
      message: 'No license activated',
      days_remaining: null,
      payload: null,
    });
    setRenewalStatus(null);
  }, [getInvoke]);

  // Check renewal status
  const checkRenewalStatus = useCallback(async (): Promise<RenewalStatus> => {
    const invoke = await getInvoke();
    const status = await invoke<RenewalStatus>('check_license_renewal_status');
    setRenewalStatus(status);
    return status;
  }, [getInvoke]);

  // Request license renewal from server
  const requestRenewal = useCallback(async (): Promise<RenewalResponse> => {
    const invoke = await getInvoke();
    setError(null);

    try {
      const response = await invoke<RenewalResponse>('request_license_renewal');

      // If renewal succeeded, refresh license status
      if (response.renewed) {
        const status = await invoke<LicenseValidationResult>('get_current_license_status');
        setLicenseStatus(status);

        const renewal = await invoke<RenewalStatus>('check_license_renewal_status');
        setRenewalStatus(renewal);
      }

      return response;
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setError(message);
      throw new Error(message);
    }
  }, [getInvoke]);

  // Derived values
  const isActivated = licenseStatus?.status !== 'not_activated';
  const isValid = licenseStatus?.is_valid ?? false;
  const daysRemaining = licenseStatus?.days_remaining ?? null;
  const clinicName = licenseStatus?.payload?.clinic_name ?? null;
  const features = licenseStatus?.payload?.features ?? [];
  const needsRenewal = renewalStatus?.needs_renewal ?? false;

  return {
    isLoading,
    isActivated,
    isValid,
    licenseStatus,
    renewalStatus,
    error,
    checkLicense,
    activateLicense,
    validateKey,
    getAuth0Config,
    hasFeature,
    clearLicense,
    checkRenewalStatus,
    requestRenewal,
    daysRemaining,
    clinicName,
    features,
    needsRenewal,
  };
}
