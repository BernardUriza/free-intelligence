/**
 * Scheduler Columns Configuration
 * 
 * Defines the resource info column (left side of scheduler).
 * Shows resource name and icon.
 */

import type { ColumnConfig } from '../types/scheduler.types';

/**
 * Timeline Columns
 * 
 * Single resource info column showing "Chat" and "Audio" rows.
 */
export const TIMELINE_COLUMNS: ColumnConfig[] = [
  {
    type: 'resourceInfo',
    text: 'Fuente',
    width: 120,
    showImage: false,
  },
];
