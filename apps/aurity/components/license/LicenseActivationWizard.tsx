'use client';

/**
 * LicenseActivationWizard - License key entry and activation UI
 *
 * Shown when:
 * - First run (no license activated)
 * - License expired
 * - Invalid license detected
 *
 * Features:
 * - License key input with AURITY-XXXX-XXXX format
 * - Real-time validation
 * - Success/error feedback
 * - Option to request trial license
 */

import { useState, useCallback, useEffect } from 'react';
import { useLicense, LicenseValidationResult } from '@/hooks/useLicense';

interface LicenseActivationWizardProps {
  onActivated?: () => void;
  onSkip?: () => void;
  showSkip?: boolean;
}

export function LicenseActivationWizard({
  onActivated,
  onSkip,
  showSkip = false,
}: LicenseActivationWizardProps) {
  const { activateLicense, validateKey, isLoading: licenseLoading } = useLicense();

  const [licenseKey, setLicenseKey] = useState('');
  const [isValidating, setIsValidating] = useState(false);
  const [isActivating, setIsActivating] = useState(false);
  const [validationResult, setValidationResult] = useState<LicenseValidationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Format license key as user types
  const handleKeyChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    let value = e.target.value.toUpperCase();

    // Remove all non-alphanumeric characters except dashes
    value = value.replace(/[^A-Z0-9-]/g, '');

    // Auto-format with dashes (AURITY-XXXX-XXXX-...)
    // Only add dashes if not already present at the right positions
    const parts = value.replace(/-/g, '');
    const chunks: string[] = [];

    // First chunk is AURITY (6 chars), rest are 4 chars each
    if (parts.length > 0) {
      chunks.push(parts.slice(0, 6)); // AURITY
      let remaining = parts.slice(6);
      while (remaining.length > 0) {
        chunks.push(remaining.slice(0, 4));
        remaining = remaining.slice(4);
      }
    }

    value = chunks.join('-');
    setLicenseKey(value);
    setError(null);
    setValidationResult(null);
  }, []);

  // Validate key on blur or when complete
  const handleValidate = useCallback(async () => {
    if (!licenseKey || licenseKey.length < 10) return;

    setIsValidating(true);
    setError(null);

    try {
      const result = await validateKey(licenseKey);
      setValidationResult(result);

      if (!result.is_valid) {
        setError(result.message);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Validation failed');
    } finally {
      setIsValidating(false);
    }
  }, [licenseKey, validateKey]);

  // Auto-validate when key looks complete
  useEffect(() => {
    // AURITY-XXXX-XXXX-... minimum ~100 chars
    if (licenseKey.length > 100 && !isValidating && !validationResult) {
      const timer = setTimeout(handleValidate, 500);
      return () => clearTimeout(timer);
    }
  }, [licenseKey, handleValidate, isValidating, validationResult]);

  // Activate license
  const handleActivate = useCallback(async () => {
    if (!licenseKey) return;

    setIsActivating(true);
    setError(null);

    try {
      await activateLicense(licenseKey);
      setSuccess(true);

      // Notify parent after brief delay
      setTimeout(() => {
        onActivated?.();
      }, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Activation failed');
    } finally {
      setIsActivating(false);
    }
  }, [licenseKey, activateLicense, onActivated]);

  // Handle paste
  const handlePaste = useCallback((e: React.ClipboardEvent) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData('text');
    setLicenseKey(pasted.toUpperCase().trim());
    setError(null);
    setValidationResult(null);
  }, []);

  const isLoading = licenseLoading || isValidating || isActivating;
  const canActivate = validationResult?.is_valid && !isLoading;

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 to-slate-800 p-4">
        <div className="max-w-md w-full text-center">
          <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-green-500/20 flex items-center justify-center">
            <svg className="w-10 h-10 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-white mb-2">Licencia Activada</h2>
          <p className="text-slate-400 mb-4">
            {validationResult?.payload?.clinic_name || 'Tu licencia'} ha sido activada correctamente.
          </p>
          <p className="text-sm text-slate-500">Iniciando Aurity...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 to-slate-800 p-4">
      <div className="max-w-xl w-full">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
            <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
            </svg>
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">Activar Aurity Desktop</h1>
          <p className="text-slate-400">
            Ingresa tu clave de licencia para activar la aplicación
          </p>
        </div>

        {/* License Key Input */}
        <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl border border-slate-700 p-6 mb-6">
          <label className="block text-sm font-medium text-slate-300 mb-3">
            Clave de Licencia
          </label>

          <div className="relative">
            <input
              type="text"
              value={licenseKey}
              onChange={handleKeyChange}
              onBlur={handleValidate}
              onPaste={handlePaste}
              placeholder="AURITY-XXXX-XXXX-XXXX-..."
              className={`
                w-full px-4 py-3 bg-slate-900/50 border rounded-xl
                text-white font-mono text-sm
                placeholder:text-slate-600
                focus:outline-none focus:ring-2
                ${error
                  ? 'border-red-500/50 focus:ring-red-500/30'
                  : validationResult?.is_valid
                    ? 'border-green-500/50 focus:ring-green-500/30'
                    : 'border-slate-600 focus:ring-blue-500/30'
                }
              `}
              disabled={isLoading}
              autoFocus
            />

            {/* Status indicator */}
            <div className="absolute right-3 top-1/2 -translate-y-1/2">
              {isValidating && (
                <div className="w-5 h-5 border-2 border-blue-400/30 border-t-blue-400 rounded-full animate-spin" />
              )}
              {!isValidating && validationResult?.is_valid && (
                <svg className="w-5 h-5 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              )}
              {!isValidating && error && (
                <svg className="w-5 h-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              )}
            </div>
          </div>

          {/* Error message */}
          {error && (
            <p className="mt-2 text-sm text-red-400">{error}</p>
          )}

          {/* License info preview */}
          {validationResult?.is_valid && validationResult.payload && (
            <div className="mt-4 p-3 bg-green-500/10 border border-green-500/20 rounded-lg">
              <div className="flex items-center gap-2 text-green-400 text-sm mb-2">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Licencia Válida
              </div>
              <div className="text-slate-300 text-sm">
                <p><span className="text-slate-500">Clínica:</span> {validationResult.payload.clinic_name}</p>
                <p><span className="text-slate-500">Funciones:</span> {validationResult.payload.features.join(', ')}</p>
                {validationResult.days_remaining !== null && (
                  <p>
                    <span className="text-slate-500">Vence en:</span>{' '}
                    <span className={validationResult.days_remaining < 30 ? 'text-amber-400' : ''}>
                      {validationResult.days_remaining} días
                    </span>
                  </p>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="space-y-3">
          <button
            onClick={handleActivate}
            disabled={!canActivate}
            className={`
              w-full py-3 px-4 rounded-xl font-medium
              transition-all duration-200
              ${canActivate
                ? 'bg-gradient-to-r from-blue-500 to-purple-600 text-white hover:from-blue-600 hover:to-purple-700'
                : 'bg-slate-700 text-slate-500 cursor-not-allowed'
              }
            `}
          >
            {isActivating ? (
              <span className="flex items-center justify-center gap-2">
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Activando...
              </span>
            ) : (
              'Activar Licencia'
            )}
          </button>

          {showSkip && (
            <button
              onClick={onSkip}
              className="w-full py-3 px-4 rounded-xl font-medium text-slate-400 hover:text-white hover:bg-slate-700/50 transition-colors"
            >
              Continuar sin licencia (modo offline)
            </button>
          )}
        </div>

        {/* Help text */}
        <div className="mt-8 text-center">
          <p className="text-slate-500 text-sm">
            ¿No tienes licencia?{' '}
            <a
              href="https://aurity.io/pricing"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-400 hover:text-blue-300"
            >
              Solicitar licencia
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}

export default LicenseActivationWizard;
