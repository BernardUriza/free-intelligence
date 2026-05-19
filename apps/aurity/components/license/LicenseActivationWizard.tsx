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
 * - File import from .key files (Desktop only)
 * - Real-time validation
 * - Success/error feedback
 * - Option to request trial license
 */

import { useState, useCallback, useEffect } from 'react';
import { createLogger } from '@/lib/internal/logger';
import { useLicense, LicenseValidationResult, LicensePayload } from '@/hooks/useLicense';

const log = createLogger('LicenseWizard');

// Tauri imports (optional - only available in desktop)
const isTauri = typeof window !== 'undefined' && '__TAURI__' in window;

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
  const { activateLicense, validateKey, isLoading: licenseLoading, checkLicense } = useLicense();

  const [licenseKey, setLicenseKey] = useState('');
  const [isValidating, setIsValidating] = useState(false);
  const [isActivating, setIsActivating] = useState(false);
  const [isImportingFile, setIsImportingFile] = useState(false);
  const [validationResult, setValidationResult] = useState<LicenseValidationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [importedPayload, setImportedPayload] = useState<LicensePayload | null>(null);

  // Handle file import from .key file (Desktop only)
  const handleFileImport = useCallback(async () => {
    if (!isTauri) {
      setError('La importación de archivos solo está disponible en la versión de escritorio');
      return;
    }

    setIsImportingFile(true);
    setError(null);

    try {
      // Dynamic imports for Tauri APIs
      const { open } = await import('@tauri-apps/plugin-dialog');
      const { invoke } = await import('@tauri-apps/api/core');

      // Open file picker
      const selected = await open({
        multiple: false,
        filters: [
          { name: 'Licencia Aurity', extensions: ['key'] },
          { name: 'Todos los archivos', extensions: ['*'] },
        ],
        title: 'Seleccionar archivo de licencia',
      });

      if (!selected) {
        // User cancelled
        setIsImportingFile(false);
        return;
      }

      // Import the license from the file
      // open() with multiple:false returns string | null
      const filePath = selected as string;
      const payload = await invoke<LicensePayload>('import_license_from_file', {
        file_path: filePath
      });

      // Success!
      setImportedPayload(payload);
      setSuccess(true);

      // Verify license was activated
      const status = await checkLicense();
      if (status.is_valid) {
        setValidationResult(status);
      }

      // Notify parent after brief delay
      setTimeout(() => {
        onActivated?.();
      }, 1500);
    } catch (err) {
      log.error('File import error', { error: String(err) });
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsImportingFile(false);
    }
  }, [checkLicense, onActivated]);

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

  const isLoading = licenseLoading || isValidating || isActivating || isImportingFile;
  const canActivate = validationResult?.is_valid && !isLoading;

  if (success) {
    const licenseHolder = importedPayload?.license_holder || validationResult?.payload?.license_holder || 'Tu licencia';
    return (
      <div className="lic-wizard-page">
        <div className="lic-wizard-success-container">
          <div className="lic-wizard-success-icon-wrapper">
            <svg className="lic-wizard-success-check" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 className="lic-wizard-success-title">Licencia Activada</h2>
          <p className="lic-wizard-success-subtitle">
            {licenseHolder} ha sido activada correctamente.
          </p>
          <p className="lic-wizard-success-loading">Iniciando Aurity...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="lic-wizard-page">
      <div className="lic-wizard-container">
        {/* Header */}
        <div className="lic-wizard-header">
          <div className="lic-wizard-header-icon">
            <svg className="lic-wizard-header-icon-svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
            </svg>
          </div>
          <h1 className="lic-wizard-title">Activar Aurity Desktop</h1>
          <p className="lic-wizard-subtitle">
            Ingresa tu clave de licencia para activar la aplicacion
          </p>
        </div>

        {/* License Key Input */}
        <div className="lic-wizard-input-card">
          <label className="lic-wizard-input-label">
            Clave de Licencia
          </label>

          <div className="lic-wizard-input-wrapper">
            <input
              type="text"
              value={licenseKey}
              onChange={handleKeyChange}
              onBlur={handleValidate}
              onPaste={handlePaste}
              placeholder="AURITY-XXXX-XXXX-XXXX-..."
              className={`lic-wizard-input ${
                error
                  ? 'lic-wizard-input-error'
                  : validationResult?.is_valid
                    ? 'lic-wizard-input-valid'
                    : 'lic-wizard-input-default'
              }`}
              disabled={isLoading}
              autoFocus
            />

            {/* Status indicator */}
            <div className="lic-wizard-input-status">
              {isValidating && (
                <div className="lic-wizard-spinner" />
              )}
              {!isValidating && validationResult?.is_valid && (
                <svg className="lic-wizard-icon-valid" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              )}
              {!isValidating && error && (
                <svg className="lic-wizard-icon-error" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              )}
            </div>
          </div>

          {/* Error message */}
          {error && (
            <p className="lic-wizard-error-msg">{error}</p>
          )}

          {/* License info preview */}
          {validationResult?.is_valid && validationResult.payload && (
            <div className="lic-wizard-preview">
              <div className="lic-wizard-preview-header">
                <svg className="lic-wizard-preview-header-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Licencia Valida
              </div>
              <div className="lic-wizard-preview-body">
                <p><span className="lic-wizard-preview-label">Titular:</span> {validationResult.payload.license_holder}</p>
                <p><span className="lic-wizard-preview-label">Funciones:</span> {validationResult.payload.features.join(', ')}</p>
                {validationResult.days_remaining !== null && (
                  <p>
                    <span className="lic-wizard-preview-label">Vence en:</span>{' '}
                    <span className={validationResult.days_remaining < 30 ? 'lic-wizard-preview-expiry-warn' : ''}>
                      {validationResult.days_remaining} dias
                    </span>
                  </p>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="lic-wizard-actions">
          {/* File import button (Desktop only) */}
          {isTauri && (
            <button
              onClick={handleFileImport}
              disabled={isLoading}
              className={isLoading ? 'lic-wizard-btn-import-disabled' : 'lic-wizard-btn-import'}
            >
              {isImportingFile ? (
                <>
                  <div className="lic-wizard-btn-import-spinner" />
                  Importando...
                </>
              ) : (
                <>
                  <svg className="lic-wizard-btn-import-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                  Cargar archivo .key
                </>
              )}
            </button>
          )}

          {/* Separator for desktop */}
          {isTauri && (
            <div className="lic-wizard-separator">
              <div className="lic-wizard-separator-line" />
              <span>o ingresa manualmente</span>
              <div className="lic-wizard-separator-line" />
            </div>
          )}

          <button
            onClick={handleActivate}
            disabled={!canActivate}
            className={canActivate ? 'lic-wizard-btn-activate' : 'lic-wizard-btn-activate-disabled'}
          >
            {isActivating ? (
              <span className="lic-wizard-btn-activate-inner">
                <div className="lic-wizard-btn-activate-spinner" />
                Activando...
              </span>
            ) : (
              'Activar Licencia'
            )}
          </button>

          {showSkip && (
            <button
              onClick={onSkip}
              className="lic-wizard-btn-skip"
            >
              Continuar sin licencia (modo offline)
            </button>
          )}
        </div>

        {/* Help text */}
        <div className="lic-wizard-footer">
          <p className="lic-wizard-footer-text">
            No tienes licencia?{' '}
            <a
              href="https://aurity.io/pricing"
              target="_blank"
              rel="noopener noreferrer"
              className="lic-wizard-footer-link"
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
