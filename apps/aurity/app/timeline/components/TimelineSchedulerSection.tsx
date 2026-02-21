/** Bryntum SchedulerPro wrapper with collapsible header. */

'use client';

import React from 'react';
import dynamic from 'next/dynamic';
import { Button } from '@/components/ui/button';
import { BarChart3, ChevronDown, ChevronUp, Loader2 } from 'lucide-react';
import type { MemoryEvent } from '@/lib/api/longitudinal-memory';
import type { ViewType } from '../types';

const TimelineScheduler = dynamic(
  () => import('@/components/timeline/TimelineScheduler'),
  {
    ssr: false,
    loading: () => (
      <div className="tl-loading-wrapper">
        <Loader2 className="tl-loading-spinner-sm" />
      </div>
    ),
  },
);

interface TimelineSchedulerSectionProps {
  events: MemoryEvent[];
  isLoading: boolean;
  viewType: ViewType;
  expanded: boolean;
  onToggleExpanded: () => void;
  onTimeRangeChange: (startDate: Date, endDate: Date) => void;
}

export function TimelineSchedulerSection({
  events,
  isLoading,
  viewType,
  expanded,
  onToggleExpanded,
  onTimeRangeChange,
}: TimelineSchedulerSectionProps) {
  const showToggle = viewType === 'both';

  return (
    <div className="tl-scheduler-container">
      {showToggle && (
        <Button
          onClick={onToggleExpanded}
          className="tl-scheduler-toggle fi-border-bottom"
          variant="ghost"
          size="sm"
          title={expanded ? 'Contraer Scheduler' : 'Expandir Scheduler'}
        >
          <div className="tl-scheduler-label">
            <BarChart3 className="tl-scheduler-icon" />
            <span className="fi-title-sm-medium">
              Visualización Timeline
            </span>
            <span className="fi-text-xs">(Bryntum SchedulerPro)</span>
          </div>
          {expanded ? (
            <ChevronUp className="tl-chevron-icon" />
          ) : (
            <ChevronDown className="tl-chevron-icon" />
          )}
        </Button>
      )}

      {(viewType === 'scheduler' || expanded) && (
        <TimelineScheduler
          events={events}
          isLoading={isLoading}
          onTimeRangeChange={onTimeRangeChange}
          className="tl-scheduler-view"
        />
      )}
    </div>
  );
}
