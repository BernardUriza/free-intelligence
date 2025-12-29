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

export function LicenseAwareAuth0Provider({ children }: LicenseAwareAuth0ProviderProps) {
  const { isLoading, isValid, getAuth0Config, licenseStatus } = useLicense();

  const [auth0Config, setAuth0Config] = useState<Auth0Config | null>(null);
  const [configLoading, setConfigLoading] = useState(true);
  const [showWizard, setShowWizard] = useState(false);

  // Check license and load Auth0 config
  useEffect(() => {
    const load = async () => {
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
  }, [isLoading, isValid, getAuth0Config]);

  // Handle license activation
  const handleActivated = () => {
    // Reload to reinitialize with new license
    window.location.reload();
  };

  // Show loading
  if (isLoading || configLoading) {
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
