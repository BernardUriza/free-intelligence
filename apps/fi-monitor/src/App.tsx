import { useState, useEffect, useCallback } from 'react'
import { SourceConfig } from './components/SourceConfig'
import { StatusCard } from './components/StatusCard'
import { StatsCards } from './components/StatsCards'
import { RecentCalls } from './components/RecentCalls'
import { ModelChart } from './components/ModelChart'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:9200'

interface Status {
  ollama: { status: string; models: string[] }
  model: { name: string | null; size_gb: number; loaded: boolean }
  system: { platform: string; hostname: string; cpu_percent?: number; memory_percent?: number }
  ollama_url: string
}

interface Stats {
  period_hours: number
  total_calls: number
  success_calls: number
  error_calls: number
  total_tokens: number
  avg_latency_ms: number
  min_latency_ms: number
  max_latency_ms: number
  by_model: Array<{ model: string; count: number; tokens: number; avg_latency_ms: number }>
}

interface Call {
  id: string
  timestamp: string
  model: string
  total_tokens: number
  latency_ms: number
  status: string
  prompt_preview: string
  response_preview: string
}

export default function App() {
  const [status, setStatus] = useState<Status | null>(null)
  const [stats, setStats] = useState<Stats | null>(null)
  const [calls, setCalls] = useState<Call[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date())

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const [statusRes, statsRes, callsRes] = await Promise.all([
        fetch(`${API_URL}/status`),
        fetch(`${API_URL}/stats?hours=24`),
        fetch(`${API_URL}/calls?limit=100`),
      ])

      if (!statusRes.ok || !statsRes.ok || !callsRes.ok) {
        throw new Error('Failed to fetch data')
      }

      const [statusData, statsData, callsData] = await Promise.all([
        statusRes.json(),
        statsRes.json(),
        callsRes.json(),
      ])

      setStatus(statusData)
      setStats(statsData)
      setCalls(callsData.calls || [])
      setLastUpdate(new Date())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 5000) // Refresh every 5 seconds
    return () => clearInterval(interval)
  }, [fetchData])

  return (
    <div className="app">
      <header className="header">
        <h1>
          <span style={{ color: '#3b82f6' }}>●</span>
          FI Monitor
        </h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <span className="time">
            Last update: {lastUpdate.toLocaleTimeString()}
          </span>
          <span className="version">v0.1.0</span>
          <button
            className="refresh-btn"
            onClick={fetchData}
            disabled={loading}
          >
            {loading ? '...' : '↻'} Refresh
          </button>
        </div>
      </header>

      {error && (
        <div className="card" style={{ background: 'rgba(239, 68, 68, 0.1)', borderColor: '#ef4444', marginBottom: '1rem' }}>
          <p style={{ color: '#ef4444' }}>Error: {error}</p>
          <p style={{ color: '#94a3b8', fontSize: '0.875rem' }}>
            Make sure FI Edge Server is running on {API_URL}
          </p>
        </div>
      )}

      <section className="section">
        <h2 className="section-title">Configuration</h2>
        <SourceConfig />
      </section>

      {status && (
        <section className="section">
          <StatusCard status={status} />
        </section>
      )}

      {stats && (
        <section className="section">
          <h2 className="section-title">Statistics (Last 24h)</h2>
          <StatsCards stats={stats} />
        </section>
      )}

      {stats && stats.by_model.length > 0 && (
        <section className="section">
          <h2 className="section-title">Calls by Model</h2>
          <ModelChart data={stats.by_model} />
        </section>
      )}

      {calls.length > 0 && (
        <section className="section">
          <h2 className="section-title">Recent Calls</h2>
          <RecentCalls calls={calls} />
        </section>
      )}
    </div>
  )
}
