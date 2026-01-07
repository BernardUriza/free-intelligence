/**
 * Bryntum Module Exports
 * 
 * Centralized export index for clean imports across the application.
 * 
 * Usage:
 * ```ts
 * import { useSchedulerState, VIEW_PRESETS, buildSchedulerConfig } from '@/components/bryntum';
 * ```
 */

// Types
export type * from './types/scheduler.types';

// Config
export { VIEW_PRESETS, getViewModes, formatDateForView, navigateDate } from './config/timeline-presets.config';
export { TIMELINE_RESOURCES } from './config/timeline-resources.config';
export { TIMELINE_COLUMNS } from './config/timeline-columns.config';

// Features
export { TIMELINE_FEATURES } from './features/timeline-features.config';
export { EVENT_TOOLTIP_CONFIG } from './features/event-tooltip.feature';

// Hooks
export { useSchedulerState } from './hooks/useSchedulerState';
export { useSchedulerLifecycle } from './hooks/useSchedulerLifecycle';
export { useSchedulerEvents } from './hooks/useSchedulerEvents';
export { useBryntumScheduler } from './hooks/useBryntumScheduler';
export { useVirtualizedTimeRanges } from './hooks/useVirtualizedTimeRanges';

// Utils
export {
  transformEvent,
  transformEvents,
  getEventColor,
  getEventTypeLabel,
  getResourceForEvent,
} from './utils/event-transform.utils';
export { buildSchedulerConfig } from './utils/scheduler-builder.utils';
export {
  buildTimelineSchedulerConfig,
  buildAppointmentSchedulerConfig,
  type TimelineSchedulerParams,
  type AppointmentSchedulerParams,
} from './utils/config-builders';
export { loadBryntumOnce, isLoaded, getBryntumModule } from './utils/bryntum-loader';
export {
  generateBlockedTimeEvents,
  isBlockedTimeEvent,
  type BlockedTimeEvent,
} from './utils/blocked-time-events';
export {
  initBryntumPatchHook,
  updateDoctorsCache,
  cleanupBryntumPatchHook,
} from './utils/bryntum-patch-hook';

// Core Component
export { SchedulerCore } from './core/SchedulerCore';
