/**
 * ErrorNormalizer - Canonical Error Format Conversion
 *
 * Transforms raw errors from any source (empty objects {}, Error instances, strings,
 * partial objects) into NormalizedAudioError format with all required fields.
 *
 * Handles edge cases:
 * - Empty objects {} → generic error with probable cause
 * - Error instances → extract message, stack, cause
 * - Strings → treat as message, infer error code
 * - Partial objects → fill in missing fields
 * - Unknown types → fallback to generic error
 *
 * @module lib/audio/ErrorNormalizer
 */

import { ERROR_CODES } from './ErrorPolicy';
import type { NormalizedAudioError } from './types/audio-errors.types';

/**
 * Normalize raw errors into canonical NormalizedAudioError structure
 */
export class ErrorNormalizer {
  /**
   * Main normalization entry point
   *
   * @param rawError - Error from any source (Error, string, object, unknown)
   * @param origen_componente - Component that generated the error
   * @param fallbackCode - Optional error code to use if inference fails
   * @returns Canonical NormalizedAudioError
   */
  normalize(
    rawError: unknown,
    origen_componente: string,
    fallbackCode?: keyof typeof ERROR_CODES
  ): NormalizedAudioError {
    // Case 1: Empty object {}
    if (this.isEmptyObject(rawError)) {
      return this.createGenericError(origen_componente, fallbackCode);
    }

    // Case 2: Error instance
    if (rawError instanceof Error) {
      return this.normalizeErrorInstance(rawError, origen_componente);
    }

    // Case 3: String
    if (typeof rawError === 'string') {
      return this.normalizeString(rawError, origen_componente, fallbackCode);
    }

    // Case 4: Object with partial data
    if (typeof rawError === 'object' && rawError !== null) {
      return this.normalizeObject(
        rawError as Record<string, unknown>,
        origen_componente
      );
    }

    // Case 5: Unknown type (null, undefined, number, boolean, symbol)
    // Don't use String() as hint for primitives - use generic message instead
    return this.createGenericError(origen_componente, fallbackCode);
  }

  /**
   * Detect empty object {}
   *
   * Returns true only for plain objects with no properties.
   * Returns false for null, arrays, or objects with properties.
   */
  private isEmptyObject(obj: unknown): boolean {
    return (
      typeof obj === 'object' &&
      obj !== null &&
      Object.keys(obj).length === 0 &&
      obj.constructor === Object
    );
  }

  /**
   * Create generic error for unrecognized input
   *
   * Used when normalizing fails to infer specific error type.
   */
  private createGenericError(
    origen: string,
    code?: keyof typeof ERROR_CODES,
    hint?: string
  ): NormalizedAudioError {
    const tipo_error = code ? ERROR_CODES[code] : 'AUDIO_UNKNOWN_ERROR';

    return {
      tipo_error,
      mensaje: hint || 'An unknown audio error occurred',
      origen_componente: origen,
      causa_probable: 'Unknown - check component lifecycle or network',
      timestamp: Date.now(),
      contexto_sanitizado: {},
      recoverable: this.isRecoverable(tipo_error),
    };
  }

  /**
   * Normalize Error instance
   *
   * Extracts: message, name, cause (if available), stack trace
   */
  private normalizeErrorInstance(
    error: Error,
    origen: string
  ): NormalizedAudioError {
    const tipo_error = this.mapErrorNameToCode(error.name, error.message);

    return {
      tipo_error,
      mensaje: error.message || 'Error without message',
      origen_componente: origen,
      causa_probable: this.inferCause(error),
      timestamp: Date.now(),
      contexto_sanitizado: {
        error_name: error.name,
        // @ts-ignore - cause may not exist in all Error instances
        cause: error.cause ? String(error.cause) : undefined,
      },
      traza_normalizada: this.extractStackSummary(error.stack),
      recoverable: this.isRecoverable(tipo_error),
    };
  }

  /**
   * Normalize string message
   *
   * Infers error code from message content.
   */
  private normalizeString(
    message: string,
    origen: string,
    code?: keyof typeof ERROR_CODES
  ): NormalizedAudioError {
    const tipo_error = code
      ? ERROR_CODES[code]
      : this.inferCodeFromMessage(message);

    return {
      tipo_error,
      mensaje: message,
      origen_componente: origen,
      causa_probable: this.inferCauseFromMessage(message),
      timestamp: Date.now(),
      contexto_sanitizado: {},
      recoverable: this.isRecoverable(tipo_error),
    };
  }

  /**
   * Normalize partial object
   *
   * Expects object with some fields already present (tipo_error, message, etc.)
   * Fills in missing required fields with defaults.
   */
  private normalizeObject(
    obj: Record<string, unknown>,
    origen: string
  ): NormalizedAudioError {
    const tipo_error = String(
      obj.code || obj.tipo_error || 'AUDIO_UNKNOWN_ERROR'
    );

    return {
      tipo_error,
      mensaje: String(obj.message || obj.mensaje || 'No message provided'),
      origen_componente: String(obj.origen_componente || origen),
      causa_probable: String(obj.causa_probable || 'Unknown'),
      timestamp: Number(obj.timestamp) || Date.now(),
      contexto_sanitizado:
        (obj.contexto_sanitizado ||
          obj.context ||
          {}) as Record<string, unknown>,
      traza_normalizada: obj.traza_normalizada as string | undefined,
      recoverable: Boolean(obj.recoverable),
    };
  }

  /**
   * Map Error.name to canonical error code
   *
   * Uses both error name and message for better inference.
   */
  private mapErrorNameToCode(name: string, message: string): string {
    const lowerName = name.toLowerCase();
    const lowerMessage = message.toLowerCase();

    // Network errors
    if (
      lowerName.includes('network') ||
      lowerMessage.includes('fetch') ||
      lowerMessage.includes('network') ||
      lowerMessage.includes('unreachable') ||
      lowerMessage.includes('unavailable')
    ) {
      return ERROR_CODES.BACKEND_UNREACHABLE;
    }

    // Playback errors
    if (
      lowerName.includes('aborterror') ||
      lowerMessage.includes('autoplay') ||
      lowerMessage.includes('play()')
    ) {
      return ERROR_CODES.PLAYBACK_FAILED;
    }

    // Rate limiting
    if (
      lowerMessage.includes('quota') ||
      lowerMessage.includes('rate') ||
      lowerMessage.includes('429')
    ) {
      return ERROR_CODES.RATE_LIMITED;
    }

    // Timeout
    if (
      lowerName.includes('timeout') ||
      lowerMessage.includes('timeout')
    ) {
      return 'AUDIO_TIMEOUT';
    }

    // Default to unknown
    return 'AUDIO_UNKNOWN_ERROR';
  }

  /**
   * Infer error code from message content
   *
   * Pattern matching for common error messages.
   */
  private inferCodeFromMessage(message: string): string {
    const lower = message.toLowerCase();

    if (lower.includes('provider not') || lower.includes('provider missing')) {
      return ERROR_CODES.NO_PROVIDER;
    }

    if (
      lower.includes('backend') ||
      lower.includes('unreachable') ||
      lower.includes('unavailable')
    ) {
      return ERROR_CODES.BACKEND_UNREACHABLE;
    }

    if (lower.includes('capability') || lower.includes('capability probe')) {
      return ERROR_CODES.CAPABILITY_FAILED;
    }

    if (
      lower.includes('rate') ||
      lower.includes('quota') ||
      lower.includes('limit')
    ) {
      return ERROR_CODES.RATE_LIMITED;
    }

    if (lower.includes('voice') || lower.includes('voice id')) {
      return ERROR_CODES.INVALID_VOICE;
    }

    if (
      lower.includes('playback') ||
      lower.includes('play') ||
      lower.includes('audio')
    ) {
      return ERROR_CODES.PLAYBACK_FAILED;
    }

    if (lower.includes('cache') || lower.includes('memory')) {
      return ERROR_CODES.CACHE_FULL;
    }

    if (lower.includes('timeout')) {
      return 'AUDIO_TIMEOUT';
    }

    if (lower.includes('permission') || lower.includes('denied')) {
      return 'AUDIO_PERMISSION_DENIED';
    }

    if (lower.includes('format') || lower.includes('unsupported')) {
      return 'AUDIO_UNSUPPORTED_FORMAT';
    }

    return 'AUDIO_UNKNOWN_ERROR';
  }

  /**
   * Infer probable root cause from Error instance
   *
   * Uses error name and message to suggest likely cause for debugging.
   */
  private inferCause(error: Error): string {
    const msg = error.message.toLowerCase();
    const name = error.name.toLowerCase();

    if (name.includes('networkerror') || msg.includes('network')) {
      return 'Network connectivity issue or backend unreachable';
    }

    if (name.includes('aborterror') || msg.includes('abort')) {
      return 'Request aborted by user or timeout occurred';
    }

    if (name.includes('notallowederror') || msg.includes('autoplay')) {
      return 'User denied audio autoplay permission in browser';
    }

    if (name.includes('notsupportederror') || msg.includes('not support')) {
      return 'Audio format or operation not supported by browser';
    }

    if (msg.includes('cors')) {
      return 'CORS policy rejected request from frontend';
    }

    if (msg.includes('401') || msg.includes('unauthorized')) {
      return 'Authentication failed or token expired';
    }

    if (msg.includes('403') || msg.includes('forbidden')) {
      return 'User lacks permission for this operation';
    }

    if (msg.includes('404')) {
      return 'Backend endpoint or voice not found';
    }

    if (msg.includes('429') || msg.includes('rate')) {
      return 'Rate limit or quota exceeded for this voice/user';
    }

    if (msg.includes('500') || msg.includes('internal')) {
      return 'Backend server error - please check backend logs';
    }

    return 'Unknown - see error message for details';
  }

  /**
   * Infer probable root cause from string message
   *
   * Fallback when we don't have an Error instance.
   */
  private inferCauseFromMessage(message: string): string {
    const lower = message.toLowerCase();

    if (lower.includes('not mounted')) {
      return 'AudioPlayerProvider missing from component tree - check app/layout.tsx';
    }

    if (lower.includes('unreachable') || lower.includes('unavailable')) {
      return 'Backend TTS endpoint unavailable - check backend health';
    }

    if (lower.includes('timeout')) {
      return 'Request timeout - network slow or backend overloaded';
    }

    if (lower.includes('permission') || lower.includes('denied')) {
      return 'User denied microphone or audio permission';
    }

    if (lower.includes('format')) {
      return 'Audio format not supported by browser or backend';
    }

    if (lower.includes('voice')) {
      return 'Voice ID not recognized - check available voices list';
    }

    return 'Unknown - review error message and component logs';
  }

  /**
   * Extract stack trace summary
   *
   * Returns first 3 frames of stack trace, truncated to 150 chars.
   * Useful for deduplication without exposing full trace.
   */
  private extractStackSummary(stack?: string): string | undefined {
    if (!stack) {
      return undefined;
    }

    // Split into lines and take first 3 (excluding error message line)
    const lines = stack.split('\n').slice(0, 3);

    // Join and truncate to 150 chars
    const summary = lines.join(' | ').substring(0, 150);

    return summary || undefined;
  }

  /**
   * Determine if error allows user retry
   *
   * Recoverable errors: NO_PROVIDER, BACKEND_UNREACHABLE, RATE_LIMITED,
   * PLAYBACK_FAILED, TIMEOUT
   *
   * Non-recoverable: INVALID_VOICE, CAPABILITY_FAILED, CACHE_FULL
   */
  private isRecoverable(tipo_error: string): boolean {
    const recoverableCodes = [
      ERROR_CODES.NO_PROVIDER,
      ERROR_CODES.BACKEND_UNREACHABLE,
      ERROR_CODES.RATE_LIMITED,
      ERROR_CODES.PLAYBACK_FAILED,
      'AUDIO_TIMEOUT',
      'AUDIO_PERMISSION_DENIED',
    ];

    return recoverableCodes.includes(tipo_error);
  }
}
