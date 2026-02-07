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
        // This commonly happens with refresh token issues
        console.debug('[LicenseGenerator] Using default features (token unavailable)');
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
      console.error('[LicenseGenerator] Failed to copy:', err);
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
    <div className={`max-w-4xl mx-auto ${className}`}>
      {/* Result Display */}
      {result && (
        <div className="mb-8 p-6 bg-emerald-500/10 border border-emerald-500/30 rounded-xl">
          <div className="flex items-center gap-2 mb-4">
            <Check className="w-5 h-5 text-emerald-400" />
            <h3 className="text-lg font-semibold text-emerald-400">
              Licencia generada exitosamente
            </h3>
          </div>

          {/* License Key */}
          <div className="mb-4">
            <label className="block text-sm text-slate-400 mb-2">Clave de Licencia</label>
            <div className="flex gap-2">
              <code className="flex-1 p-4 bg-slate-900 border border-slate-700 rounded-lg text-sm font-mono text-slate-200 break-all max-h-32 overflow-y-auto">
                {result.license_key}
              </code>
              <div className="flex flex-col gap-2">
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
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-slate-400">ID de Licencia:</span>
              <span className="ml-2 text-slate-200 font-mono">{result.license_id}</span>
            </div>
            <div>
              <span className="text-slate-400">Titular:</span>
              <span className="ml-2 text-slate-200">
                {result.license_holder || '(no especificado)'}
              </span>
            </div>
            <div>
              <span className="text-slate-400">Máx. Clínicas:</span>
              <span className="ml-2 text-slate-200">{result.max_clinics}</span>
            </div>
            <div>
              <span className="text-slate-400">Expira:</span>
              <span className="ml-2 text-slate-200">{formatDate(result.expires_at)}</span>
            </div>
            <div className="col-span-2">
              <span className="text-slate-400">Features:</span>
              <span className="ml-2 text-slate-200">{result.features.join(', ')}</span>
            </div>
          </div>

          {/* Generate Another Button */}
          <div className="mt-6 pt-4 border-t border-slate-700">
            <Button onClick={handleReset} variant="outline" icon={RefreshCw}>
              Generar Otra Licencia
            </Button>
          </div>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
          <p className="text-red-400">{error}</p>
        </div>
      )}

      {/* Generation Form */}
      {!result && (
        <form onSubmit={handleGenerate} className="space-y-6">
          {/* License Capacity */}
          <div className="p-6 bg-slate-800/50 border border-slate-700 rounded-xl">
            <div className="flex items-center gap-2 mb-4">
              <Users className="w-5 h-5 text-blue-400" />
              <h3 className="text-lg font-medium text-slate-200">Capacidad de Licencia</h3>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-slate-400 mb-2">
                  Máximo de Clínicas <span className="text-red-400">*</span>
                </label>
                <input
                  type="number"
                  value={maxClinics}
                  onChange={(e) => setMaxClinics(Math.max(1, parseInt(e.target.value) || 1))}
                  min={1}
                  max={100}
                  required
                  className="w-full px-4 py-2.5 bg-slate-900 border border-slate-600 rounded-lg text-slate-200 placeholder-slate-500 focus:border-blue-500 focus:outline-none"
                />
                <p className="mt-1 text-xs text-slate-500">
                  El admin creará las clínicas después de activar la licencia
                </p>
              </div>
              <div>
                <label className="block text-sm text-slate-400 mb-2">
                  Titular de Licencia
                </label>
                <input
                  type="text"
                  value={licenseHolder}
                  onChange={(e) => setLicenseHolder(e.target.value)}
                  placeholder="Dr. García / Hospital Central"
                  className="w-full px-4 py-2.5 bg-slate-900 border border-slate-600 rounded-lg text-slate-200 placeholder-slate-500 focus:border-blue-500 focus:outline-none"
                />
                <p className="mt-1 text-xs text-slate-500">
                  Opcional, solo para identificación
                </p>
              </div>
            </div>
          </div>

          {/* Features */}
          <div className="p-6 bg-slate-800/50 border border-slate-700 rounded-xl">
            <div className="flex items-center gap-2 mb-4">
              <Sparkles className="w-5 h-5 text-amber-400" />
              <h3 className="text-lg font-medium text-slate-200">Funcionalidades</h3>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {features.map((feature) => (
                <label
                  key={feature.id}
                  className={`
                    flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors
                    ${
                      selectedFeatures.includes(feature.id)
                        ? 'bg-blue-500/20 border-blue-500/50'
                        : 'bg-slate-900 border-slate-700 hover:border-slate-600'
                    }
                  `}
                >
                  <input
                    type="checkbox"
                    checked={selectedFeatures.includes(feature.id)}
                    onChange={() => toggleFeature(feature.id)}
                    className="w-4 h-4 rounded border-slate-600 bg-slate-900 text-blue-500 focus:ring-blue-500"
                  />
                  <div>
                    <div className="text-sm font-medium text-slate-200">{feature.name}</div>
                    <div className="text-xs text-slate-500">{feature.description}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Expiration */}
          <div className="p-6 bg-slate-800/50 border border-slate-700 rounded-xl">
            <div className="flex items-center gap-2 mb-4">
              <Calendar className="w-5 h-5 text-cyan-400" />
              <h3 className="text-lg font-medium text-slate-200">Vigencia</h3>
            </div>

            <div className="flex flex-wrap gap-3">
              <label
                className={`
                  flex items-center gap-2 px-4 py-2 rounded-lg border cursor-pointer transition-colors
                  ${
                    expirationPreset === '1year'
                      ? 'bg-cyan-500/20 border-cyan-500/50'
                      : 'bg-slate-900 border-slate-700 hover:border-slate-600'
                  }
                `}
              >
                <input
                  type="radio"
                  name="expiration"
                  checked={expirationPreset === '1year'}
                  onChange={() => setExpirationPreset('1year')}
                  className="w-4 h-4"
                />
                <span className="text-slate-200">1 Año</span>
              </label>

              <label
                className={`
                  flex items-center gap-2 px-4 py-2 rounded-lg border cursor-pointer transition-colors
                  ${
                    expirationPreset === '2years'
                      ? 'bg-cyan-500/20 border-cyan-500/50'
                      : 'bg-slate-900 border-slate-700 hover:border-slate-600'
                  }
                `}
              >
                <input
                  type="radio"
                  name="expiration"
                  checked={expirationPreset === '2years'}
                  onChange={() => setExpirationPreset('2years')}
                  className="w-4 h-4"
                />
                <span className="text-slate-200">2 Años</span>
              </label>

              <label
                className={`
                  flex items-center gap-2 px-4 py-2 rounded-lg border cursor-pointer transition-colors
                  ${
                    expirationPreset === 'custom'
                      ? 'bg-cyan-500/20 border-cyan-500/50'
                      : 'bg-slate-900 border-slate-700 hover:border-slate-600'
                  }
                `}
              >
                <input
                  type="radio"
                  name="expiration"
                  checked={expirationPreset === 'custom'}
                  onChange={() => setExpirationPreset('custom')}
                  className="w-4 h-4"
                />
                <span className="text-slate-200">Personalizado</span>
              </label>

              {expirationPreset === 'custom' && (
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    value={customDays}
                    onChange={(e) => setCustomDays(Math.max(1, parseInt(e.target.value) || 1))}
                    min={1}
                    max={3650}
                    className="w-24 px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-slate-200 focus:border-cyan-500 focus:outline-none"
                  />
                  <span className="text-slate-400">días</span>
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
