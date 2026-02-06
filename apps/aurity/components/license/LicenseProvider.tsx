'use client';

/**
 * LicenseProvider - Wraps auth with license-based configuration
 *
 * Flow:
 * 1. Check if license is activated
 * 2. If not activated → show LicenseActivationWizard
 * 3. If activated → render children (app)
 */

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  ReactNode,
} from 'react';
import { LicenseActivationWizard } from './LicenseActivationWizard';
import { LicenseRenewalBanner } from './LicenseRenewalBanner';
import { useLicense, LicensePayload, RenewalStatus } from '@/hooks/useLicense';

interface LicenseContextType {
  isLicenseValid: boolean;
  licensePayload: LicensePayload | null;
  daysRemaining: number | null;
  features: string[];
  hasFeature: (feature: string) => boolean;
  clearLicense: () => Promise<void>;
  renewalStatus: RenewalStatus | null;
  needsRenewal: boolean;
}

const LicenseContext = createContext<LicenseContextType | undefined>(undefined);

interface LicenseProviderProps {
  children: ReactNode;
}

export function LicenseProvider({ children }: LicenseProviderProps) {
  const {
    isLoading,
    isValid,
    licenseStatus,
    renewalStatus,
    needsRenewal,
    clearLicense,
    daysRemaining,
    features,
  } = useLicense();

  const [showWizard, setShowWizard] = useState(false);

  // Check license on mount
  useEffect(() => {
    if (isLoading) return;

    if (!isValid) {
      setShowWizard(true);
    } else {
      setShowWizard(false);
    }
  }, [isLoading, isValid]);

  // Handle license activation
  const handleActivated = useCallback(() => {
    // Reload the page to reinitialize with new license
    window.location.reload();
  }, []);

  // Check if a feature is enabled
  const hasFeature = useCallback(
    (feature: string) => features.includes(feature),
    [features]
  );

  // Show loading state
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 to-slate-800">
        <div className="text-center">
          <div className="w-12 h-12 mx-auto mb-4 border-3 border-blue-400/30 border-t-blue-400 rounded-full animate-spin" />
          <p className="text-slate-400">Verificando licencia...</p>
        </div>
      </div>
    );
  }

  // Show activation wizard if license is not valid
  if (showWizard) {
    return <LicenseActivationWizard onActivated={handleActivated} />;
  }

  // License is valid - provide context and render children
  const contextValue: LicenseContextType = {
    isLicenseValid: isValid,
    licensePayload: licenseStatus?.payload ?? null,
    daysRemaining,
    features,
    hasFeature,
    clearLicense,
    renewalStatus,
    needsRenewal,
  };

  return (
    <LicenseContext.Provider value={contextValue}>
      {/* Show renewal warning banner at top of app */}
      <LicenseRenewalBanner className="fixed top-0 left-0 right-0 z-50" />
      {children}
    </LicenseContext.Provider>
  );
}

export function useLicenseContext(): LicenseContextType {
  const context = useContext(LicenseContext);
  if (!context) {
    throw new Error('useLicenseContext must be used within LicenseProvider');
  }
  return context;
}
