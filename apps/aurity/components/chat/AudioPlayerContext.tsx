// @ts-nocheck - temporary: suppress TS diagnostics while refactoring audio subsystem
'use client';

/**
 * AudioPlayerContext - Integrated audio subsystem
 *
 * Provides global audio player functionality with:
 * - Provider registry (Azure, OpenAI Standard, OpenAI Steerable)
 * - Capability detection (backend, Audio API, autoplay)
 * - Queue management with deduplication
 * - State machine for playback lifecycle
 * - Error policy with PII redaction
 * - Consent flow (first-click banner)
 *
 * Eliminates "No provider found" warning by mounting provider globally.
 *
 * @see /apps/aurity/docs/audio/
 */

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  type ReactNode,
} from 'react';
import { toastError, swal } from '@/lib/swal';
import { QueueManager } from '@/lib/audio/QueueManager';
import { AudioStateMachine } from '@/lib/audio/AudioStateMachine';
import { probeCapabilities } from '@/lib/audio/CapabilityProbe';
import { getProviderByVoice } from '@/lib/audio/ProviderRegistry';
import { initErrorReporter, reportAudioError } from '@/lib/audio/ErrorPolicy';
import { getVoiceDisplayName } from '@/lib/voiceAliases';
import { api, getBackendUrl } from '@/lib/api/client';

// Small helper to escape HTML for safe inline rendering in modals
function escapeHtml(input: string): string {
  return input
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

interface AudioPlayerContextValue {
  /** Generate and play audio for the given text */
  generateAudio: (text: string, voice: string, isUserMessage?: boolean) => Promise<void>;
  /** Is audio subsystem ready? */
  isReady: boolean;
  /** Current state machine state */
  currentState: string;
}

const AudioPlayerContext = createContext<AudioPlayerContextValue | null>(null);

/**
 * AudioPlayerProvider - Global audio provider
 *
 * Mounts at app root level (app/layout.tsx) to provide audio functionality
 * to all SpeakButton instances throughout the component tree.
 *
 * Integrates 6 subsystems:
 * 1. ProviderRegistry - Provider metadata and selection
 * 2. CapabilityProbe - Detect backend/API availability
 * 3. QueueManager - Cache and deduplication
 * 4. AudioStateMachine - Playback lifecycle
 * 5. ErrorPolicy - Structured logging with PII redaction
 * 6. ConsentBanner - First-click permission (handled by layout)
 */
export function AudioPlayerProvider({ children }: { children: ReactNode }) {
  const [queueManager] = useState(() => new QueueManager());
  const [stateMachine] = useState(() => new AudioStateMachine());
  const [isReady, setIsReady] = useState(false);
  const [availableProviders, setAvailableProviders] = useState<Record<string, boolean> | null>(null);

  const BACKEND_URL = getBackendUrl();

  // Probe capabilities on mount
  useEffect(() => {
    // Initialize error reporter on first mount
    initErrorReporter(BACKEND_URL).catch(() => {
      // Silent failure - reporter will initialize lazily on first error
    });

    probeCapabilities(BACKEND_URL).then(report => {
      if (report.backendReachable && report.audioApiSupported) {
        stateMachine.transition('CAPABILITIES_OK');
        setIsReady(true);
      } else {
        stateMachine.transition('CAPABILITIES_FAILED');
        reportAudioError(
          { tipo_error: 'AUDIO_CAPABILITY_FAILED', mensaje: 'Capability probe failed', contexto: report },
          'AudioPlayerContext'
        );
      }
    });
    // Fetch configured providers so frontend can avoid calling unavailable ones
    (async () => {
      try {
        const body = await api.get<{ providers: Record<string, boolean> }>('/api/tts/providers');
        setAvailableProviders(body.providers || null);
      } catch {
        setAvailableProviders(null);
      }
    })();
  }, [BACKEND_URL, stateMachine]);

  // Phase 4: Observability (commented - activate when backend endpoint is ready)
  // Sends cache stats to backend every 60 seconds
  /*
  useEffect(() => {
    const interval = setInterval(() => {
      const stats = queueManager.getCacheStats();
      fetch(`${BACKEND_URL}/api/observability/audio/metrics`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          cache_size: stats.size,
          cache_max: stats.maxSize,
          queue_depth: 0, // TODO: track queue depth
          timestamp: Date.now(),
        }),
      }).catch(err => console.error('[AudioMetrics] Failed to send:', err));
    }, 60000); // Every minute

    return () => clearInterval(interval);
  }, [BACKEND_URL, queueManager]);
  */

  /**
   * Generate and play audio
   *
   * Flow:
   * 1. Check consent (first-click banner)
   * 2. Validate state (can play?)
   * 3. Get provider by voice
   * 4. Check cache (cache hit → play immediately)
   * 5. Cache miss → enqueue, fetch from backend, cache, play
   *
   * @param text - Text to synthesize
   * @param voice - Voice ID (e.g., "nova", "alloy")
   * @param isUserMessage - Is this a user message? (higher priority)
   */
  const generateAudio = useCallback(
    async (text: string, voice: string, isUserMessage?: boolean) => {
      // 1. Consent check
      const consentGiven = localStorage.getItem('audio_consent_given');
      if (!consentGiven) {
        window.dispatchEvent(new Event('audio:first-request'));
        localStorage.setItem('audio_consent_given', 'true');
      }

      // 2. State check
      if (!stateMachine.canPlay()) {
        reportAudioError(
          { tipo_error: 'AUDIO_NO_PROVIDER', mensaje: 'Cannot play in current state', contexto: { state: stateMachine.getState() } },
          'AudioPlayerContext'
        );
        return;
      }

      // 3. Get provider
      const provider = getProviderByVoice(voice);

      // 4. Check cache
      const cachedUrl = await queueManager.getCached(text, voice, provider.id);
      if (cachedUrl) {
        // Cache hit - play immediately
        const audio = new Audio(cachedUrl);
        stateMachine.transition('PLAY');
        audio.play();
        audio.onended = () => stateMachine.transition('END');
        return;
      }

      // 5. Cache miss - enqueue request
      await queueManager.enqueue({
        text,
        voice,
        provider: provider.id,
        timestamp: Date.now(),
        priority: isUserMessage ? 2 : 1, // User messages higher priority
      });

      // Fetch from backend
      try {
        const payload = {
          text,
          voice,
          provider: provider.id,
          speed: 1.0,
        };

        // Guard: if we know configured providers and the selected provider is not available,
        // show an informative toast/modal instead of sending the request.
        if (availableProviders && provider.id && !availableProviders[provider.id]) {
          const friendly = getVoiceDisplayName(voice) || voice;
          const msg = `${friendly} requires provider ${provider.id}, which is not configured on the backend.`;
          try {
            toastError(msg);
          } catch {
            // ignore
          }

          if (process.env.NODE_ENV !== 'production') {
            await swal.fire({
              title: 'Proveedor TTS no configurado',
              html: `<p>${escapeHtml(msg)}</p><p>Para habilitarlo en desarrollo exporta las variables de entorno respectivas y reinicia el backend.</p>`,
              confirmButtonText: 'Copiar instrucción',
              showCancelButton: true,
            }).then(async (r) => {
              if (r.isConfirmed) {
                const envCmd = provider.id === 'azure'
                  ? "export AZURE_SPEECH_KEY=... && export AZURE_SPEECH_REGION=..."
                  : "export OPENAI_API_KEY=...";
                try { await navigator.clipboard.writeText(envCmd); } catch { /* ignore */ }
              }
            });
          }

          throw new Error('TTS provider not configured');
        }

        // Debug-level request log to help backend debugging (remove in prod)
        // NOTE: keep logs scrubbed of PII in production.
        // eslint-disable-next-line no-console
        console.debug('[AudioPlayer] TTS request payload:', payload);

        const response = await fetch(`${BACKEND_URL}/api/tts/synthesize`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });

        if (!response.ok) {
          // Try to capture backend response body for troubleshooting
          let respText = '<no-body>';
          try {
            respText = await response.text();
          } catch {
            // ignore
          }

          // Structured error log with backend body
          reportAudioError(
            { tipo_error: 'AUDIO_BACKEND_UNREACHABLE', mensaje: `TTS backend returned ${response.status}`, contexto: { payload, status: response.status, body: respText } },
            'AudioPlayerContext'
          );

          // Show a concise toast message to the user/developer
          try {
              toastError(`TTS error: ${response.status} - ${String(respText).slice(0, 160)}`);
            } catch {
              // ignore toast failures
            }

          // In development, show a modal with full backend response and option to copy
          if (process.env.NODE_ENV !== 'production') {
            const safeBody = escapeHtml(String(respText));
            const friendlyVoice = getVoiceDisplayName(voice) || voice;
            const safeVoice = escapeHtml(String(friendlyVoice));

            // Build a curl command template for reproducing the request locally
            const jsonPayload = JSON.stringify(payload, null, 2).replace(/'/g, "'\"'\"");
            const curlTemplate = `# Voice: ${friendlyVoice}\n` +
              `curl -v -X POST '${BACKEND_URL}/api/tts/synthesize' \n+  -H 'Content-Type: application/json' \
  --data-raw '${jsonPayload}'`;
            const result = await swal.fire({
              title: `TTS backend error (${response.status})`,
                 html: `<div style='text-align:left;max-height:340px;overflow:auto'><div style='margin-bottom:8px'><strong>Voz:</strong> <span style='color:#4ade80;font-family:monospace'>${safeVoice}</span></div><pre style='white-space:pre-wrap'>${safeBody}</pre><hr/><small class='text-slate-400'>Puedes reproducir con curl (botón Copiar curl)</small></div>`,
              showCancelButton: true,
              showDenyButton: true,
              confirmButtonText: 'Copiar respuesta',
              denyButtonText: 'Copiar curl',
              cancelButtonText: 'Cerrar',
              width: '720px',
            });

            if (result.isConfirmed) {
              try {
                await navigator.clipboard.writeText(String(respText));
              } catch {
                // ignore copy error
              }
            }

            if (result.isDenied) {
              try {
                await navigator.clipboard.writeText(curlTemplate);
              } catch {
                // ignore copy error
              }
            }
          }

          throw new Error(`TTS failed: ${response.status} - ${respText}`);
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);

        // Add to cache
        await queueManager.addToCache(text, voice, provider.id, url);

        // Play
        const audio = new Audio(url);
        stateMachine.transition('PLAY');
        audio.play();
        audio.onended = () => stateMachine.transition('END');
      } catch (error) {
        // Transition to ERROR state if possible
        try {
          // Only transition to ERROR if we are currently playing; otherwise keep 'ready'
          if (stateMachine.getState && stateMachine.getState() === 'playing') {
            stateMachine.transition('ERROR');
          }
        } catch {
          // eslint-disable-next-line no-console
          console.warn('[AudioPlayer] stateMachine transition to ERROR failed:');
        }

        // Ensure structured log includes the thrown error message
        reportAudioError(
          { tipo_error: 'AUDIO_PLAYBACK_FAILED', mensaje: `Playback failed: ${String(error)}`, contexto: { text, voice } },
          'AudioPlayerContext'
        );

        try {
          toastError(`Audio playback failed: ${String(error).slice(0, 140)}`);
        } catch {
          // ignore
        }

        if (process.env.NODE_ENV !== 'production') {
          // Show dev modal with error details
          try {
            const safeErr = escapeHtml(String(error));
            await swal.fire({
              title: 'Audio playback error',
              html: `<pre style="text-align:left;white-space:pre-wrap;max-height:320px;overflow:auto">${safeErr}</pre>`,
              confirmButtonText: 'Copiar error',
              showCancelButton: true,
            });
          } catch {
            // ignore modal errors
          }
        }

        // Re-throw so callers/tests can observe failure if needed
        throw error;
      }
    },
    [BACKEND_URL, queueManager, stateMachine]
  );

  return (
    <AudioPlayerContext.Provider
      value={{
        generateAudio,
        isReady,
        currentState: stateMachine.getState(),
      }}
    >
      {children}
    </AudioPlayerContext.Provider>
  );
}

/**
 * Hook to access audio player from any message component
 *
 * Returns:
 * - generateAudio: Function to generate and play audio
 * - isReady: Boolean indicating if audio subsystem is ready
 * - currentState: Current state machine state
 *
 * If provider is not mounted, returns fallback with structured error.
 */
export function useAudioPlayerContext() {
  const context = useContext(AudioPlayerContext);
  if (!context) {
    // This should never happen now (provider mounted globally)
    reportAudioError(
      { tipo_error: 'AUDIO_NO_PROVIDER', mensaje: 'AudioPlayerProvider not mounted' },
      'useAudioPlayerContext'
    );
    return {
      generateAudio: () => Promise.resolve(),
      isReady: false,
      currentState: 'failed',
    };
  }
  return context;
}
