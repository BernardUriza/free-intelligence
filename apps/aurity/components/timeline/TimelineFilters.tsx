'use client';

/**
 * TimelineFilters Component
 *
 * Filter controls for the longitudinal memory:
 * - Event type tabs (All / Chat / Audio)
 *
 * Note: Time range filtering is handled by the Bryntum scheduler navigation.
 *
 * Card: FI-PHIL-DOC-014
 * Created: 2025-11-22
 * Updated: 2025-01-14 - Removed period presets (use scheduler navigation instead)
 */

import React from 'react';
import { Button } from '@/components/ui/button';
import { Filter, MessageCircle, Mic } from 'lucide-react';
import {
  EVENT_TYPES,
  type EventTypeFilter,
} from '@/config/timeline.config';

interface TimelineFiltersProps {
  // Current filter state
  eventType: EventTypeFilter;

  // Counts for badges
  totalCount: number;
  chatCount: number;
  audioCount: number;

  // Callbacks
  onEventTypeChange: (type: EventTypeFilter) => void;
}

export function TimelineFilters({
  eventType,
  totalCount,
  chatCount,
  audioCount,
  onEventTypeChange,
}: TimelineFiltersProps) {
  return (
    <div className="fi-flex-gap p-1 bg-slate-800/50 rounded-lg border border-slate-700 w-fit">
      <Button
        onClick={() => onEventTypeChange(EVENT_TYPES.ALL)}
        className={eventType === EVENT_TYPES.ALL ? 'history-filter-btn-emerald' : 'history-filter-btn'}
        variant="ghost"
        size="sm"
        title="Ver Todo"
      >
        <Filter className="h-4 w-4" />
        Todo ({totalCount})
      </Button>

      <Button
        onClick={() => onEventTypeChange(EVENT_TYPES.CHAT)}
        className={eventType === EVENT_TYPES.CHAT ? 'history-filter-btn-sky' : 'history-filter-btn'}
        variant="ghost"
        size="sm"
        title="Ver Chat"
      >
        <MessageCircle className="h-4 w-4" />
        Chat ({chatCount})
      </Button>

      <Button
        onClick={() => onEventTypeChange(EVENT_TYPES.AUDIO)}
        className={eventType === EVENT_TYPES.AUDIO ? 'history-filter-btn-emerald' : 'history-filter-btn'}
        variant="ghost"
        size="sm"
        title="Ver Audio"
      >
        <Mic className="h-4 w-4" />
        Audio ({audioCount})
      </Button>
    </div>
  );
}
