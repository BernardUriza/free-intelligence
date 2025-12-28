/**
 * Bryntum Scheduler Builder
 * 
 * Factory function to create BryntumSchedulerConfig from app state.
 * Centralizes all configuration logic in one pure function.
 */

import type {
  BryntumSchedulerConfig,
  ViewMode,
  UnifiedEvent,
  SchedulerCallbacks,
} from '../types/scheduler.types';
import { VIEW_PRESETS } from '../config/timeline-presets.config';
import { TIMELINE_RESOURCES } from '../config/timeline-resources.config';
import { TIMELINE_COLUMNS } from '../config/timeline-columns.config';
import { TIMELINE_FEATURES } from '../features/timeline-features.config';
import { transformEvents } from '../utils/event-transform.utils';

interface BuildSchedulerConfigParams {
  viewMode: ViewMode;
  currentDate: Date;
  events: UnifiedEvent[];
  callbacks?: SchedulerCallbacks;
}

/**
 * Build complete Bryntum SchedulerPro configuration
 * 
 * Pure function that generates configuration object based on current state.
 * No side effects, fully testable.
 */
export function buildSchedulerConfig({
  viewMode,
  currentDate,
  events,
  callbacks,
}: BuildSchedulerConfigParams): BryntumSchedulerConfig {
  const viewConfig = VIEW_PRESETS[viewMode];
  const { start, end } = viewConfig.getDateRange(currentDate);

  return {
    // Time axis
    startDate: start,
    endDate: end,
    viewPreset: viewConfig.preset,

    // Layout
    rowHeight: 60, // Increased from 50 to make rows more visible
    barMargin: 4,
    
    // Grid configuration - ensure resources column is visible
    subGridConfigs: {
      locked: {
        width: 200, // Fixed width for resource column
        flex: 0,
      },
      normal: {
        flex: 1, // Flexible timeline area
      },
    },

    // Data
    resources: TIMELINE_RESOURCES,
    events: transformEvents(events),
    columns: TIMELINE_COLUMNS,

    // Features
    features: TIMELINE_FEATURES,

    // Event listeners
    listeners: {
      eventClick: callbacks?.onEventClick
        ? (event) => {
            const originalEvent = event.eventRecord.data.originalEvent as UnifiedEvent;
            if (originalEvent && callbacks.onEventClick) {
              callbacks.onEventClick(originalEvent);
            }
          }
        : undefined,
    },
  };
}
