/**
 * Longitudinal Memory Configuration
 *
 * Centralized configuration for longitudinal memory (memoria longitudinal).
 * NO HARDCODING - all limits, defaults, and settings are here.
 *
 * Card: FI-PHIL-DOC-014
 * Created: 2025-11-22
 */

// ============================================================================
// Pagination Configuration
// ============================================================================

export const MEMORY_PAGINATION = {
  /** Default items per page */
  DEFAULT_LIMIT: 50,

  /** Maximum items per page */
  MAX_LIMIT: 200,

  /** Minimum items per page */
  MIN_LIMIT: 10,

  /** Prefetch threshold (load more when X items from end) */
  PREFETCH_THRESHOLD: 10,

  /** Initial load size */
  INITIAL_LOAD: 30,
} as const;

// ============================================================================
// Time Range Configuration
// ============================================================================

export const MEMORY_TIME_RANGES = {
  /** Default time window in hours */
  DEFAULT_WINDOW_HOURS: 24 * 7, // 1 week

  /** Maximum time window in days */
  MAX_WINDOW_DAYS: 365, // 1 year

  /** Quick filter presets */
  PRESETS: [
    { label: 'Última hora', hours: 1 },
    { label: 'Últimas 24h', hours: 24 },
    { label: 'Última semana', hours: 24 * 7 },
    { label: 'Último mes', hours: 24 * 30 },
    { label: 'Últimos 3 meses', hours: 24 * 90 },
    { label: 'Todo', hours: null }, // No filter
  ] as const,
} as const;

// ============================================================================
// Event Types
// ============================================================================

export const EVENT_TYPES = {
  ALL: 'all',
  CHAT: 'chat',
  AUDIO: 'audio',
} as const;

export type EventTypeFilter = typeof EVENT_TYPES[keyof typeof EVENT_TYPES];

// ============================================================================
// UI Configuration
// ============================================================================

export const TIMELINE_UI = {
  /** Maximum height for timeline container */
  MAX_HEIGHT: 'max-h-[700px]',

  /** Animation duration for transitions (ms) */
  TRANSITION_MS: 200,

  /** Debounce time for search input (ms) */
  SEARCH_DEBOUNCE_MS: 300,

  /** Auto-refresh interval (ms, 0 = disabled) */
  AUTO_REFRESH_MS: 0,

  /** Show audio visualization chart */
  SHOW_AUDIO_VISUALIZATION: true,

  /** Maximum events to show in audio visualization */
  AUDIO_VIZ_MAX_EVENTS: 10,

  /** Content preview length (chars) */
  CONTENT_PREVIEW_LENGTH: 200,

  /** Session ID display length (chars) */
  SESSION_ID_DISPLAY_LENGTH: 16,
} as const;

// ============================================================================
// Color Scheme
// ============================================================================

export const TIMELINE_COLORS = {
  // Chat events
  chat_user: {
    bg: 'bg-sky-500/10',
    border: 'border-sky-500/30',
    text: 'text-sky-400',
    badge: 'bg-sky-500',
  },
  chat_assistant: {
    bg: 'bg-violet-500/10',
    border: 'border-violet-500/30',
    text: 'text-violet-400',
    badge: 'bg-violet-500',
  },

  // Audio events
  transcription: {
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-500/30',
    text: 'text-emerald-400',
    badge: 'bg-emerald-500',
  },

  // Default/fallback
  default: {
    bg: 'bg-slate-500/10',
    border: 'border-slate-500/30',
    text: 'text-slate-400',
    badge: 'bg-slate-500',
  },
} as const;

// ============================================================================
// Export Types
// ============================================================================

export type TimelinePreset = typeof MEMORY_TIME_RANGES.PRESETS[number];
export type TimelineColorScheme = typeof TIMELINE_COLORS;

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Get color scheme for an event type
 */
export function getEventColors(eventType: string): (typeof TIMELINE_COLORS)[keyof typeof TIMELINE_COLORS] {
  const type = eventType.toLowerCase();

  if (type === 'chat_user') return TIMELINE_COLORS.chat_user;
  if (type === 'chat_assistant') return TIMELINE_COLORS.chat_assistant;
  if (type === 'transcription') return TIMELINE_COLORS.transcription;

  return TIMELINE_COLORS.default;
}

/**
 * Calculate time range from preset
 */
export function getTimeRangeFromPreset(
  preset: TimelinePreset
): { start: string | null; end: string | null } {
  if (preset.hours === null) {
    return { start: null, end: null };
  }

  const now = new Date();
  const start = new Date(now.getTime() - preset.hours * 60 * 60 * 1000);

  return {
    start: start.toISOString(),
    end: now.toISOString(),
  };
}

/**
 * Format timestamp for display
 */
export function formatEventTimestamp(timestamp: number | string): string {
  const date = typeof timestamp === 'number'
    ? new Date(timestamp * 1000)
    : new Date(timestamp);

  return date.toLocaleTimeString('es-MX', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: true,
  });
}

/**
 * Format date for display
 */
export function formatEventDate(timestamp: number | string): string {
  const date = typeof timestamp === 'number'
    ? new Date(timestamp * 1000)
    : new Date(timestamp);

  return date.toLocaleDateString('es-MX', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}
