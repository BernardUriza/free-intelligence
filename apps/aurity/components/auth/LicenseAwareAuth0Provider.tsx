'use client';

/**
 * LicenseAwareAuth0Provider - Combined License + Auth0 Provider for Desktop
 *
 * NEW FLOW (2026-01-21):
 * This provider:
 * 1. Renders DesktopAuth0Provider immediately (NO license check on mount)
 * 2. License check happens when user attempts to login (in loginWithRedirect)
 * 3. Shows LicenseActivationWizard if needed WHEN user tries to login
 * 4. Gets Auth0 config from license after activation
 *
 * This allows users to see DesktopSetupWizard (dependencies) BEFORE needing a license.
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
  // NEW FLOW: Simply render DesktopAuth0Provider without checking license upfront
  // License check happens inside DesktopAuth0Provider.loginWithRedirect()

  // Still need to wait for hydration to avoid SSR mismatch
  const [isHydrated, setIsHydrated] = useState(false);

  useEffect(() => {
    setIsHydrated(true);
  }, []);

  // Show loading during hydration only
  if (!isHydrated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 to-slate-800">
        <div className="text-center">
          <div className="w-12 h-12 mx-auto mb-4 border-3 border-blue-400/30 border-t-blue-400 rounded-full animate-spin" />
          <p className="text-slate-400">Cargando...</p>
        </div>
      </div>
    );
  }

  // Render DesktopAuth0Provider immediately
  // It will handle license check when user attempts login
  return (
    <DesktopAuth0Provider>
      {children}
    </DesktopAuth0Provider>
  );
}

export default LicenseAwareAuth0Provider;
