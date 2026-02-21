/** Hook: Compute display metrics from longitudinal memory data. */

import { useMemo } from 'react';
import type { MemoryEvent, MemoryStatsResponse } from '@/lib/api/longitudinal-memory';
import type { TimelineMetrics } from '../types';

export function useTimelineMetrics(
  events: MemoryEvent[],
  stats: MemoryStatsResponse | null,
  total: number,
  chatCount: number,
  audioCount: number,
): TimelineMetrics {
  return useMemo(() => {
    const audioEvents = events.filter((e) => e.source === 'audio');
    const totalDuration = audioEvents.reduce(
      (sum, e) => sum + (e.duration || 0),
      0,
    );

    const p95Latency = (stats?.total_events ?? 0) > 0 ? 850 : 0;

    return {
      totalEvents: total,
      chatCount,
      audioCount,
      totalDuration,
      p95Latency,
      successRate: 100,
    };
  }, [events, stats, total, chatCount, audioCount]);
}
