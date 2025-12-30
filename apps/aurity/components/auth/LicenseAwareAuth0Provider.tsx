'use client';

/**
 * LicenseAwareAuth0Provider - Combined License + Auth0 Provider for Desktop
 *
 * This provider:
 * 1. First checks for valid license
 * 2. Shows LicenseActivationWizard if needed
 * 3. Gets Auth0 config from license
 * 4. Initializes DesktopAuth0Provider with license config
 *
 * Usage:
 * ```tsx
 * <LicenseAwareAuth0Provider>
 *   <App />
 * </LicenseAwareAuth0Provider>
 * ```
 */

import { useState, useEffect, ReactNode } from 'react';
import { LicenseActivationWizard } from '@/components/license/LicenseActivationWizard';
import { DesktopAuth0Provider } from './DesktopAuth0Provider';
import { useLicense, Auth0Config } from '@/hooks/useLicense';

interface LicenseAwareAuth0ProviderProps {
  children: ReactNode;
}

// Check if running in Tauri (safe to call at module level)
function isTauriRuntime(): boolean {
  return typeof window !== 'undefined' && '__TAURI__' in window;
}

export function LicenseAwareAuth0Provider({ children }: LicenseAwareAuth0ProviderProps) {
  // Wait for hydration before doing anything Tauri-related
  const [isHydrated, setIsHydrated] = useState(false);
  const [isTauri, setIsTauri] = useState(false);

  useEffect(() => {
    setIsTauri(isTauriRuntime());
    setIsHydrated(true);
  }, []);

  // Use license hook (it handles non-Tauri case internally)
  const { isLoading, isValid, getAuth0Config } = useLicense();

  const [auth0Config, setAuth0Config] = useState<Auth0Config | null>(null);
  const [configLoading, setConfigLoading] = useState(true);
  const [showWizard, setShowWizard] = useState(false);

  // Check license and load Auth0 config AFTER hydration
  useEffect(() => {
    // Don't do anything until hydrated and we know we're in Tauri
    if (!isHydrated) return;

    const load = async () => {
      // If not in Tauri, skip license check (shouldn't happen, but safety)
      if (!isTauri) {
        console.log('[LicenseAwareAuth0] Not in Tauri, skipping license check');
        setConfigLoading(false);
        return;
      }

      if (isLoading) return;

      if (!isValid) {
        console.log('[LicenseAwareAuth0] License not valid, showing wizard');
        setShowWizard(true);
        setConfigLoading(false);
        return;
      }

      try {
        const config = await getAuth0Config();
        console.log('[LicenseAwareAuth0] Loaded Auth0 config from license:', {
          domain: config.domain,
          audience: config.audience,
        });
        setAuth0Config(config);
        setShowWizard(false);
      } catch (err) {
        console.error('[LicenseAwareAuth0] Failed to get Auth0 config:', err);
        setShowWizard(true);
      } finally {
        setConfigLoading(false);
      }
    };

    load();
  }, [isHydrated, isTauri, isLoading, isValid, getAuth0Config]);

  // Handle license activation
  const handleActivated = () => {
    // Reload to reinitialize with new license
    window.location.reload();
  };

  // Show loading during hydration or license check
  if (!isHydrated || isLoading || configLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 to-slate-800">
        <div className="text-center">
          <div className="w-12 h-12 mx-auto mb-4 border-3 border-blue-400/30 border-t-blue-400 rounded-full animate-spin" />
          <p className="text-slate-400">Verificando licencia...</p>
        </div>
      </div>
    );
  }

  // Show wizard if license not valid
  if (showWizard) {
    return <LicenseActivationWizard onActivated={handleActivated} />;
  }

  // License valid - render DesktopAuth0Provider with license config
  return (
    <DesktopAuth0Provider auth0Config={auth0Config ?? undefined}>
      {children}
    </DesktopAuth0Provider>
  );
}

export default LicenseAwareAuth0Provider;
