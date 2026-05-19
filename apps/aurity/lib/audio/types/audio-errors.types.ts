/**
 * Audio Error Types - Shared type definitions for the error subsystem
 *
 * Used by: ErrorNormalizer, ErrorClassifier, ErrorDeduplicator, ErrorReporter, ErrorPolicy
 *
 * @module lib/audio/types/audio-errors.types
 */

/** Telemetry identifiers for distributed tracing */
export interface TelemetryIds {
  request_id?: string;
  workflow_id?: string;
  session_id?: string;
  idempotency_key?: string;
  chunk_number?: number;
}

/** Severity levels for classified errors */
export type SeverityLevel = 'error' | 'warn' | 'info' | 'debug';

/** Canonical normalized error format (output of ErrorNormalizer) */
export interface NormalizedAudioError {
  tipo_error: string;
  mensaje: string;
  origen_componente: string;
  causa_probable: string;
  timestamp: number;
  contexto_sanitizado: Record<string, unknown>;
  recoverable: boolean;
  traza_normalizada?: string;
  session_id?: string;
  workflow_id?: string;
  request_id?: string;
}

/** Error with severity classification (output of ErrorClassifier) */
export interface ClassifiedError extends NormalizedAudioError {
  severity: SeverityLevel;
  environment: 'development' | 'production';
  actionable: boolean;
}

/** Deduplication cache entry */
export interface DedupeEntry {
  key: string;
  first_seen: number;
  last_seen: number;
  count: number;
}

/** Internal state of the ErrorReporter */
export interface ReporterState {
  eventos_enviados_total: number;
  eventos_suprimidos_dedupe: number;
  eventos_suprimidos_muestreo: number;
  ultimos_eventos: ClassifiedError[];
  errores_por_tipo: Record<string, number>;
}

/** Metrics exported by ErrorReporter */
export interface AudioErrorMetrics {
  tasas_error: Record<string, number>;
  severidades: Record<SeverityLevel, number>;
  colisiones_dedupe: number;
  tasa_muestreo_efectiva: number;
}
