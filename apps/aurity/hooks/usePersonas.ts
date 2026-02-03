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
import { backendHealth } from '@aurity-standalone/api-client/backend-health';
import { api } from '@/lib/api/client';

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
    model: undefined,
    temperature: 0.7,
    maxTokens: 2048,
  },
  {
    id: 'soap_editor',
    name: 'Editor SOAP',
    description: 'Especialista en notas clínicas formato SOAP',
    icon: 'FileEdit',
    model: undefined,
    temperature: 0.3,
    maxTokens: 4096,
  },
  {
    id: 'clinical_advisor',
    name: 'Asesor Clínico',
    description: 'Consultor para decisiones clínicas complejas',
    icon: 'Microscope',
    model: undefined,
    temperature: 0.5,
    maxTokens: 2048,
  },
  {
    id: 'onboarding_guide',
    name: 'Guía de Onboarding',
    description: 'Te acompaña en tu primer uso de la plataforma',
    icon: 'Compass',
    model: undefined,
    temperature: 0.8,
    maxTokens: 1024,
  },
  {
    id: 'pattern_weaver',
    name: 'Tejedor de Patrones',
    description: 'Identifica patrones en datos clínicos longitudinales',
    icon: 'Network',
    model: undefined,
    temperature: 0.4,
    maxTokens: 4096,
  },
  {
    id: 'sovereignty_guide',
    name: 'Guía de Soberanía',
    description: 'Experto en privacidad y soberanía de datos médicos',
    icon: 'Shield',
    model: undefined,
    temperature: 0.6,
    maxTokens: 2048,
  },
  {
    id: 'growth_mirror',
    name: 'Espejo de Crecimiento',
    description: 'Refleja tu progreso y áreas de mejora profesional',
    icon: 'TrendingUp',
    model: undefined,
    temperature: 0.7,
    maxTokens: 2048,
  },
  {
    id: 'honest_limiter',
    name: 'Limitador Honesto',
    description: 'Te ayuda a establecer límites saludables en tu práctica',
    icon: 'Activity',
    model: undefined,
    temperature: 0.5,
    maxTokens: 1024,
  },
];

export function usePersonas(): UsePersonasReturn {
  const [personas, setPersonas] = useState<PersonaOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPersonas = async () => {
    // Use fallback personas if backend is known to be unavailable
    if (!backendHealth.isAvailable()) {
      setLoading(false);
      setPersonas(FALLBACK_PERSONAS);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      // api.get handles auth token automatically via getAuthToken() in @/lib/api/client
      const data = await api.get<{ personas: Array<{
        id: string;
        name: string;
        description: string;
        voice?: string;
        model?: string;
        temperature?: number;
        max_tokens?: number;
      }> }>('/api/aurity/personas');

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
      setPersonas(FALLBACK_PERSONAS);
    } finally {
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
