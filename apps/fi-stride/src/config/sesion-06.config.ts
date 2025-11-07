/**
 * SESION-06 Configuration - Live Session v2.0 (TTS WASM + Encryption)
 *
 * File: apps/fi-stride/src/config/sesion-06.config.ts
 * Card: FI-STRIDE-SESION-06
 * Created: 2025-11-06
 */

import type { UseTTSConfig } from '../hooks/useTTS';

export interface SESION06Config {
  app_root: string;
  presign_url?: string;
  nas_spki_url?: string;
  locale_default: 'es-MX' | 'es-ES' | 'en-US';
  tts: UseTTSConfig;
  segment_ms: number;
  rpe_threshold_pause: number;
  use_cloud_tts: boolean;
}

// Load from environment variables
const getEnvVar = (key: string, defaultValue?: string): string | undefined => {
  if (typeof window === 'undefined') {
    return defaultValue;
  }
  return (import.meta.env as Record<string, string>)[key] || defaultValue;
};

export const sesion06Config: SESION06Config = {
  app_root: 'apps/fi-stride-pwa',
  presign_url: getEnvVar('VITE_PRESIGN_URL'),
  nas_spki_url: getEnvVar('VITE_NAS_SPKI_URL', '/nas_pubkey.spki'),
  locale_default: 'es-MX',

  // TTS Configuration (Azure primary, fallback to local engines)
  tts: {
    engines_priority: ['azure', 'piper', 'webspeech', 'kokoro'],
    use_cloud_tts: getEnvVar('VITE_USE_CLOUD_TTS') === 'true',
    azure_endpoint: getEnvVar('VITE_AZURE_TTS_ENDPOINT'),
    azure_key: getEnvVar('VITE_AZURE_TTS_KEY'),
    locale_default: 'es-MX',
    rate: 0.85, // Slower for T21 accessibility
    pitch: 1.0, // Normal pitch
    dtype: 'q8', // For local engines (Kokoro/Piper)
    timeout: 5000, // 5 second per-engine timeout
  },

  // Session configuration
  segment_ms: 60000, // 60 second segments for encryption
  rpe_threshold_pause: 4, // RPE >= 4 triggers auto-pause suggestion
};

export default sesion06Config;
