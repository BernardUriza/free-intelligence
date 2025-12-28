/**
 * Polling configuration constants
 *
 * Centralizes timing constants for adaptive polling behavior.
 */

export const POLLING_CONFIG = {
  /** Initial fast polling interval (ms) - used when job is active */
  INITIAL_INTERVAL: 1000,

  /** Maximum backoff interval (ms) - used when job is idle */
  MAX_INTERVAL: 8000,

  /** Maximum polling attempts before timeout (3 min at worst case) */
  MAX_ATTEMPTS: 180,

  /** Request timeout for individual poll requests (ms) */
  REQUEST_TIMEOUT: 5000,

  /** Modal success display duration before auto-close (ms) */
  SUCCESS_DISPLAY_DURATION: 2000,

  /** Interval for hidden tab polling (ms) - slower to save resources */
  HIDDEN_TAB_INTERVAL: 2000,
} as const;

/**
 * Backoff multiplier for exponential backoff
 */
export const BACKOFF_MULTIPLIER = 1.5;
