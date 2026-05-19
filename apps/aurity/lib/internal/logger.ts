/**
 * Structured Frontend Logger
 *
 * Lightweight logger that replaces raw console.log with structured,
 * environment-aware logging. Uses observability primitives for PII safety.
 *
 * Usage:
 *   const log = createLogger('WebSocket');
 *   log.info('Connected', { doctor_id: 'doc_123' });
 *   log.warn('Reconnecting', { attempt: 3 });
 *   log.error('Failed', error);
 *
 * In development: outputs to console with structured prefix
 * In production: suppresses debug/info, only warn/error output
 *
 * @module lib/internal/logger
 */

import { sanitizeMessagePreview } from './observability';

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface Logger {
  debug: (msg: string, ctx?: Record<string, unknown>) => void;
  info: (msg: string, ctx?: Record<string, unknown>) => void;
  warn: (msg: string, ctx?: Record<string, unknown>) => void;
  error: (msg: string, ctx?: Record<string, unknown>) => void;
}

const isDev = typeof process !== 'undefined' && process.env.NODE_ENV === 'development';

const LEVEL_PRIORITY: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
};

// In production, suppress debug and info to reduce noise
const MIN_LEVEL: LogLevel = isDev ? 'debug' : 'warn';

function shouldLog(level: LogLevel): boolean {
  return LEVEL_PRIORITY[level] >= LEVEL_PRIORITY[MIN_LEVEL];
}

function sanitizeContext(ctx: Record<string, unknown>): Record<string, unknown> {
  const safe: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(ctx)) {
    if (typeof value === 'string' && value.length > 60) {
      safe[key] = sanitizeMessagePreview(value);
    } else {
      safe[key] = value;
    }
  }
  return safe;
}

/**
 * Create a logger scoped to a component/module
 *
 * @param component - Component or module name (e.g., 'WebSocket', 'AudioPlayer')
 * @returns Logger with debug/info/warn/error methods
 */
export function createLogger(component: string): Logger {
  const prefix = `[${component}]`;

  const log = (level: LogLevel, msg: string, ctx?: Record<string, unknown>) => {
    if (!shouldLog(level)) return;

    const method = level === 'debug' ? 'log' : level;
    const safeCtx = ctx ? sanitizeContext(ctx) : undefined;

    if (safeCtx && Object.keys(safeCtx).length > 0) {
      console[method](prefix, msg, safeCtx);
    } else {
      console[method](prefix, msg);
    }
  };

  return {
    debug: (msg, ctx) => log('debug', msg, ctx),
    info: (msg, ctx) => log('info', msg, ctx),
    warn: (msg, ctx) => log('warn', msg, ctx),
    error: (msg, ctx) => log('error', msg, ctx),
  };
}
