/**
 * Timeline API Adapter Factory
 *
 * Feature flag: switches between real API and DemoAdapter.
 *
 * File: lib/api/timeline-adapter.ts
 * Card: FI-UI-FEAT-207
 * Created: 2025-10-30
 *
 * Philosophy AURITY:
 * - DemoMode conmuta sin cambiar UI
 * - Contrato espejo: mismas interfaces
 */

import {
  SessionSummary,
  SessionDetail,
  TimelineStats,
  getSessionSummaries as apiGetSessionSummaries,
  getSessionDetail as apiGetSessionDetail,
  getTimelineStats as apiGetTimelineStats,
} from './timeline';
import { DemoAdapter, parseDemoConfig } from '@/lib/demo';
import type { DemoConfig } from '@/lib/demo/types';

/**
 * Singleton demo adapter instance
 */
let demoAdapterInstance: DemoAdapter | null = null;

/**
 * Get or create demo adapter
 */
function getDemoAdapter(): DemoAdapter {
  if (!demoAdapterInstance) {
    demoAdapterInstance = new DemoAdapter();
  }
  return demoAdapterInstance;
}

/**
 * Check if demo mode is enabled
 */
export function isDemoMode(): boolean {
  const config = parseDemoConfig();
  return config.enabled;
}

/**
 * Get demo adapter (if demo mode enabled)
 */
export function getDemoAdapterIfEnabled(): DemoAdapter | null {
  return isDemoMode() ? getDemoAdapter() : null;
}

/**
 * Update demo configuration
 */
export function updateDemoConfig(config: Partial<DemoConfig>): void {
  const adapter = getDemoAdapter();
  adapter.updateConfig(config);
}

/**
 * Get session summaries (demo-aware)
 */
export async function getSessionSummariesAdapted(params?: {
  limit?: number;
  offset?: number;
  sort?: 'recent' | 'oldest' | 'events_desc' | 'events_asc';
}): Promise<SessionSummary[]> {
  if (isDemoMode()) {
    const adapter = getDemoAdapter();
    return adapter.getSessionSummaries(params);
  }
  return apiGetSessionSummaries(params);
}

/**
 * Get session detail (demo-aware)
 */
export async function getSessionDetailAdapted(
  sessionId: string
): Promise<SessionDetail> {
  if (isDemoMode()) {
    const adapter = getDemoAdapter();
    return adapter.getSessionDetail(sessionId);
  }
  return apiGetSessionDetail(sessionId);
}

/**
 * Get timeline stats (demo-aware)
 */
export async function getTimelineStatsAdapted(): Promise<TimelineStats> {
  if (isDemoMode()) {
    const adapter = getDemoAdapter();
    return adapter.getTimelineStats();
  }
  return apiGetTimelineStats();
}
