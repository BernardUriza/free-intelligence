/**
 * ErrorClassifier - Environment-Aware Severity Mapping
 *
 * Maps error types to severity levels based on environment (dev vs prod).
 * Also determines actionability (whether to trigger overlay/alert).
 *
 * Key insight: In development, non-actionable errors are degraded to debug/info/warn
 * to avoid Turbopack overlay noise. In production, full severity is used.
 *
 * Actionable errors (require immediate action):
 * - NO_PROVIDER: Critical app state (provider missing)
 * - BACKEND_UNREACHABLE: Service degradation
 * - CAPABILITY_FAILED: Initialization failure
 * - INVALID_VOICE: Configuration bug
 *
 * Non-actionable errors (informational):
 * - PLAYBACK_FAILED: User can retry or try different voice
 * - RATE_LIMITED: Temporary quota issue
 * - CACHE_FULL: Performance hint, not user-blocking
 * - TIMEOUT: Transient issue, user can retry
 *
 * @module lib/audio/ErrorClassifier
 */

import { ERROR_CODES } from './ErrorPolicy';
import type {
  NormalizedAudioError,
  ClassifiedError,
  SeverityLevel,
} from './types/audio-errors.types';

/**
 * Severity mapping for development environment
 *
 * Intentionally degraded to avoid Turbopack overlay triggers.
 * Use console.warn/log/debug instead of console.error.
 */
const SEVERITY_MAP_DEV: Record<string, SeverityLevel> = {
  [ERROR_CODES.NO_PROVIDER]: 'warn', // Critical but expected during setup
  [ERROR_CODES.BACKEND_UNREACHABLE]: 'info', // Expected during backend restart
  [ERROR_CODES.CAPABILITY_FAILED]: 'warn',
  [ERROR_CODES.RATE_LIMITED]: 'info', // Informational - user knows about quota
  [ERROR_CODES.INVALID_VOICE]: 'warn',
  [ERROR_CODES.PLAYBACK_FAILED]: 'debug', // Very noisy in dev (autoplay policies)
  [ERROR_CODES.CACHE_FULL]: 'debug', // Perf hint, not user-blocking
  'AUDIO_UNKNOWN_ERROR': 'warn',
  'AUDIO_NETWORK_ERROR': 'info',
  'AUDIO_TIMEOUT': 'info',
  'AUDIO_PERMISSION_DENIED': 'warn',
  'AUDIO_UNSUPPORTED_FORMAT': 'warn',
};

/**
 * Severity mapping for production environment
 *
 * Full severity levels reflecting business impact.
 */
const SEVERITY_MAP_PROD: Record<string, SeverityLevel> = {
  [ERROR_CODES.NO_PROVIDER]: 'error', // Critical - provider should always be mounted
  [ERROR_CODES.BACKEND_UNREACHABLE]: 'error', // Service degradation
  [ERROR_CODES.CAPABILITY_FAILED]: 'error',
  [ERROR_CODES.RATE_LIMITED]: 'warn', // User-facing issue but recoverable
  [ERROR_CODES.INVALID_VOICE]: 'error', // Config bug
  [ERROR_CODES.PLAYBACK_FAILED]: 'warn', // User can retry or choose different voice
  [ERROR_CODES.CACHE_FULL]: 'info', // Performance hint
  'AUDIO_UNKNOWN_ERROR': 'error',
  'AUDIO_NETWORK_ERROR': 'error',
  'AUDIO_TIMEOUT': 'warn',
  'AUDIO_PERMISSION_DENIED': 'warn',
  'AUDIO_UNSUPPORTED_FORMAT': 'error',
};

/**
 * Actionable error codes that require immediate user attention
 *
 * These should trigger overlay/alert notifications.
 * User-blocking or app-blocking errors.
 */
const ACTIONABLE_CODES = [
  ERROR_CODES.NO_PROVIDER,
  ERROR_CODES.BACKEND_UNREACHABLE,
  ERROR_CODES.CAPABILITY_FAILED,
  ERROR_CODES.INVALID_VOICE,
  'AUDIO_PERMISSION_DENIED',
];

/**
 * Classify error with environment-aware severity and actionability
 */
export class ErrorClassifier {
  /**
   * Current environment (auto-detected from process.env.NODE_ENV)
   */
  private environment: 'development' | 'production';

  constructor() {
    this.environment =
      process.env.NODE_ENV === 'production' ? 'production' : 'development';
  }

  /**
   * Classify error with severity and actionability
   *
   * @param error - Normalized error to classify
   * @returns Classified error with severity and actionability flag
   */
  classify(error: NormalizedAudioError): ClassifiedError {
    const severityMap =
      this.environment === 'production' ? SEVERITY_MAP_PROD : SEVERITY_MAP_DEV;

    const severity =
      (severityMap[error.tipo_error] as SeverityLevel) || 'warn';
    const actionable = ACTIONABLE_CODES.includes(error.tipo_error);

    return {
      ...error,
      severity,
      environment: this.environment,
      actionable,
    };
  }

  /**
   * Determine if error should trigger Turbopack overlay
   *
   * In development: Only actionable errors trigger overlay
   * In production: Never trigger overlay (no Turbopack in prod)
   *
   * @returns true if should trigger overlay, false otherwise
   */
  shouldTriggerOverlay(error: ClassifiedError): boolean {
    // Never trigger overlay in production
    if (this.environment === 'production') {
      return false;
    }

    // In dev: only actionable errors trigger overlay
    // This prevents noise from informational/debug errors
    return error.actionable;
  }

  /**
   * Get console method for this severity level
   *
   * In development: Degrade error→warn to avoid overlay
   * In production: Use appropriate level for severity
   *
   * @returns console method: 'error' | 'warn' | 'log' | 'debug'
   */
  getConsoleMethod(
    severity: SeverityLevel
  ): 'error' | 'warn' | 'log' | 'debug' {
    switch (severity) {
      case 'critical':
      case 'error':
        // Degrade error to warn in dev to avoid overlay
        return this.environment === 'production' ? 'error' : 'warn';

      case 'warn':
        return 'warn';

      case 'info':
        return 'log';

      case 'debug':
        return 'debug';

      default:
        return 'log';
    }
  }

  /**
   * Get current environment
   */
  getEnvironment(): 'development' | 'production' {
    return this.environment;
  }

  /**
   * Get severity for a specific error code in current environment
   *
   * Useful for testing and diagnostics.
   *
   * @param tipo_error - Error code to look up
   * @returns Severity level
   */
  getSeverityForCode(tipo_error: string): SeverityLevel {
    const severityMap =
      this.environment === 'production' ? SEVERITY_MAP_PROD : SEVERITY_MAP_DEV;
    return (severityMap[tipo_error] as SeverityLevel) || 'warn';
  }

  /**
   * Check if error code is actionable
   *
   * @param tipo_error - Error code to check
   * @returns true if actionable, false otherwise
   */
  isActionable(tipo_error: string): boolean {
    return ACTIONABLE_CODES.includes(tipo_error);
  }
}
