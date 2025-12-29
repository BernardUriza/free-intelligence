'use client';

/**
 * LicenseGenerator - Superadmin License Generation Form
 *
 * A comprehensive form for generating Aurity Desktop license keys.
 * Only accessible to users with FI-superadmin role.
 *
 * Features:
 * - Clinic selector with autocomplete (loads from backend)
 * - Option to create new clinic manually
 * - Auth0 configuration with defaults from current env
 * - Feature toggles (checkboxes)
 * - Expiration date picker (preset + custom)
 * - Copy-to-clipboard for generated key
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
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
import { fetchClinics, Clinic } from '@/lib/api/clinics';
import {
  Key,
  Copy,
  Check,
  RefreshCw,
  Building2,
  Shield,
  Calendar,
  Sparkles,
  Search,
  Plus,
  ChevronDown,
  Download,
} from 'lucide-react';

interface LicenseGeneratorProps {
  className?: string;
}

export function LicenseGenerator({ className = '' }: LicenseGeneratorProps) {
  const { getAccessTokenSilently } = useAuth();

  // Clinic selection state
  const [clinics, setClinics] = useState<Clinic[]>([]);
  const [clinicsLoading, setClinicsLoading] = useState(true);
  const [selectedClinic, setSelectedClinic] = useState<Clinic | null>(null);
  const [isNewClinic, setIsNewClinic] = useState(false);
  const [clinicSearchQuery, setClinicSearchQuery] = useState('');
  const [showClinicDropdown, setShowClinicDropdown] = useState(false);

  // Form state (for new clinic or manual override)
  const [clinicId, setClinicId] = useState('');
  const [clinicName, setClinicName] = useState('');

  // Auth0 fields - pre-fill with current env values
  const [auth0Domain, setAuth0Domain] = useState(
    process.env.NEXT_PUBLIC_AUTH0_DOMAIN || ''
  );
  const [auth0ClientId, setAuth0ClientId] = useState(
    process.env.NEXT_PUBLIC_AUTH0_CLIENT_ID || ''
  );
  const [auth0Audience, setAuth0Audience] = useState(
    process.env.NEXT_PUBLIC_AUTH0_AUDIENCE || 'https://app.aurity.io'
  );

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

  // Filter clinics based on search query
  const filteredClinics = useMemo(() => {
    if (!clinicSearchQuery.trim()) return clinics;
    const query = clinicSearchQuery.toLowerCase();
    return clinics.filter(
      (c) =>
        c.name.toLowerCase().includes(query) ||
        c.clinic_id.toLowerCase().includes(query)
    );
  }, [clinics, clinicSearchQuery]);

  // Load clinics on mount
  useEffect(() => {
    const loadClinics = async () => {
      try {
        setClinicsLoading(true);
        const data = await fetchClinics(false); // Include inactive clinics
        setClinics(data);
      } catch (err) {
        console.warn('[LicenseGenerator] Failed to load clinics:', err);
      } finally {
        setClinicsLoading(false);
      }
    };
    loadClinics();
  }, []);

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

  // Handle clinic selection
  const handleSelectClinic = (clinic: Clinic) => {
    setSelectedClinic(clinic);
    setClinicId(clinic.clinic_id);
    setClinicName(clinic.name);
    setIsNewClinic(false);
    setShowClinicDropdown(false);
    setClinicSearchQuery('');
  };

  // Handle new clinic mode
  const handleNewClinic = () => {
    setSelectedClinic(null);
    setClinicId('');
    setClinicName('');
    setIsNewClinic(true);
    setShowClinicDropdown(false);
    setClinicSearchQuery('');
  };

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

    // Create filename: clinic-name-YYYY-MM-DD.key
    const date = new Date().toISOString().split('T')[0];
    const clinicSlug = (result.clinic_name || result.clinic_id)
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '');
    const filename = `${clinicSlug}-${date}.key`;

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
  const isFormValid = clinicId && auth0Domain && auth0ClientId;

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
          {/* Clinic Selection */}
          <div className="p-6 bg-slate-800/50 border border-slate-700 rounded-xl">
            <div className="flex items-center gap-2 mb-4">
              <Building2 className="w-5 h-5 text-blue-400" />
              <h3 className="text-lg font-medium text-slate-200">Seleccionar Clínica</h3>
            </div>

            {/* Clinic Selector */}
            <div className="relative mb-4">
              <div
                onClick={() => setShowClinicDropdown(!showClinicDropdown)}
                className="w-full px-4 py-3 bg-slate-900 border border-slate-600 rounded-lg text-slate-200 cursor-pointer flex items-center justify-between hover:border-slate-500 transition-colors"
              >
                <span className={selectedClinic || isNewClinic ? 'text-slate-200' : 'text-slate-500'}>
                  {selectedClinic
                    ? `${selectedClinic.name} (${selectedClinic.clinic_id})`
                    : isNewClinic
                    ? 'Nueva Clínica (manual)'
                    : 'Selecciona una clínica...'}
                </span>
                <ChevronDown className={`w-5 h-5 text-slate-400 transition-transform ${showClinicDropdown ? 'rotate-180' : ''}`} />
              </div>

              {/* Dropdown */}
              {showClinicDropdown && (
                <div className="absolute z-50 w-full mt-2 bg-slate-900 border border-slate-600 rounded-lg shadow-xl max-h-80 overflow-hidden">
                  {/* Search Input */}
                  <div className="p-3 border-b border-slate-700">
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                      <input
                        type="text"
                        value={clinicSearchQuery}
                        onChange={(e) => setClinicSearchQuery(e.target.value)}
                        placeholder="Buscar clínica..."
                        className="w-full pl-10 pr-4 py-2 bg-slate-800 border border-slate-600 rounded-lg text-slate-200 placeholder-slate-500 focus:border-blue-500 focus:outline-none"
                        autoFocus
                      />
                    </div>
                  </div>

                  {/* Options */}
                  <div className="max-h-56 overflow-y-auto">
                    {/* New Clinic Option */}
                    <button
                      type="button"
                      onClick={handleNewClinic}
                      className="w-full px-4 py-3 flex items-center gap-3 hover:bg-slate-800 text-left border-b border-slate-700"
                    >
                      <Plus className="w-5 h-5 text-emerald-400" />
                      <div>
                        <div className="text-emerald-400 font-medium">Nueva Clínica</div>
                        <div className="text-xs text-slate-500">Crear entrada manual</div>
                      </div>
                    </button>

                    {/* Clinic List */}
                    {clinicsLoading ? (
                      <div className="px-4 py-6 text-center text-slate-500">
                        Cargando clínicas...
                      </div>
                    ) : filteredClinics.length === 0 ? (
                      <div className="px-4 py-6 text-center text-slate-500">
                        No se encontraron clínicas
                      </div>
                    ) : (
                      filteredClinics.map((clinic) => (
                        <button
                          key={clinic.clinic_id}
                          type="button"
                          onClick={() => handleSelectClinic(clinic)}
                          className={`w-full px-4 py-3 flex items-center gap-3 hover:bg-slate-800 text-left ${
                            selectedClinic?.clinic_id === clinic.clinic_id ? 'bg-blue-500/10' : ''
                          }`}
                        >
                          <Building2 className="w-5 h-5 text-slate-400" />
                          <div className="flex-1 min-w-0">
                            <div className="text-slate-200 font-medium truncate">{clinic.name}</div>
                            <div className="text-xs text-slate-500 truncate">
                              {clinic.clinic_id} · {clinic.specialty || 'General'}
                              {!clinic.is_active && (
                                <span className="ml-2 text-amber-500">(Inactiva)</span>
                              )}
                            </div>
                          </div>
                          {selectedClinic?.clinic_id === clinic.clinic_id && (
                            <Check className="w-5 h-5 text-blue-400" />
                          )}
                        </button>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Manual Clinic Fields (shown when new clinic or for override) */}
            {(isNewClinic || selectedClinic) && (
              <div className="grid grid-cols-2 gap-4 pt-4 border-t border-slate-700">
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
                    disabled={!!selectedClinic}
                    className="w-full px-4 py-2.5 bg-slate-900 border border-slate-600 rounded-lg text-slate-200 placeholder-slate-500 focus:border-blue-500 focus:outline-none disabled:opacity-60 disabled:cursor-not-allowed"
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
                    disabled={!!selectedClinic}
                    className="w-full px-4 py-2.5 bg-slate-900 border border-slate-600 rounded-lg text-slate-200 placeholder-slate-500 focus:border-blue-500 focus:outline-none disabled:opacity-60 disabled:cursor-not-allowed"
                  />
                </div>
              </div>
            )}
          </div>

          {/* Auth0 Configuration */}
          <div className="p-6 bg-slate-800/50 border border-slate-700 rounded-xl">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Shield className="w-5 h-5 text-purple-400" />
                <h3 className="text-lg font-medium text-slate-200">Configuración Auth0</h3>
              </div>
              <span className="text-xs text-slate-500 bg-slate-700/50 px-2 py-1 rounded">
                Pre-llenado con config actual
              </span>
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
            disabled={!isFormValid}
          >
            {isLoading ? 'Generando...' : 'Generar Licencia'}
          </Button>
        </form>
      )}

      {/* Click outside to close dropdown */}
      {showClinicDropdown && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setShowClinicDropdown(false)}
        />
      )}
    </div>
  );
}
