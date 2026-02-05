/**
 * usePersonas Hook
 *
 * Fetches available AI personas from backend API.
 * Single source of truth - personas are defined in backend YAML files.
 *
 * Architecture:
 * - Backend: /backend/config/personas/*.yaml
 * - API: GET /api/admin/personas
 * - Frontend: This hook (cached)
 *
 * @example
 * const { personas, loading, error } = usePersonas();
 */

import { useState, useEffect } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { backendHealth } from '@/lib/api/backend-health';

export interface PersonaOption {
  id: string;
  name: string;
  description: string;
  icon?: string; // Optional frontend-only icon mapping
  voice?: string; // TTS voice ID (e.g., "nova", "alloy")
  model?: string; // LLM model (e.g., "qwen3:1.7b", "gpt-4o-mini")
  temperature?: number; // Sampling temperature (0.0-1.0)
  maxTokens?: number; // Max tokens for response
}

interface UsePersonasReturn {
  personas: PersonaOption[];
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:7001';
const AUTH0_AUDIENCE = process.env.NEXT_PUBLIC_AUTH0_AUDIENCE || 'https://app.aurity.io';
const AUTH0_SCOPE = process.env.NEXT_PUBLIC_AUTH0_SCOPE || 'openid profile email offline_access';

// Icon mapping for personas (frontend only)
const PERSONA_ICON_MAP: Record<string, string> = {
  'general_assistant': 'Stethoscope',
  'soap_editor': 'FileEdit',
  'clinical_advisor': 'Microscope',
  'onboarding_guide': 'Compass',
  'pattern_weaver': 'Network',
  'sovereignty_guide': 'Shield',
  'growth_mirror': 'TrendingUp',
  'honest_limiter': 'Activity',
};

// Fallback personas when backend is unavailable (offline mode)
// These should match the personas defined in backend/config/personas/*.yaml
const FALLBACK_PERSONAS: PersonaOption[] = [
  {
    id: 'general_assistant',
    name: 'Asistente General',
    description: 'Asistente médico general para consultas variadas',
    icon: 'Stethoscope',
    model: 'qwen3:1.7b',
    temperature: 0.7,
    maxTokens: 2048,
  },
  {
    id: 'soap_editor',
    name: 'Editor SOAP',
    description: 'Especialista en notas clínicas formato SOAP',
    icon: 'FileEdit',
    model: 'qwen3:1.7b',
    temperature: 0.3,
    maxTokens: 4096,
  },
  {
    id: 'clinical_advisor',
    name: 'Asesor Clínico',
    description: 'Consultor para decisiones clínicas complejas',
    icon: 'Microscope',
    model: 'qwen3:1.7b',
    temperature: 0.5,
    maxTokens: 2048,
  },
  {
    id: 'onboarding_guide',
    name: 'Guía de Onboarding',
    description: 'Te acompaña en tu primer uso de la plataforma',
    icon: 'Compass',
    model: 'qwen3:1.7b',
    temperature: 0.8,
    maxTokens: 1024,
  },
  {
    id: 'pattern_weaver',
    name: 'Tejedor de Patrones',
    description: 'Identifica patrones en datos clínicos longitudinales',
    icon: 'Network',
    model: 'qwen3:1.7b',
    temperature: 0.4,
    maxTokens: 4096,
  },
  {
    id: 'sovereignty_guide',
    name: 'Guía de Soberanía',
    description: 'Experto en privacidad y soberanía de datos médicos',
    icon: 'Shield',
    model: 'qwen3:1.7b',
    temperature: 0.6,
    maxTokens: 2048,
  },
  {
    id: 'growth_mirror',
    name: 'Espejo de Crecimiento',
    description: 'Refleja tu progreso y áreas de mejora profesional',
    icon: 'TrendingUp',
    model: 'qwen3:1.7b',
    temperature: 0.7,
    maxTokens: 2048,
  },
  {
    id: 'honest_limiter',
    name: 'Limitador Honesto',
    description: 'Te ayuda a establecer límites saludables en tu práctica',
    icon: 'Activity',
    model: 'qwen3:1.7b',
    temperature: 0.5,
    maxTokens: 1024,
  },
];

export function usePersonas(): UsePersonasReturn {
  const [personas, setPersonas] = useState<PersonaOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { getAccessTokenSilently, isAuthenticated } = useAuth();

  const fetchPersonas = async () => {
    console.debug('[usePersonas] fetchPersonas called, backend available?', backendHealth.isAvailable());
    // Use fallback personas if backend is known to be unavailable
    if (!backendHealth.isAvailable()) {
      console.debug('[usePersonas] backend unavailable, using FALLBACK_PERSONAS');
      setLoading(false);
      setPersonas(FALLBACK_PERSONAS);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      // Obtain bearer token for public workflow route
      let token: string | undefined;
      if (isAuthenticated) {
        try {
          // audience and scope are configured in Auth0Provider
          token = await getAccessTokenSilently();
        } catch (tokenErr) {
          // Do not fail personas fetch solely due to token issues; fallback below
          console.warn('[usePersonas] getAccessTokenSilently failed:', tokenErr);
        }
      }

      const response = await fetch(`${BACKEND_URL}/api/aurity/assistant/personas`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });

      if (!response.ok) {
        // 401/403 = not authenticated, use fallback silently (expected in onboarding)
        if (response.status === 401 || response.status === 403) {
          console.debug('[usePersonas] Not authenticated, using FALLBACK_PERSONAS');
          setPersonas(FALLBACK_PERSONAS);
          setLoading(false);
          return;
        }
        throw new Error(`Failed to fetch personas: ${response.status}`);
      }

      const data = await response.json();

      // Transform backend response to frontend format
      const transformedPersonas: PersonaOption[] = data.personas.map((p: any) => ({
        id: p.id,
        name: p.name,
        description: p.description,
        icon: PERSONA_ICON_MAP[p.id],
        voice: p.voice, // TTS voice from backend
        model: p.model, // LLM model from persona config
        temperature: p.temperature,
        maxTokens: p.max_tokens,
      }));

      setPersonas(transformedPersonas);
      console.debug('[usePersonas] fetched personas, count=', transformedPersonas.length);
      // Report success to circuit breaker
      backendHealth.reportSuccess();
    } catch (err) {
      // Report failure to circuit breaker
      backendHealth.reportFailure();

      // Don't log connection errors (they're expected when backend is down)
      const errorStr = String(err);
      const isConnectionError =
        (err instanceof TypeError && errorStr.includes('fetch')) ||
        errorStr.includes('ERR_CONNECTION_REFUSED') ||
        errorStr.includes('NetworkError');

      if (!isConnectionError) {
        console.error('[usePersonas] Error fetching personas:', err);
      }
      setError(err instanceof Error ? err.message : 'Unknown error');

      // Fallback to default personas on error (offline mode)
      console.debug('[usePersonas] fetch error, using FALLBACK_PERSONAS');
      setPersonas(FALLBACK_PERSONAS);
    } finally {
      console.debug('[usePersonas] fetchPersonas finally, setting loading=false');
      setLoading(false);
    }
  };

  useEffect(() => {
    // Fetch on mount (circuit breaker will handle failures)
    fetchPersonas();

    // Subscribe to health changes - refetch when backend comes back online
    const unsubscribe = backendHealth.subscribe((available) => {
      if (available) {
        fetchPersonas();
      }
    });

    return unsubscribe;
  }, []);

  return {
    personas,
    loading,
    error,
    refetch: fetchPersonas,
  };
}
