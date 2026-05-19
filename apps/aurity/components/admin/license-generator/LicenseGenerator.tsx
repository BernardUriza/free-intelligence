'use client';

/**
 * LicenseGenerator - Superadmin License Generation Form
 *
 * A comprehensive form for generating Aurity Desktop license keys.
 * Only accessible to users with FI-superadmin role.
 *
 * Features:
 * - Max clinics capacity (clinics created AFTER activation)
 * - Optional license holder name
 * - Feature toggles (checkboxes)
 * - Expiration date picker (preset + custom)
 * - Copy-to-clipboard for generated key
 */

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@aurity-standalone/hooks/useAuth';
import { Button } from '@/components/ui/button';
import {
  licensesApi,
  setLicenseToken,
  LicenseGenerationRequest,
  LicenseGenerationResponse,
  DEFAULT_FEATURES,
  FeatureInfo,
} from '@/lib/api/licenses';
import {
  Key,
  Copy,
  Check,
  RefreshCw,
  Calendar,
  Sparkles,
  Download,
  Users,
} from 'lucide-react';
import { createLogger } from '@/lib/internal/logger';

const log = createLogger('LicenseGenerator');

interface LicenseGeneratorProps {
  className?: string;
}

export function LicenseGenerator({ className = '' }: LicenseGeneratorProps) {
  const { getAccessTokenSilently } = useAuth();

  // License capacity state
  const [maxClinics, setMaxClinics] = useState(1);
  const [licenseHolder, setLicenseHolder] = useState('');

  // Features state
  const [selectedFeatures, setSelectedFeatures] = useState<string[]>([
    'soap',
    'timeline',
    'prescriptions',
  ]);
  const [features, setFeatures] = useState<FeatureInfo[]>(DEFAULT_FEATURES);

  // Expiration state
  const [expirationPreset, setExpirationPreset] = useState<'1year' | '2years' | 'custom'>('1year');
  const [customDays, setCustomDays] = useState(365);

  // UI state
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<LicenseGenerationResponse | null>(null);
  const [copied, setCopied] = useState(false);

  // Load available features on mount (optional - uses defaults if fails)
  useEffect(() => {
    const loadFeatures = async () => {
      try {
        const token = await getAccessTokenSilently();
        if (token) {
          setLicenseToken(token);
          const response = await licensesApi.getFeatures();
          setFeatures(response.features);
        }
      } catch (err) {
        // Silently fail - use default features
      }
    };
    loadFeatures();
  }, [getAccessTokenSilently]);

  // Calculate expiration days
  const getExpirationDays = (): number => {
    switch (expirationPreset) {
      case '1year':
        return 365;
      case '2years':
        return 730;
      case 'custom':
        return customDays;
      default:
        return 365;
    }
  };

  // Toggle feature selection
  const toggleFeature = (featureId: string) => {
    setSelectedFeatures((prev) =>
      prev.includes(featureId)
        ? prev.filter((f) => f !== featureId)
        : [...prev, featureId]
    );
  };

  // Copy license key to clipboard
  const copyToClipboard = useCallback(async () => {
    if (!result?.license_key) return;

    try {
      await navigator.clipboard.writeText(result.license_key);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      log.error('Failed to copy license key', { error: String(err) });
    }
  }, [result]);

  // Download license as .key file
  const downloadLicenseFile = useCallback(() => {
    if (!result?.license_key) return;

    // Create filename: holder-name-YYYY-MM-DD.key or aurity-license-YYYY-MM-DD.key
    const date = new Date().toISOString().split('T')[0];
    const holderSlug = result.license_holder
      ? result.license_holder
          .toLowerCase()
          .replace(/[^a-z0-9]+/g, '-')
          .replace(/^-|-$/g, '')
      : 'aurity-license';
    const filename = `${holderSlug}-${date}.key`;

    // Create blob and download
    const blob = new Blob([result.license_key], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [result]);

  // Generate license
  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const token = await getAccessTokenSilently();
      if (!token) {
        throw new Error('No authentication token available');
      }

      setLicenseToken(token);

      const request: LicenseGenerationRequest = {
        max_clinics: maxClinics,
        license_holder: licenseHolder.trim() || undefined,
        features: selectedFeatures,
        expires_days: getExpirationDays(),
      };

      const response = await licensesApi.generate(request);
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate license');
    } finally {
      setIsLoading(false);
    }
  };

  // Reset form for new license
  const handleReset = () => {
    setResult(null);
    setError(null);
  };

  // Format date for display
  const formatDate = (isoDate: string): string => {
    return new Date(isoDate).toLocaleDateString('es-MX', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  // Determine if form is valid
  const isFormValid = maxClinics >= 1;

  return (
    <div className={`lic-gen-container ${className}`}>
      {/* Result Display */}
      {result && (
        <div className="admin-license-result">
          <div className="lic-gen-result-header">
            <Check className="lic-gen-result-icon" />
            <h3 className="lic-gen-result-title">
              Licencia generada exitosamente
            </h3>
          </div>

          {/* License Key */}
          <div className="lic-gen-key-wrapper">
            <label className="lic-gen-key-label">Clave de Licencia</label>
            <div className="lic-gen-key-row">
              <code className="admin-license-key-display">
                {result.license_key}
              </code>
              <div className="lic-gen-key-actions">
                <Button
                  onClick={downloadLicenseFile}
                  variant="primary"
                  size="sm"
                  icon={Download}
                >
                  Descargar .key
                </Button>
                <Button
                  onClick={copyToClipboard}
                  variant={copied ? 'success' : 'secondary'}
                  size="sm"
                  icon={copied ? Check : Copy}
                >
                  {copied ? 'Copiado' : 'Copiar'}
                </Button>
              </div>
            </div>
          </div>

          {/* License Details */}
          <div className="lic-gen-details-grid">
            <div>
              <span className="lic-text-label">ID de Licencia:</span>
              <span className="lic-text-value-mono">{result.license_id}</span>
            </div>
            <div>
              <span className="lic-text-label">Titular:</span>
              <span className="lic-text-value">
                {result.license_holder || '(no especificado)'}
              </span>
            </div>
            <div>
              <span className="lic-text-label">Max. Clinicas:</span>
              <span className="lic-text-value">{result.max_clinics}</span>
            </div>
            <div>
              <span className="lic-text-label">Expira:</span>
              <span className="lic-text-value">{formatDate(result.expires_at)}</span>
            </div>
            <div className="lic-gen-details-full">
              <span className="lic-text-label">Features:</span>
              <span className="lic-text-value">{result.features.join(', ')}</span>
            </div>
          </div>

          {/* Generate Another Button */}
          <div className="lic-gen-details-divider">
            <Button onClick={handleReset} variant="outline" icon={RefreshCw}>
              Generar Otra Licencia
            </Button>
          </div>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="admin-license-error">
          <p className="lic-gen-error-text">{error}</p>
        </div>
      )}

      {/* Generation Form */}
      {!result && (
        <form onSubmit={handleGenerate} className="lic-gen-form">
          {/* License Capacity */}
          <div className="admin-license-section">
            <div className="lic-gen-section-header">
              <Users className="lic-gen-section-icon-blue" />
              <h3 className="lic-gen-section-title">Capacidad de Licencia</h3>
            </div>

            <div className="lic-gen-field-grid">
              <div>
                <label className="lic-gen-field-label">
                  Maximo de Clinicas <span className="lic-gen-field-required">*</span>
                </label>
                <input
                  type="number"
                  value={maxClinics}
                  onChange={(e) => setMaxClinics(Math.max(1, parseInt(e.target.value) || 1))}
                  min={1}
                  max={100}
                  required
                  className="admin-license-input"
                />
                <p className="lic-gen-field-hint">
                  El admin creara las clinicas despues de activar la licencia
                </p>
              </div>
              <div>
                <label className="lic-gen-field-label">
                  Titular de Licencia
                </label>
                <input
                  type="text"
                  value={licenseHolder}
                  onChange={(e) => setLicenseHolder(e.target.value)}
                  placeholder="Dr. Garcia / Hospital Central"
                  className="admin-license-input"
                />
                <p className="lic-gen-field-hint">
                  Opcional, solo para identificacion
                </p>
              </div>
            </div>
          </div>

          {/* Features */}
          <div className="admin-license-section">
            <div className="lic-gen-section-header">
              <Sparkles className="lic-gen-section-icon-amber" />
              <h3 className="lic-gen-section-title">Funcionalidades</h3>
            </div>

            <div className="lic-gen-features-grid">
              {features.map((feature) => (
                <label
                  key={feature.id}
                  className={selectedFeatures.includes(feature.id) ? 'admin-license-toggle-active' : 'admin-license-toggle'}
                >
                  <input
                    type="checkbox"
                    checked={selectedFeatures.includes(feature.id)}
                    onChange={() => toggleFeature(feature.id)}
                    className="lic-gen-feature-checkbox"
                  />
                  <div>
                    <div className="lic-gen-feature-name">{feature.name}</div>
                    <div className="lic-gen-feature-desc">{feature.description}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Expiration */}
          <div className="admin-license-section">
            <div className="lic-gen-section-header">
              <Calendar className="lic-gen-section-icon-cyan" />
              <h3 className="lic-gen-section-title">Vigencia</h3>
            </div>

            <div className="lic-gen-expiration-row">
              <label
                className={expirationPreset === '1year' ? 'admin-license-radio-active' : 'admin-license-radio'}
              >
                <input
                  type="radio"
                  name="expiration"
                  checked={expirationPreset === '1year'}
                  onChange={() => setExpirationPreset('1year')}
                  className="lic-gen-radio-size"
                />
                <span className="lic-gen-radio-label">1 Ano</span>
              </label>

              <label
                className={expirationPreset === '2years' ? 'admin-license-radio-active' : 'admin-license-radio'}
              >
                <input
                  type="radio"
                  name="expiration"
                  checked={expirationPreset === '2years'}
                  onChange={() => setExpirationPreset('2years')}
                  className="lic-gen-radio-size"
                />
                <span className="lic-gen-radio-label">2 Anos</span>
              </label>

              <label
                className={expirationPreset === 'custom' ? 'admin-license-radio-active' : 'admin-license-radio'}
              >
                <input
                  type="radio"
                  name="expiration"
                  checked={expirationPreset === 'custom'}
                  onChange={() => setExpirationPreset('custom')}
                  className="lic-gen-radio-size"
                />
                <span className="lic-gen-radio-label">Personalizado</span>
              </label>

              {expirationPreset === 'custom' && (
                <div className="lic-gen-custom-days-row">
                  <input
                    type="number"
                    value={customDays}
                    onChange={(e) => setCustomDays(Math.max(1, parseInt(e.target.value) || 1))}
                    min={1}
                    max={3650}
                    className="lic-gen-custom-days-input"
                  />
                  <span className="lic-gen-custom-days-label">dias</span>
                </div>
              )}
            </div>
          </div>

          {/* Submit Button */}
          <Button
            type="submit"
            variant="primary"
            size="lg"
            fullWidth
            loading={isLoading}
            icon={Key}
            disabled={!isFormValid}
          >
            {isLoading ? 'Generando...' : 'Generar Licencia'}
          </Button>
        </form>
      )}

    </div>
  );
}
