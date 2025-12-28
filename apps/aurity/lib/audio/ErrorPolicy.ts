/**
 * ErrorPolicy - Structured error handling with PII redaction
 *
 * Transforms noisy console warnings into structured events with normalized error codes.
 * Redacts PII (emails, phone numbers) before logging to comply with HIPAA/privacy policies.
 *
 * Phase 1 (Legacy): createAudioError, logAudioError (maintained for backward compatibility)
 * Phase 2+ (New): reportAudioError via ErrorReporter subsystem with:
 * - Normalization of empty objects, Error instances, strings
 * - Environment-aware severity mapping (dev degraded, prod full)
 * - Deduplication (5s window)
 * - Sampling (10% in dev, 100% in prod)
 * - PII redaction
 * - Console in dev, backend POST in production
 *
 * Error codes:
 * - AUDIO_NO_PROVIDER: AudioPlayerProvider not mounted
 * - AUDIO_BACKEND_UNREACHABLE: TTS endpoint unavailable
 * - AUDIO_CAPABILITY_FAILED: Capability probe failed
 * - AUDIO_RATE_LIMITED: TTS quota exceeded
 * - AUDIO_PLAYBACK_FAILED: Audio playback error
 * - AUDIO_INVALID_VOICE: Unknown voice ID
 * - AUDIO_CACHE_FULL: Cache LRU eviction triggered
 *
 * @module ErrorPolicy
 * @see /apps/aurity/docs/audio/RUNBOOK.md
 */

export interface AudioError {
  code: string;
  message: string;
  context: Record<string, unknown>;
  timestamp: number;
  recoverable: boolean;
}

/**
 * Normalized error codes for audio subsystem
 */
export const ERROR_CODES = {
  NO_PROVIDER: 'AUDIO_NO_PROVIDER',
  BACKEND_UNREACHABLE: 'AUDIO_BACKEND_UNREACHABLE',
  CAPABILITY_FAILED: 'AUDIO_CAPABILITY_FAILED',
  RATE_LIMITED: 'AUDIO_RATE_LIMITED',
  INVALID_VOICE: 'AUDIO_INVALID_VOICE',
  PLAYBACK_FAILED: 'AUDIO_PLAYBACK_FAILED',
  CACHE_FULL: 'AUDIO_CACHE_FULL',
} as const;

/**
 * Redact PII from text before logging
 *
 * Redacts:
 * - Email addresses → [EMAIL]
 * - Phone numbers (10+ digits) → [PHONE]
 * - Truncates text > 100 characters
 *
 * @param text - Text that may contain PII
 * @returns Redacted text safe for logging
 */
export function redactPII(text: string): string {
  // Redact email-like patterns
  let redacted = text.replace(
    /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g,
    '[EMAIL]'
  );

  // Redact phone-like patterns (10+ digits)
  redacted = redacted.replace(/\b\d{10,}\b/g, '[PHONE]');

  // Truncate if too long
  if (redacted.length > 100) {
    redacted = redacted.substring(0, 97) + '...';
  }

  return redacted;
}

/**
 * Create structured error event
 *
 * Automatically redacts PII from context.text field.
 * Marks errors as recoverable or unrecoverable based on code.
 *
 * @param code - Error code key (e.g., 'NO_PROVIDER', 'PLAYBACK_FAILED')
 * @param message - Human-readable error description
 * @param context - Additional context (will be redacted if contains 'text' field)
 * @returns Structured AudioError event
 */
export function createAudioError(
  code: keyof typeof ERROR_CODES,
  message: string,
  context: Record<string, unknown> = {}
): AudioError {
  // Redact PII from context
  const sanitizedContext = { ...context };
  if (typeof sanitizedContext.text === 'string') {
    sanitizedContext.text = redactPII(sanitizedContext.text);
  }

  // Determine if error is recoverable
  const recoverableErrors = ['NO_PROVIDER', 'BACKEND_UNREACHABLE', 'RATE_LIMITED'];
  const recoverable = recoverableErrors.includes(code);

  return {
    code: ERROR_CODES[code],
    message,
    context: sanitizedContext,
    timestamp: Date.now(),
    recoverable,
  };
}

/**
 * Log error to console (dev) or backend (prod)
 *
 * Development: Logs full error object to console.error
 * Production: Sends error code and message only (TODO: implement backend endpoint)
 *
 * @param error - AudioError event to log
 */
export function logAudioError(error: AudioError): void {
  if (process.env.NODE_ENV === 'development') {
    console.error('[AudioPolicy]', error);
  } else {
    // In production, send to backend observability sink
    // TODO: Implement /api/observability/events endpoint (Phase 4)
    console.error('[AudioPolicy]', error.code, error.message);
  }
}

/**
 * Transform legacy "No provider found" warning
 *
 * Converts the old console.warn fallback into a structured error event.
 *
 * @returns AudioError event for missing provider
 */
export function transformNoProviderWarning(): AudioError {
  return createAudioError(
    'NO_PROVIDER',
    'AudioPlayerProvider not mounted in component tree',
    {
      hint: 'Mount <AudioPlayerProvider> in app/layout.tsx',
      recoverable: true,
    }
  );
}

// ============================================================================
// New ErrorReporter-based functions (Phase 2+)
// ============================================================================

import type { TelemetryIds } from './types/audio-errors.types';

// Lazy import to avoid circular dependency with ErrorReporter
let ErrorReporterClass: typeof import('./ErrorReporter').ErrorReporter | null = null;

/**
 * Global error reporter instance
 * Lazily initialized on first use
 */
let globalReporter: any = null;

/**
 * Initialize error reporter (call once from AudioPlayerContext)
 *
 * @param backendUrl - Optional backend URL (uses NEXT_PUBLIC_BACKEND_URL if not provided)
 */
export async function initErrorReporter(backendUrl?: string): Promise<void> {
  if (!globalReporter) {
    if (!ErrorReporterClass) {
      const { ErrorReporter } = await import('./ErrorReporter');
      ErrorReporterClass = ErrorReporter;
    }
    globalReporter = new ErrorReporterClass(backendUrl);
  }
}

/**
 * Report audio error (replaces logAudioError for new code)
 *
 * This is the main entry point for the new ErrorReporter subsystem.
 * Handles full pipeline: normalize → classify → dedupe → sample → redact → sink
 *
 * @param error - Raw error from any source
 * @param component - Component name that generated the error
 * @param telemetryIds - Optional telemetry identifiers (session_id, workflow_id, request_id)
 *
 * @example
 * await reportAudioError(error, 'AudioPlayerContext', { session_id: '...' });
 */
export async function reportAudioError(
  error: unknown,
  component: string,
  telemetryIds?: TelemetryIds
): Promise<void> {
  if (!globalReporter) {
    await initErrorReporter();
  }

  await globalReporter!.report(error, component, telemetryIds);
}

/**
 * Get error metrics (for debugging and dashboards)
 *
 * Returns current metrics:
 * - tasas_error: errors per minute by type
 * - severidades: count of errors by severity level
 * - colisiones_dedupe: number of suppressed duplicates
 * - tasa_muestreo_efectiva: actual sampling rate achieved
 *
 * @returns AudioErrorMetrics or null if reporter not initialized
 *
 * @example
 * const metrics = getErrorMetrics();
 * console.log('Dedupe collisions:', metrics?.colisiones_dedupe);
 */
export function getErrorMetrics() {
  return globalReporter?.getMetrics() || null;
}

/**
 * Get error reporter state (for debugging)
 *
 * Returns current state:
 * - eventos_enviados_total: total errors reported
 * - eventos_suprimidos_dedupe: errors suppressed by dedupe
 * - eventos_suprimidos_muestreo: errors suppressed by sampling
 * - ultimos_eventos: last 10 events (for review)
 * - errores_por_tipo: count by error type
 *
 * @returns ReporterState or null if reporter not initialized
 *
 * @example
 * const state = getErrorState();
 * console.log('Total events:', state?.eventos_enviados_total);
 */
export function getErrorState() {
  return globalReporter?.getState() || null;
}
