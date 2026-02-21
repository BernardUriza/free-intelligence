/** Hook: Transform MemoryEvents into TimelineEvents with optional time-range filtering. */

import { useMemo } from 'react';
import type { MemoryEvent } from '@/lib/api/longitudinal-memory';
import type { TimelineEvent } from '@/components/audit/EventTimeline';
import type { SchedulerTimeRange } from '../types';

/**
 * Filters `events` by the scheduler's visible time range (when set)
 * and maps each `MemoryEvent` to the `TimelineEvent` shape consumed
 * by `<VirtualizedTimeline>` and `<EventTimeline>`.
 */
export function useTimelineEvents(
  events: MemoryEvent[],
  schedulerTimeRange: SchedulerTimeRange | null,
) {
  const filteredEvents = useMemo(() => {
    if (!schedulerTimeRange) return events;

    const start = schedulerTimeRange.startDate.getTime() / 1000;
    const end = schedulerTimeRange.endDate.getTime() / 1000;

    return events.filter((e) => e.timestamp >= start && e.timestamp <= end);
  }, [events, schedulerTimeRange]);

  const timelineEvents = useMemo<TimelineEvent[]>(
    () =>
      filteredEvents.map((e, idx) => ({
        id: e.id,
        timestamp: e.timestamp,
        type: (e as unknown as Record<string, unknown>).type as string ?? e.event_type,
        content: e.content,
        metadata: {
          event_number: idx + 1,
          session_id: e.session_id,
          persona: e.persona,
          chunk_number: e.chunk_number,
          duration: e.duration,
          confidence: e.confidence,
          language: e.language,
          stt_provider: e.stt_provider,
          source: e.source,
        },
      })),
    [filteredEvents],
  );

  return timelineEvents;
}
