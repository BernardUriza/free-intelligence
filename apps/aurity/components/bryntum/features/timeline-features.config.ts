/**
 * Scheduler Features Configuration
 * 
 * Centralized configuration for all Bryntum SchedulerPro features.
 * Disables editing, enables tooltips, optimizes for read-only timeline view.
 */

import type { SchedulerFeatures } from '../types/scheduler.types';
import { EVENT_TOOLTIP_CONFIG } from './event-tooltip.feature';

/**
 * Timeline Scheduler Features
 * 
 * Read-only configuration:
 * - NO drag/drop
 * - NO resize
 * - NO editing
 * - YES tooltips (rich event preview)
 */
export const TIMELINE_FEATURES: SchedulerFeatures = {
  eventDrag: false,
  eventResize: false,
  eventEdit: false,
  eventTooltip: EVENT_TOOLTIP_CONFIG,
};
