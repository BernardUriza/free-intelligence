/**
 * Timestamp Utilities for Chat Messages
 *
 * Provides intelligent timestamp formatting with:
 * - Relative time ("hace 2min", "hace 1h", "ayer")
 * - Absolute time for tooltips
 * - Smart grouping detection
 * - Locale support (ES-MX)
 */

export interface TimestampOptions {
  /** Locale for formatting (default: 'es-MX') */
  locale?: string;

  /** Show relative time (default: true) */
  relative?: boolean;

  /** Threshold in minutes to switch from relative to absolute (default: 60) */
  relativeThreshold?: number;

  /** Include seconds in time display (default: false) */
  showSeconds?: boolean;
}

/**
 * Format timestamp for display
 * Returns relative time for recent messages, absolute for older ones
 */
export function formatMessageTime(
  timestamp: string | Date,
  options: TimestampOptions = {}
): string {
  const {
    locale = 'es-MX',
    relative = true,
    relativeThreshold = 60,
    showSeconds = false,
  } = options;

  const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  // Relative time for recent messages
  if (relative && diffMins < relativeThreshold) {
    if (diffMins < 1) return 'Ahora';
    if (diffMins === 1) return 'Hace 1min';
    if (diffMins < 60) return `Hace ${diffMins}min`;
    if (diffHours === 1) return 'Hace 1h';
    return `Hace ${diffHours}h`;
  }

  // Yesterday
  if (diffDays === 1) {
    return `Ayer ${date.toLocaleTimeString(locale, {
      hour: '2-digit',
      minute: '2-digit',
      ...(showSeconds && { second: '2-digit' }),
    })}`;
  }

  // This week (show day name)
  if (diffDays < 7) {
    return date.toLocaleDateString(locale, {
      weekday: 'short',
      hour: '2-digit',
      minute: '2-digit',
      ...(showSeconds && { second: '2-digit' }),
    });
  }

  // Older messages (show date)
  return date.toLocaleDateString(locale, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    ...(showSeconds && { second: '2-digit' }),
  });
}

/**
 * Format absolute timestamp for tooltips
 */
export function formatAbsoluteTime(
  timestamp: string | Date,
  locale: string = 'es-MX'
): string {
  const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;

  return date.toLocaleString(locale, {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

/**
 * Check if messages should be grouped (within 2 minutes of each other)
 */
export function shouldGroupMessages(
  timestamp1: string | Date,
  timestamp2: string | Date,
  thresholdMinutes: number = 2
): boolean {
  const date1 = typeof timestamp1 === 'string' ? new Date(timestamp1) : timestamp1;
  const date2 = typeof timestamp2 === 'string' ? new Date(timestamp2) : timestamp2;

  const diffMs = Math.abs(date2.getTime() - date1.getTime());
  const diffMins = diffMs / (1000 * 60);

  return diffMins <= thresholdMinutes;
}

/**
 * Get day divider text for message grouping
 */
export function getDayDividerText(
  timestamp: string | Date,
  locale: string = 'es-MX'
): string {
  const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
  const now = new Date();
  const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return 'Hoy';
  if (diffDays === 1) return 'Ayer';
  if (diffDays < 7) {
    return date.toLocaleDateString(locale, { weekday: 'long' });
  }

  return date.toLocaleDateString(locale, {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  });
}

/**
 * Format duration between two timestamps
 */
export function formatDuration(
  start: string | Date,
  end: string | Date
): string {
  const startDate = typeof start === 'string' ? new Date(start) : start;
  const endDate = typeof end === 'string' ? new Date(end) : end;

  const diffMs = endDate.getTime() - startDate.getTime();
  const diffSecs = Math.floor(diffMs / 1000);
  const diffMins = Math.floor(diffSecs / 60);
  const diffHours = Math.floor(diffMins / 60);

  if (diffSecs < 60) return `${diffSecs}s`;
  if (diffMins < 60) return `${diffMins}m ${diffSecs % 60}s`;
  return `${diffHours}h ${diffMins % 60}m`;
}
