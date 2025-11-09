/**
 * useTTS Hook - Advanced TTS engine selector with fallback chain
 *
 * Engines (priority order):
 * 1. Kokoro WASM - Fast, offline, ~300MB (q8 quantization)
 * 2. Piper ONNX - Quality, offline, ~100MB per voice
 * 3. Web Speech API - Browser native, free, no downloads
 * 4. Azure TTS - Cloud, premium quality (optional, requires API key)
 *
 * File: apps/fi-stride/src/hooks/useTTS.ts
 * Card: FI-STRIDE-SESION-06
 * Created: 2025-11-06
 */

import { useEffect, useRef, useState, useCallback } from 'react';

type TTSEngine = 'kokoro' | 'piper' | 'webspeech' | 'azure';
type TTSState = 'idle' | 'initializing' | 'ready' | 'synthesizing' | 'error';
type QuantizationType = 'fp32' | 'fp16' | 'q8' | 'q4';

interface UseTTSConfig {
  engines_priority?: TTSEngine[]; // Order to try: ['kokoro', 'piper', 'webspeech', 'azure']
  dtype?: QuantizationType; // Kokoro quantization level
  timeout?: number; // Per-engine timeout in ms
  use_cloud_tts?: boolean; // Enable Azure TTS fallback
  azure_endpoint?: string; // Azure TTS endpoint (if use_cloud_tts=true)
  azure_key?: string; // Azure TTS API key (if use_cloud_tts=true)
  locale_default?: 'es-ES' | 'en-US'; // Default language
  rate?: number; // Speech rate (0.5-2.0)
  pitch?: number; // Speech pitch (0.5-2.0)
}

interface TTSResult {
  audio: AudioBuffer | Blob | Float32Array; // Varies by engine
  engine: TTSEngine;
  duration?: number;
}

interface UseTTSReturn {
  state: TTSState;
  error: Error | null;
  synthesize: (text: string) => Promise<TTSResult>;
  isReady: boolean;
  activeEngine: TTSEngine | null;
  engines_available: TTSEngine[];
}

// Queue for requests during initialization
interface QueuedRequest {
  text: string;
  resolve: (result: TTSResult) => void;
  reject: (error: Error) => void;
}

// Helper: Check if Kokoro is available
async function isKokoroAvailable(): Promise<boolean> {
  try {
    // Check if we can dynamically import kokoro-js
    // For now, check if transformers.js is available
    return typeof window !== 'undefined' && 'indexedDB' in window;
  } catch {
    return false;
  }
}

// Helper: Check if Piper is available
async function isPiperAvailable(): Promise<boolean> {
  try {
    return typeof window !== 'undefined' && 'indexedDB' in window;
  } catch {
    return false;
  }
}

// Helper: Check if Web Speech API is available
function isWebSpeechAvailable(): boolean {
  if (typeof window === 'undefined') return false;
  const speech = (window as any).SpeechSynthesisUtterance;
  const synth = (window as any).speechSynthesis;
  return !!(speech && synth);
}

// Helper: Synthesize using Web Speech API
function synthesizeWebSpeech(
  text: string,
  config: UseTTSConfig
): Promise<TTSResult> {
  return new Promise((resolve, reject) => {
    if (!isWebSpeechAvailable()) {
      reject(new Error('Web Speech API not available'));
      return;
    }

    try {
      // Cancel any previous utterance
      window.speechSynthesis.cancel();

      // Small delay to ensure cancel completes
      setTimeout(() => {
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = config.locale_default || 'es-ES';
        utterance.rate = config.rate || 0.9;
        utterance.pitch = config.pitch || 1.0;
        utterance.volume = 1.0; // Max volume

        // Try to select feminine Spanish voice (prioritize Spain/Mexico)
        const voices = window.speechSynthesis.getVoices();

        // First try: Spanish female voice (es-ES or es-MX)
        let selectedVoice = voices.find(
          (v) =>
            (v.lang === 'es-ES' || v.lang === 'es-MX' || v.lang.startsWith('es')) &&
            (v.name.toLowerCase().includes('female') ||
              v.name.toLowerCase().includes('woman') ||
              v.name.toLowerCase().includes('mujer') ||
              v.name.toLowerCase().includes('monica') ||
              v.name.toLowerCase().includes('lucia') ||
              v.name.toLowerCase().includes('conchita'))
        );

        // Fallback: any Spanish voice
        if (!selectedVoice) {
          selectedVoice = voices.find((v) => v.lang.startsWith('es'));
        }

        if (selectedVoice) {
          utterance.voice = selectedVoice;
        }

        const startTime = Date.now();
        utterance.onend = () => {
          const duration = (Date.now() - startTime) / 1000;
          resolve({
            audio: new Float32Array(0), // Web Speech doesn't return audio buffer
            engine: 'webspeech',
            duration,
          });
        };

        utterance.onerror = (event) => {
          reject(new Error(`Web Speech error: ${event.error}`));
        };

        window.speechSynthesis.speak(utterance);
      }, 100);
    } catch (error) {
      reject(error);
    }
  });
}

// Helper: Synthesize using Azure TTS (real implementation)
async function synthesizeAzure(
  text: string,
  config: UseTTSConfig
): Promise<TTSResult> {
  if (!config.azure_endpoint || !config.azure_key) {
    throw new Error('Azure TTS not configured (missing endpoint/key)');
  }

  try {
    // Azure OpenAI TTS endpoint expects specific format
    const response = await fetch(config.azure_endpoint, {
      method: 'POST',
      headers: {
        'api-key': config.azure_key,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        input: text,
        voice: 'nova', // Female voice for KATNISS
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Azure TTS error (${response.status}): ${errorText}`);
    }

    const startTime = Date.now();
    const arrayBuffer = await response.arrayBuffer();
    const duration = (Date.now() - startTime) / 1000;

    // Auto-play the audio
    try {
      const audioBlob = new Blob([arrayBuffer], { type: 'audio/mpeg' });
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio();
      audio.src = audioUrl;
      audio.play().catch((err) => console.warn('Audio playback failed:', err));
    } catch (playbackErr) {
      console.warn('Could not auto-play audio:', playbackErr);
    }

    return {
      audio: arrayBuffer,
      engine: 'azure',
      duration,
    };
  } catch (error) {
    throw error;
  }
}

/**
 * useTTS Hook
 *
 * Usage:
 * ```tsx
 * const { synthesize, isReady, activeEngine } = useTTS({
 *   engines_priority: ['kokoro', 'piper', 'webspeech'],
 *   locale_default: 'es-ES',
 *   rate: 0.85,
 * });
 *
 * const handleSpeak = async () => {
 *   try {
 *     const result = await synthesize('Hola mundo');
 *     // Play result.audio
 *   } catch (error) {
 *     console.error('TTS failed:', error);
 *   }
 * };
 * ```
 */
export function useTTS(config: UseTTSConfig = {}): UseTTSReturn {
  const {
    engines_priority = ['azure', 'piper', 'webspeech', 'kokoro'], // Azure first (user has credentials)
    dtype = 'q8',
    timeout = 5000,
    use_cloud_tts = true, // Azure enabled by default
    locale_default = 'es-ES',
    rate = 0.85,
    pitch = 1.0,
  } = config;

  const [state, setState] = useState<TTSState>('initializing');
  const [error, setError] = useState<Error | null>(null);
  const [activeEngine, setActiveEngine] = useState<TTSEngine | null>(null);
  const [engines_available, setEnginesAvailable] = useState<TTSEngine[]>([]);

  const queueRef = useRef<QueuedRequest[]>([]);
  const engineRef = useRef<any>(null);
  const isInitializingRef = useRef(false);

  // Detect available engines at startup
  useEffect(() => {
    const detectEngines = async () => {
      const available: TTSEngine[] = [];

      for (const engine of engines_priority) {
        try {
          let isAvailable = false;

          if (engine === 'kokoro') {
            isAvailable = await isKokoroAvailable();
          } else if (engine === 'piper') {
            isAvailable = await isPiperAvailable();
          } else if (engine === 'webspeech') {
            isAvailable = isWebSpeechAvailable();
          } else if (engine === 'azure') {
            isAvailable = use_cloud_tts && !!config.azure_endpoint && !!config.azure_key;
          }

          if (isAvailable) {
            available.push(engine);
          }
        } catch {
          // Engine not available, skip
        }
      }

      setEnginesAvailable(available);

      // If no engines available, error out
      if (available.length === 0) {
        setError(new Error('No TTS engines available'));
        setState('error');
        return;
      }

      // Try to initialize engines in priority order
      await initializeEngines(available);
    };

    detectEngines();
  }, [engines_priority, use_cloud_tts, config.azure_endpoint, config.azure_key]);

  // Initialize engines with fallback chain
  const initializeEngines = async (available: TTSEngine[]) => {
    if (isInitializingRef.current) return;
    isInitializingRef.current = true;

    try {
      for (const engine of available) {
        try {
          // Initialize this engine
          await initializeEngine(engine);
          setActiveEngine(engine);
          setState('ready');
          processQueue();
          return; // Success, stop trying other engines
        } catch (err) {
          console.warn(`Failed to initialize ${engine}:`, err);
          continue; // Try next engine
        }
      }

      // All engines failed
      throw new Error(`Failed to initialize any TTS engine: ${available.join(', ')}`);
    } catch (err) {
      setError(err as Error);
      setState('error');
    } finally {
      isInitializingRef.current = false;
    }
  };

  // Initialize a specific engine
  const initializeEngine = async (engine: TTSEngine): Promise<void> => {
    const timeoutPromise = new Promise<void>((_, reject) =>
      setTimeout(() => reject(new Error(`${engine} initialization timeout`)), timeout)
    );

    const initPromise = (async () => {
      switch (engine) {
        case 'kokoro': {
          // Lazy load Kokoro
          // const { KokoroTTS } = await import('kokoro-js');
          // engineRef.current = await KokoroTTS.from_pretrained(
          //   'onnx-community/Kokoro-82M-ONNX',
          //   { dtype, device: 'wasm' }
          // );
          // For now, stub
          engineRef.current = { engine: 'kokoro' };
          break;
        }

        case 'piper': {
          // Lazy load Piper
          // const tts = await import('@mintplex-labs/piper-tts-web');
          // engineRef.current = tts;
          // For now, stub
          engineRef.current = { engine: 'piper' };
          break;
        }

        case 'webspeech': {
          // Web Speech API - no initialization needed
          if (!isWebSpeechAvailable()) {
            throw new Error('Web Speech API not available');
          }
          engineRef.current = { engine: 'webspeech' };
          break;
        }

        case 'azure': {
          // Azure TTS - validate config
          if (!config.azure_endpoint || !config.azure_key) {
            throw new Error('Azure TTS not configured');
          }
          engineRef.current = { engine: 'azure' };
          break;
        }

        default:
          throw new Error(`Unknown engine: ${engine}`);
      }
    })();

    await Promise.race([initPromise, timeoutPromise]);
  };

  // Process queued requests
  const processQueue = () => {
    while (queueRef.current.length > 0 && state === 'ready') {
      const { text, resolve, reject } = queueRef.current.shift()!;
      synthesize(text)
        .then(resolve)
        .catch(reject);
    }
  };

  // Main synthesize function with fallback chain
  const synthesize = useCallback(
    async (text: string): Promise<TTSResult> => {
      // Queue if still initializing
      if (state === 'initializing') {
        return new Promise((resolve, reject) => {
          queueRef.current.push({ text, resolve, reject });
        });
      }

      if (state === 'error') {
        throw error || new Error('TTS in error state');
      }

      if (!activeEngine) {
        throw new Error('No active TTS engine');
      }

      setState('synthesizing');

      try {
        // Try current engine
        let result: TTSResult;

        if (activeEngine === 'webspeech') {
          result = await synthesizeWebSpeech(text, { ...config, rate, pitch, locale_default });
        } else if (activeEngine === 'azure') {
          result = await synthesizeAzure(text, config);
        } else if (activeEngine === 'kokoro') {
          // Stub: Replace with real Kokoro implementation
          result = await synthesizeWebSpeech(text, { ...config, rate, pitch, locale_default });
        } else if (activeEngine === 'piper') {
          // Stub: Replace with real Piper implementation
          result = await synthesizeWebSpeech(text, { ...config, rate, pitch, locale_default });
        } else {
          throw new Error(`Unknown engine: ${activeEngine}`);
        }

        setState('ready');
        return result;
      } catch (err) {
        // Try fallback engines
        const currentIdx = engines_available.indexOf(activeEngine);
        const remainingEngines = engines_available.slice(currentIdx + 1);

        for (const fallbackEngine of remainingEngines) {
          try {
            await initializeEngine(fallbackEngine);
            setActiveEngine(fallbackEngine);

            let result: TTSResult;
            if (fallbackEngine === 'webspeech') {
              result = await synthesizeWebSpeech(text, { ...config, rate, pitch, locale_default });
            } else if (fallbackEngine === 'azure') {
              result = await synthesizeAzure(text, config);
            } else {
              throw new Error(`Fallback engine ${fallbackEngine} not implemented`);
            }

            setState('ready');
            return result;
          } catch {
            continue; // Try next fallback
          }
        }

        // All engines failed
        setState('error');
        const fallbackErr = new Error(
          `All TTS engines failed. Last error: ${(err as Error).message}`
        );
        setError(fallbackErr);
        throw fallbackErr;
      }
    },
    [activeEngine, state, error, engines_available, config, rate, pitch, locale_default]
  );

  return {
    state,
    error,
    synthesize,
    isReady: state === 'ready',
    activeEngine,
    engines_available,
  };
}

export type { UseTTSConfig, UseTTSReturn, TTSEngine, TTSState, TTSResult };
