'use client';

/**
 * TimelineFilters Component
 *
 * Filter controls for the longitudinal memory:
 * - Event type tabs (All / Chat / Audio)
 * - Time range presets
 * - Custom date range picker
 *
 * Card: FI-PHIL-DOC-014
 * Created: 2025-11-22
 */

import React from 'react';
import { Button } from '@/components/ui/button';
import { Filter, MessageCircle, Mic, Clock, Calendar } from 'lucide-react';
import {
  EVENT_TYPES,
  MEMORY_TIME_RANGES,
  type EventTypeFilter,
  type TimelinePreset,
} from '@/config/timeline.config';

interface TimelineFiltersProps {
  // Current filter state
  eventType: EventTypeFilter;
  selectedPreset: TimelinePreset | null;

  // Counts for badges
  totalCount: number;
  chatCount: number;
  audioCount: number;

  // Callbacks
  onEventTypeChange: (type: EventTypeFilter) => void;
  onPresetChange: (preset: TimelinePreset) => void;
}

export function TimelineFilters({
  eventType,
  selectedPreset,
  totalCount,
  chatCount,
  audioCount,
  onEventTypeChange,
  onPresetChange,
}: TimelineFiltersProps) {
  return (
    <div className="space-y-4">
      {/* Event Type Tabs */}
      <div className="fi-flex-gap p-1 bg-slate-800/50 rounded-lg border border-slate-700 w-fit">
        <Button
          onClick={() => onEventTypeChange(EVENT_TYPES.ALL)}
          className={`fi-flex-gap px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            eventType === EVENT_TYPES.ALL
              ? 'bg-emerald-600 text-white'
              : 'text-slate-400 hover:text-white hover:bg-slate-700'
          }`}
          variant="ghost"
          size="sm"
          title="Ver Todo"
        >
          <Filter className="h-4 w-4" />
          Todo ({totalCount})
        </Button>

        <Button
          onClick={() => onEventTypeChange(EVENT_TYPES.CHAT)}
          className={`fi-flex-gap px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            eventType === EVENT_TYPES.CHAT
              ? 'bg-sky-600 text-white'
              : 'text-slate-400 hover:text-white hover:bg-slate-700'
          }`}
          variant="ghost"
          size="sm"
          title="Ver Chat"
        >
          <MessageCircle className="h-4 w-4" />
          Chat ({chatCount})
        </Button>

        <Button
          onClick={() => onEventTypeChange(EVENT_TYPES.AUDIO)}
          className={`fi-flex-gap px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            eventType === EVENT_TYPES.AUDIO
              ? 'bg-emerald-600 text-white'
              : 'text-slate-400 hover:text-white hover:bg-slate-700'
          }`}
          variant="ghost"
          size="sm"
          title="Ver Audio"
        >
          <Mic className="h-4 w-4" />
          Audio ({audioCount})
        </Button>
      </div>

      {/* Time Range Presets */}
      <div className="fi-flex-gap flex-wrap">
        <div className="flex items-center gap-1.5 text-sm text-slate-500">
          <Clock className="h-4 w-4" />
          <span>Período:</span>
        </div>

        {MEMORY_TIME_RANGES.PRESETS.map((preset) => (
          <Button
            key={preset.label}
            onClick={() => onPresetChange(preset)}
            className={`px-3 py-1.5 rounded-md fi-text-xs-medium transition-colors ${
              selectedPreset?.label === preset.label
                ? 'bg-slate-700 text-white border border-slate-600'
                : 'bg-slate-800/50 text-slate-400 hover:text-white hover:bg-slate-700 border border-transparent'
            }`}
            variant="ghost"
            size="sm"
            title={`Preset ${preset.label}`}
          >
            {preset.label}
          </Button>
        ))}

        {/* Custom Range Button (placeholder for date picker) */}
        <Button
          className="fi-btn-filter"
          title="Rango personalizado (próximamente)"
          variant="ghost"
          size="sm"
        >
          <Calendar className="h-3 w-3" />
          Personalizado
        </Button>
      </div>
    </div>
  );
}
