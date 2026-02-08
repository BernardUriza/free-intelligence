/**
 * ErrorReporter - Central Orchestrator for Error Handling
 *
 * Flow:
 * 1. Normalize (raw error → canonical format)
 * 2. Classify (add severity & actionability)
 * 3. Deduplicate (suppress within 5s window)
 * 4. Sample (drop by rate in dev)
 * 5. Redact (mask PII)
 * 6. Sink (console in dev, backend POST in prod)
 *
 * @module lib/audio/ErrorReporter
 */

import { ErrorNormalizer } from './ErrorNormalizer';
import { ErrorClassifier } from './ErrorClassifier';
import { ErrorDeduplicator } from './ErrorDeduplicator';
import { ErrorSampler } from './ErrorSampler';
import { redactPII } from './ErrorPolicy';
import { ROUTES } from '@/lib/api/routes';
import type {
  ClassifiedError,
  ReporterState,
  AudioErrorMetrics,
  TelemetryIds,
} from './types/audio-errors.types';

/**
 * Unified error reporter - orchestrates all subsystems
 */
export class ErrorReporter {
  /**
   * Normalizer module
   */
  private normalizer = new ErrorNormalizer();

  /**
   * Classifier module
   */
  private classifier = new ErrorClassifier();

  /**
   * Deduplicator module
   */
  private deduplicator = new ErrorDeduplicator();

  /**
   * Sampler module
   */
  private sampler: ErrorSampler;

  /**
   * Internal state tracking
   */
  private state: ReporterState;

  /**
   * Current environment
   */
  private environment: 'development' | 'production';

  /**
   * Backend URL for observability sink
   */
  private backendUrl: string;

  /**
   * Create error reporter
   *
   * @param backendUrl - Backend URL for observability endpoint
   */
  constructor(backendUrl?: string) {
    this.environment =
      process.env.NODE_ENV === 'production' ? 'production' : 'development';
    this.sampler = new ErrorSampler(this.environment);
    this.backendUrl =
      backendUrl || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:7001';

    this.state = {
      eventos_enviados_total: 0,
      eventos_suprimidos_dedupe: 0,
      eventos_suprimidos_muestreo: 0,
      ultimos_eventos: [],
      errores_por_tipo: {},
    };
  }

  /**
   * Report error (main entry point)
   *
   * Processes error through entire pipeline:
   * normalize → classify → dedupe → sample → redact → sink
   *
   * @param rawError - Raw error from any source
   * @param origen_componente - Component name that generated error
   * @param telemetryIds - Optional telemetry identifiers
   */
  async report(
    rawError: unknown,
    origen_componente: string,
    telemetryIds?: TelemetryIds
  ): Promise<void> {
    // Step 1: Normalize
    const normalized = this.normalizer.normalize(rawError, origen_componente);

    // Attach telemetry IDs
    if (telemetryIds) {
      if (telemetryIds.session_id) normalized.session_id = telemetryIds.session_id;
      if (telemetryIds.workflow_id) normalized.workflow_id = telemetryIds.workflow_id;
      if (telemetryIds.request_id) normalized.request_id = telemetryIds.request_id;
    }

    // Step 2: Classify
    const classified = this.classifier.classify(normalized);

    // Step 3: Deduplicate
    if (this.deduplicator.shouldSuppress(classified)) {
      this.state.eventos_suprimidos_dedupe += 1;
      return; // Suppress duplicate
    }

    // Step 4: Sample
    if (!this.sampler.shouldSample()) {
      this.state.eventos_suprimidos_muestreo += 1;
      return; // Drop due to sampling
    }

    // Step 5: Redact PII
    const redacted = this.redactError(classified);

    // Step 6: Route to sink (console or backend)
    await this.sink(redacted);

    // Update state
    this.updateState(redacted);
  }

  /**
   * Redact PII from error before logging/sending
   *
   * @private
   */
  private redactError(error: ClassifiedError): ClassifiedError {
    const redacted = { ...error };

    // Redact mensaje
    redacted.mensaje = redactPII(error.mensaje);

    // Redact contexto fields
    const context = { ...error.contexto_sanitizado };
    if (typeof context.text === 'string') {
      context.text = redactPII(context.text);
    }
    if (typeof context.message === 'string') {
      context.message = redactPII(context.message);
    }
    redacted.contexto_sanitizado = context;

    return redacted;
  }

  /**
   * Route error to appropriate sink
   *
   * Development: console (warn/log/debug based on severity)
   * Production: backend POST endpoint + timeline event
   *
   * @private
   */
  private async sink(error: ClassifiedError): Promise<void> {
    if (this.environment === 'development') {
      this.sinkDevelopment(error);
    } else {
      await this.sinkProduction(error);
    }

    // Always emit timeline event (development and production)
    await this.sinkTimeline(error);
  }

  /**
   * Development sink - console with degraded severity
   *
   * @private
   */
  private sinkDevelopment(error: ClassifiedError): void {
    const consoleMethod = this.classifier.getConsoleMethod(error.severity);
    const prefix = `[AudioError:${error.severity}]`;

    console[consoleMethod](prefix, {
      tipo: error.tipo_error,
      mensaje: error.mensaje,
      origen: error.origen_componente,
      causa: error.causa_probable,
      recoverable: error.recoverable,
      contexto: error.contexto_sanitizado,
    });
  }

  /**
   * Production sink - send to backend observability endpoint
   *
   * @private
   */
  private async sinkProduction(error: ClassifiedError): Promise<void> {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);

      const response = await fetch(
        `${this.backendUrl}/api/observability/audio/events`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            event_type: 'audio.error',
            severity: error.severity,
            error_code: error.tipo_error,
            message: error.mensaje,
            component: error.origen_componente,
            cause: error.causa_probable,
            recoverable: error.recoverable,
            context: error.contexto_sanitizado,
            timestamp: error.timestamp,
            session_id: error.session_id,
            workflow_id: error.workflow_id,
            request_id: error.request_id,
          }),
          signal: controller.signal,
        }
      );

      clearTimeout(timeoutId);

      if (!response.ok) {
        // Fallback to console if backend returns error
        console.warn(`[AudioError] Backend returned ${response.status}`);
      }
    } catch {
      // Silent failure - don't create error loops
      // Errors in reporting should not trigger more errors
      console.warn('[AudioError] Failed to send to backend');
    }
  }

  /**
   * Timeline sink - emit error as timeline event
   *
   * Formats the classified error as a TimelineEvent and sends to timeline endpoint
   * or emits as browser event for frontend handling.
   *
   * @private
   */
  private async sinkTimeline(error: ClassifiedError): Promise<void> {
    try {
      // Format error as timeline event
      const timelineEvent = {
        id: `audio-error-${error.timestamp}-${Math.random().toString(36).substr(2, 9)}`,
        type: 'audio_error',
        content: error.mensaje,
        metadata: {
          error_code: error.tipo_error,
          severity: error.severity,
          component: error.origen_componente,
          cause: error.causa_probable,
          recoverable: error.recoverable,
          timestamp: error.timestamp,
          session_id: error.session_id,
          workflow_id: error.workflow_id,
          context: error.contexto_sanitizado,
        },
        timestamp: error.timestamp,
      };

      // In browser environment, emit custom event for timeline listener
      if (typeof window !== 'undefined') {
        const event = new CustomEvent('audioErrorEvent', {
          detail: timelineEvent,
        });
        window.dispatchEvent(event);
      }

      // Optionally send to timeline endpoint (if available)
      // This allows backend to store timeline events separately
      if (this.backendUrl && this.environment === 'production') {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 3000);

        try {
          await fetch(`${this.backendUrl}${ROUTES.timeline}/audio-error`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(timelineEvent),
            signal: controller.signal,
          });
        } finally {
          clearTimeout(timeoutId);
        }
      }
    } catch {
      // Silent failure - timeline events are informational
      // Don't let timeline sinking errors trigger error loops
    }
  }

  /**
   * Update internal state
   *
   * @private
   */
  private updateState(error: ClassifiedError): void {
    this.state.eventos_enviados_total += 1;
    this.state.errores_por_tipo[error.tipo_error] =
      (this.state.errores_por_tipo[error.tipo_error] || 0) + 1;

    // Keep last 10 events
    this.state.ultimos_eventos.push(error);
    if (this.state.ultimos_eventos.length > 10) {
      this.state.ultimos_eventos.shift();
    }
  }

  /**
   * Get reporter state (for debugging)
   *
   * @returns Current ReporterState
   */
  getState(): ReporterState {
    return { ...this.state };
  }

  /**
   * Export metrics for observability
   *
   * @returns AudioErrorMetrics with rates, severities, stats
   */
  getMetrics(): AudioErrorMetrics {
    const dedupeStats = this.deduplicator.getStats();
    const samplerStats = this.sampler.getStats();

    // Calculate error rates (errors/min)
    const tasas_error: Record<string, number> = {};
    for (const [tipo, count] of Object.entries(this.state.errores_por_tipo)) {
      tasas_error[tipo] = count / 60; // Approximate rate
    }

    // Count by severity
    const severidades: Record<string, number> = {
      debug: 0,
      info: 0,
      warn: 0,
      error: 0,
      critical: 0,
    };
    for (const evento of this.state.ultimos_eventos) {
      severidades[evento.severity] = (severidades[evento.severity] || 0) + 1;
    }

    return {
      tasas_error,
      severidades,
      colisiones_dedupe: dedupeStats.total_suppressed,
      tasa_muestreo_efectiva: samplerStats.effective_rate,
    };
  }

  /**
   * Clear all state (for testing)
   *
   * @internal
   */
  clear(): void {
    this.deduplicator.clear();
    this.sampler.reset?.();
    this.state = {
      eventos_enviados_total: 0,
      eventos_suprimidos_dedupe: 0,
      eventos_suprimidos_muestreo: 0,
      ultimos_eventos: [],
      errores_por_tipo: {},
    };
  }
}
