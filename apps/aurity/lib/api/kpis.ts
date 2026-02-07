/**
 * KPIs API Client
 *
 * Fetches system metrics from backend KPIs API
 * Card: FI-UI-FEAT-200
 */

import { api } from './client';

export interface KPIMetrics {
  window: string
  asOf: string
  requests: {
    total: number
    "2xx": number
    "4xx": number
    "5xx": number
  }
  latency: {
    p50_ms: number
    p95_ms: number
    max_ms: number
  }
  tokens: {
    in: number
    out: number
    unknown: number
  }
  cache: {
    hit: number
    miss: number
    hit_ratio: number
  }
  providers: Array<{
    id: string
    count: number
    pct: number
  }>
}

export interface KPIChip {
  id: string
  label: string
  value: string | number
  unit: string
  trend?: "up" | "down" | "stable"
}

export interface KPIChipsResponse {
  window: string
  asOf: string
  chips: KPIChip[]
}

/**
 * Fetch KPI metrics (summary view)
 */
export async function getKPIMetrics(window: string = "5m"): Promise<KPIMetrics> {
  return api.get<KPIMetrics>(`/api/aurity/kpis?window=${window}&view=summary`);
}

/**
 * Fetch KPI chips (UI-ready format)
 */
export async function getKPIChips(window: string = "5m"): Promise<KPIChipsResponse> {
  return api.get<KPIChipsResponse>(`/api/aurity/kpis?window=${window}&view=chips`);
}
