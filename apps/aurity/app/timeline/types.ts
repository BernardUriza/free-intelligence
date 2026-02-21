/** Shared types for the Timeline page. */

export type ViewType = 'scheduler' | 'list' | 'both';

export interface TimelineMetrics {
  totalEvents: number;
  chatCount: number;
  audioCount: number;
  totalDuration: number;
  p95Latency: number;
  successRate: number;
}

export interface SchedulerTimeRange {
  startDate: Date;
  endDate: Date;
}
