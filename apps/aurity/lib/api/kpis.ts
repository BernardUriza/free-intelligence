/**
 * KPIs API Client
 *
 * Fetches system metrics from backend KPIs API
 * Card: FI-UI-FEAT-200
 */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:7001"

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
  const response = await fetch(`${API_BASE}/api/workflows/aurity/kpis?window=${window}&view=summary`, {
    cache: "no-store", // Always fetch fresh data for dashboard
  })

  if (!response.ok) {
    throw new Error(`KPIs API failed: ${response.status} - ${response.url}`)
  }

  return response.json()
}

/**
 * Fetch KPI chips (UI-ready format)
 */
export async function getKPIChips(window: string = "5m"): Promise<KPIChipsResponse> {
  const response = await fetch(`${API_BASE}/api/workflows/aurity/kpis?window=${window}&view=chips`, {
    cache: "no-store",
  })

  if (!response.ok) {
    throw new Error(`KPIs API failed: ${response.status} - ${response.url}`)
  }

  return response.json()
}
