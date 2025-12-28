/**
 * @aurity-standalone/observability
 * 
 * HIPAA-compliant observability utilities for healthcare applications.
 * Provides safe logging, telemetry, and monitoring without exposing PHI/PII.
 * 
 * @module @aurity-standalone/observability
 * @version 0.1.0
 * @license MIT
 */

/**
 * Telemetry identifiers for distributed tracing
 */
export interface TelemetryIds {
  /** Unique request identifier */
  request_id?: string;
  /** Workflow identifier */
  workflow_id?: string;
  /** Session identifier */
  session_id?: string;
  /** Idempotency key for duplicate detection */
  idempotency_key?: string;
}

/**
 * Sanitize message preview for logging (removes PHI/PII)
 * 
 * Truncates input to specified length to prevent logging sensitive data.
 * Use this for logging user messages, medical notes, or any text that may contain PHI.
 * 
 * @param input - Input string to sanitize
 * @param max - Maximum length (default: 60 characters)
 * @returns Truncated string safe for logging
 * 
 * @example
 * ```typescript
 * const userMessage = "Patient John Doe has diabetes type 2 and hypertension";
 * const safe = sanitizeMessagePreview(userMessage, 20);
 * console.log(safe); // "Patient John Doe has"
 * 
 * // Safe to log without PHI
 * logger.info('User message received', { preview: safe });
 * ```
 */
export function sanitizeMessagePreview(input: string, max = 60): string {
  const s = input ?? '';
  return s.length <= max ? s : s.slice(0, max);
}

/**
 * Generate 8-character hash for short identifiers
 * 
 * Creates a deterministic short hash from any string input.
 * Useful for creating collision-resistant short IDs for logging and telemetry.
 * 
 * @param input - String to hash
 * @returns 8-character hexadecimal hash
 * 
 * @example
 * ```typescript
 * const sessionId = "session_2025-01-18_patient_john_doe_123";
 * const shortId = hash8(sessionId);
 * console.log(shortId); // "a4b3c2d1"
 * 
 * // Safe to log without exposing full session ID
 * logger.info('Session started', { session_hash: shortId });
 * ```
 */
export function hash8(input: string): string {
  let h = 0;
  for (let i = 0; i < input.length; i++) {
    h = (h * 31 + input.charCodeAt(i)) >>> 0;
  }
  return (h >>> 0).toString(16).slice(0, 8);
}

/**
 * Create a safe telemetry context for logging
 * 
 * Extracts only non-sensitive identifiers for distributed tracing.
 * 
 * @param ids - Telemetry identifiers
 * @returns Safe telemetry context
 * 
 * @example
 * ```typescript
 * const context = createTelemetryContext({
 *   request_id: 'req_123',
 *   session_id: 'session_456',
 *   workflow_id: 'wf_789'
 * });
 * 
 * logger.info('Request processed', context);
 * ```
 */
export function createTelemetryContext(ids: TelemetryIds): Record<string, string> {
  const context: Record<string, string> = {};
  
  if (ids.request_id) context.request_id = ids.request_id;
  if (ids.workflow_id) context.workflow_id = ids.workflow_id;
  if (ids.session_id) context.session_id = ids.session_id;
  if (ids.idempotency_key) context.idempotency_key = ids.idempotency_key;
  
  return context;
}

/**
 * Measure execution time of async operations
 * 
 * @param label - Operation label for logging
 * @param fn - Async function to measure
 * @returns Result of the function and execution time in milliseconds
 * 
 * @example
 * ```typescript
 * const { result, duration } = await measureAsync('database-query', async () => {
 *   return await db.query('SELECT * FROM patients');
 * });
 * 
 * logger.info('Query completed', { duration_ms: duration });
 * ```
 */
export async function measureAsync<T>(
  label: string,
  fn: () => Promise<T>
): Promise<{ result: T; duration: number }> {
  const start = performance.now();
  const result = await fn();
  const duration = performance.now() - start;
  
  return { result, duration };
}

/**
 * Format file size for human-readable display
 * 
 * @param bytes - File size in bytes
 * @returns Formatted string (e.g., "1.5 MB")
 * 
 * @example
 * ```typescript
 * console.log(formatBytes(1536)); // "1.5 KB"
 * console.log(formatBytes(1048576)); // "1 MB"
 * ```
 */
export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}
