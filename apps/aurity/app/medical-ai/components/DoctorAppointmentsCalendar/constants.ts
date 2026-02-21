/**
 * DoctorAppointmentsCalendar - Constants
 *
 * Single Responsibility: visual tokens shared across the calendar module.
 */

import type { StatusColor } from './types';

// ============================================================================
// Non-business hours visual
// ============================================================================

export const NON_BUSINESS_PATTERN = {
  gradient: `repeating-linear-gradient(
    -45deg,
    rgba(100, 116, 139, 0.08),
    rgba(100, 116, 139, 0.08) 4px,
    rgba(100, 116, 139, 0.15) 4px,
    rgba(100, 116, 139, 0.15) 8px
  )`,
  border: 'rgba(100, 116, 139, 0.3)',
} as const;

// ============================================================================
// Appointment status palette
// ============================================================================

export const STATUS_COLORS: Record<string, StatusColor> = {
  scheduled: {
    bg: 'rgba(59, 130, 246, 0.3)',
    border: 'rgba(59, 130, 246, 0.6)',
    text: '#93c5fd',
  },
  confirmed: {
    bg: 'rgba(16, 185, 129, 0.3)',
    border: 'rgba(16, 185, 129, 0.6)',
    text: '#6ee7b7',
  },
  checked_in: {
    bg: 'rgba(245, 158, 11, 0.3)',
    border: 'rgba(245, 158, 11, 0.6)',
    text: '#fcd34d',
  },
  in_progress: {
    bg: 'rgba(139, 92, 246, 0.3)',
    border: 'rgba(139, 92, 246, 0.6)',
    text: '#c4b5fd',
  },
  completed: {
    bg: 'rgba(100, 116, 139, 0.2)',
    border: 'rgba(100, 116, 139, 0.4)',
    text: '#94a3b8',
  },
  cancelled: {
    bg: 'rgba(239, 68, 68, 0.2)',
    border: 'rgba(239, 68, 68, 0.4)',
    text: '#fca5a5',
  },
  no_show: {
    bg: 'rgba(239, 68, 68, 0.2)',
    border: 'rgba(239, 68, 68, 0.4)',
    text: '#fca5a5',
  },
} as const;
