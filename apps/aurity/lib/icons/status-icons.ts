/**
 * Status Icons
 *
 * Lucide icons for status indicators, replacing emojis like ✅❌⚠️
 * Used across console logs, UI feedback, and status displays.
 */

import {
  CheckCircle,
  Check,
  AlertTriangle,
  XCircle,
  Circle,
  AlertCircle,
  Construction,
  Timer,
  RefreshCw,
  Rocket,
  Loader2,
  Info,
  HelpCircle,
  Ban,
  ThumbsUp,
  ThumbsDown,
  Pause,
  Play,
  Square,
  CircleDot,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

/**
 * Status icons mapping
 * Maps status keys to Lucide icon components
 */
export const STATUS_ICONS: Record<string, LucideIcon> = {
  // Success states
  success: CheckCircle,
  check: Check,
  done: CheckCircle,
  complete: CheckCircle,
  verified: CheckCircle,
  approved: ThumbsUp,

  // Warning states
  warning: AlertTriangle,
  caution: AlertTriangle,
  attention: AlertTriangle,

  // Error states
  error: XCircle,
  failed: XCircle,
  rejected: ThumbsDown,
  blocked: Ban,
  critical: AlertCircle,

  // Progress states
  loading: Loader2,
  pending: Timer,
  waiting: Timer,
  processing: RefreshCw,
  refresh: RefreshCw,
  wip: Construction,
  paused: Pause,
  playing: Play,
  stopped: Square,

  // Info states
  info: Info,
  help: HelpCircle,
  tip: Info,

  // Launch/action states
  launch: Rocket,
  start: Play,
  active: CircleDot,

  // Circle status indicators (use with color classes)
  status_ok: Circle,
  status_warning: Circle,
  status_error: Circle,
  status_neutral: Circle,
} as const;

/**
 * Color classes for status circles
 * Use these with Circle icon for colored status indicators
 */
export const STATUS_COLORS: Record<string, string> = {
  status_ok: 'text-green-500',
  status_warning: 'text-yellow-500',
  status_error: 'text-red-500',
  status_neutral: 'text-gray-400',
  success: 'text-green-500',
  warning: 'text-yellow-500',
  error: 'text-red-500',
  info: 'text-blue-500',
  critical: 'text-red-600',
} as const;

/**
 * Get icon for a status type
 * @param status - The status key (e.g., 'success', 'error', 'warning')
 * @returns The corresponding Lucide icon component
 */
export function getStatusIcon(status: string): LucideIcon {
  const normalizedStatus = status.toLowerCase().replace(/[\s-]/g, '_');
  return STATUS_ICONS[normalizedStatus] || Circle;
}

/**
 * Get color class for a status type
 * @param status - The status key
 * @returns Tailwind color class string
 */
export function getStatusColor(status: string): string {
  const normalizedStatus = status.toLowerCase().replace(/[\s-]/g, '_');
  return STATUS_COLORS[normalizedStatus] || 'text-gray-500';
}

/**
 * Check if a status key exists
 */
export function hasStatusIcon(status: string): boolean {
  const normalizedStatus = status.toLowerCase().replace(/[\s-]/g, '_');
  return normalizedStatus in STATUS_ICONS;
}

/**
 * Console log prefixes (text-based, for non-UI logging)
 * Use these instead of emojis in console.log statements
 */
export const LOG_PREFIXES = {
  success: '[OK]',
  error: '[ERROR]',
  warning: '[WARN]',
  info: '[INFO]',
  debug: '[DEBUG]',
  start: '[START]',
  end: '[END]',
  skip: '[SKIP]',
} as const;
