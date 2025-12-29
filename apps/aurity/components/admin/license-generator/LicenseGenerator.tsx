'use client';

/**
 * LicenseGenerator - Superadmin License Generation Form
 *
 * A comprehensive form for generating Aurity Desktop license keys.
 * Only accessible to users with FI-superadmin role.
 *
 * Features:
 * - Clinic information (ID, name)
 * - Auth0 configuration (domain, client ID, audience)
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
import { Key, Copy, Check, RefreshCw, Building2, Shield, Calendar, Sparkles } from 'lucide-react';

interface LicenseGeneratorProps {
  className?: string;
}

export function LicenseGenerator({ className = '' }: LicenseGeneratorProps) {
  const { getAccessTokenSilently } = useAuth();

  // Form state
  const [clinicId, setClinicId] = useState('');
  const [clinicName, setClinicName] = useState('');
  const [auth0Domain, setAuth0Domain] = useState('');
  const [auth0ClientId, setAuth0ClientId] = useState('');
  const [auth0Audience, setAuth0Audience] = useState('https://app.aurity.io');
  const [selectedFeatures, setSelectedFeatures] = useState<string[]>([
    'soap',
    'timeline',
    'prescriptions',
  ]);
  const [expirationPreset, setExpirationPreset] = useState<'1year' | '2years' | 'custom'>('1year');
  const [customDays, setCustomDays] = useState(365);

  // Available features
  const [features, setFeatures] = useState<FeatureInfo[]>(DEFAULT_FEATURES);

  // UI state
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<LicenseGenerationResponse | null>(null);
  const [copied, setCopied] = useState(false);

  // Load available features on mount
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
        console.warn('[LicenseGenerator] Failed to load features, using defaults');
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
        clinic_id: clinicId.trim(),
        clinic_name: clinicName.trim() || undefined,
        auth0_domain: auth0Domain.trim(),
        auth0_client_id: auth0ClientId.trim(),
        auth0_audience: auth0Audience.trim() || 'https://app.aurity.io',
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
    // Keep form values for convenience
  };

  // Format date for display
  const formatDate = (isoDate: string): string => {
    return new Date(isoDate).toLocaleDateString('es-MX', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

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
              <code className="flex-1 p-4 bg-slate-900 border border-slate-700 rounded-lg text-sm font-mono text-slate-200 break-all">
                {result.license_key}
              </code>
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

          {/* License Details */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-slate-400">ID de Licencia:</span>
              <span className="ml-2 text-slate-200 font-mono">{result.license_id}</span>
            </div>
            <div>
              <span className="text-slate-400">Clínica:</span>
              <span className="ml-2 text-slate-200">
                {result.clinic_name || result.clinic_id}
              </span>
            </div>
            <div>
              <span className="text-slate-400">Expira:</span>
              <span className="ml-2 text-slate-200">{formatDate(result.expires_at)}</span>
            </div>
            <div>
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
          {/* Clinic Information */}
          <div className="p-6 bg-slate-800/50 border border-slate-700 rounded-xl">
            <div className="flex items-center gap-2 mb-4">
              <Building2 className="w-5 h-5 text-blue-400" />
              <h3 className="text-lg font-medium text-slate-200">Datos de Clínica</h3>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-slate-400 mb-2">
                  ID de Clínica <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={clinicId}
                  onChange={(e) => setClinicId(e.target.value)}
                  placeholder="clinic_001"
                  required
                  className="w-full px-4 py-2.5 bg-slate-900 border border-slate-600 rounded-lg text-slate-200 placeholder-slate-500 focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-sm text-slate-400 mb-2">
                  Nombre de Clínica <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={clinicName}
                  onChange={(e) => setClinicName(e.target.value)}
                  placeholder="Hospital Central"
                  required
                  className="w-full px-4 py-2.5 bg-slate-900 border border-slate-600 rounded-lg text-slate-200 placeholder-slate-500 focus:border-blue-500 focus:outline-none"
                />
              </div>
            </div>
          </div>

          {/* Auth0 Configuration */}
          <div className="p-6 bg-slate-800/50 border border-slate-700 rounded-xl">
            <div className="flex items-center gap-2 mb-4">
              <Shield className="w-5 h-5 text-purple-400" />
              <h3 className="text-lg font-medium text-slate-200">Configuración Auth0</h3>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm text-slate-400 mb-2">
                  Dominio Auth0 <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={auth0Domain}
                  onChange={(e) => setAuth0Domain(e.target.value)}
                  placeholder="dev-xxxxxxxx.us.auth0.com"
                  required
                  className="w-full px-4 py-2.5 bg-slate-900 border border-slate-600 rounded-lg text-slate-200 placeholder-slate-500 focus:border-blue-500 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-slate-400 mb-2">
                    Client ID <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="text"
                    value={auth0ClientId}
                    onChange={(e) => setAuth0ClientId(e.target.value)}
                    placeholder="HBevb9r9..."
                    required
                    className="w-full px-4 py-2.5 bg-slate-900 border border-slate-600 rounded-lg text-slate-200 placeholder-slate-500 focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm text-slate-400 mb-2">Audience</label>
                  <input
                    type="text"
                    value={auth0Audience}
                    onChange={(e) => setAuth0Audience(e.target.value)}
                    placeholder="https://app.aurity.io"
                    className="w-full px-4 py-2.5 bg-slate-900 border border-slate-600 rounded-lg text-slate-200 placeholder-slate-500 focus:border-blue-500 focus:outline-none"
                  />
                </div>
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
            disabled={!clinicId || !auth0Domain || !auth0ClientId}
          >
            {isLoading ? 'Generando...' : 'Generar Licencia'}
          </Button>
        </form>
      )}
    </div>
  );
}
