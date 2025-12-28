/**
 * Observability Utilities (Extracted from @aurity/fi-observability)
 * 
 * Telemetry and logging utilities for HIPAA-compliant monitoring.
 * Standalone version - no external dependencies required.
 * 
 * @module lib/internal/observability
 */

/**
 * Telemetry identifiers for distributed tracing
 */
export interface TelemetryIds {
  request_id?: string;
  workflow_id?: string;
  session_id?: string;
  idempotency_key?: string;
  chunk_number?: number;
}

/**
 * Sanitize message preview for logging (removes PHI/PII)
 * 
 * @param input - Input string to sanitize
 * @param max - Maximum length (default: 60)
 * @returns Truncated string safe for logging
 * 
 * @example
 * sanitizeMessagePreview("Patient has diabetes type 2 and hypertension", 20)
 * // Returns: "Patient has diabetes..."
 */
export function sanitizeMessagePreview(input: string, max = 60): string {
  const s = input ?? '';
  return s.length <= max ? s : s.slice(0, max);
}

/**
 * Generate 8-character hash for short identifiers
 * 
 * @param input - String to hash
 * @returns 8-character hexadecimal hash
 * 
 * @example
 * hash8("session_123_2024-01-01")
 * // Returns: "a4b3c2d1"
 */
export function hash8(input: string): string {
  let h = 0;
  for (let i = 0; i < input.length; i++) {
    h = (h * 31 + input.charCodeAt(i)) >>> 0;
  }
  return (h >>> 0).toString(16).slice(0, 8);
}
