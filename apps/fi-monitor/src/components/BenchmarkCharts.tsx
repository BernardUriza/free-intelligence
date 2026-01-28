import { useState, useEffect } from 'react'
import { invoke } from '../lib/tauri-adapter'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar
} from 'recharts'

interface RagBenchmark {
  single_query_ms: number
  batch_10_ms: number
  batch_32_ms: number
  batch_100_ms: number
  throughput_qps: number
  gpu_memory_mb: number
  device: string
  gpu_name: string | null
  model: string
}

interface OllamaBenchmark {
  single_query_ms: number
  batch_5_avg_ms: number
  tokens_per_sec: number
  model: string
  eval_duration_ms: number
  eval_count: number
}

interface GatewayBenchmark {
  health_check_ms: number
  routing_overhead_ms: number
}

interface BenchmarkSuite {
  timestamp: string
  rag_service: RagBenchmark | null
  ollama: OllamaBenchmark | null
  gateway: GatewayBenchmark | null
  total_duration_ms: number
}

interface BenchmarkHistory {
  results: BenchmarkSuite[]
}

type TimeRange = '24h' | '7d' | '30d' | 'all'

export function BenchmarkCharts() {
  const [history, setHistory] = useState<BenchmarkHistory | null>(null)
  const [timeRange, setTimeRange] = useState<TimeRange>('7d')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadHistory()
  }, [])

  const loadHistory = async () => {
    setLoading(true)
    try {
      const result = await invoke<BenchmarkHistory>('get_benchmark_history')
      setHistory(result)
    } catch (error) {
      console.error('[BenchmarkCharts] Failed to load history:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="benchmark-charts loading">
        <div className="spinner" />
        <span>Loading historical data...</span>
      </div>
    )
  }

  if (!history || history.results.length === 0) {
    return (
      <div className="benchmark-charts empty">
        <p>📊 No historical data yet.</p>
        <p>Run benchmarks to start tracking performance over time.</p>
      </div>
    )
  }

  // Filter by time range
  const now = Date.now()
  const cutoffMs: Record<TimeRange, number> = {
    '24h': 24 * 60 * 60 * 1000,
    '7d': 7 * 24 * 60 * 60 * 1000,
    '30d': 30 * 24 * 60 * 60 * 1000,
    'all': Infinity
  }

  const filtered = history.results.filter(r => {
    const timestamp = new Date(r.timestamp).getTime()
    return now - timestamp < cutoffMs[timeRange]
  })

  // Prepare chart data
  const ollamaData = filtered
    .filter(r => r.ollama !== null)
    .map(r => ({
      date: new Date(r.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      latency: r.ollama!.single_query_ms,
      tokens_per_sec: r.ollama!.tokens_per_sec
    }))

  const ragData = filtered
    .filter(r => r.rag_service !== null)
    .map(r => ({
      date: new Date(r.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      throughput: r.rag_service!.throughput_qps,
      batch_10: r.rag_service!.batch_10_ms,
      batch_32: r.rag_service!.batch_32_ms
    }))

  const gatewayData = filtered
    .filter(r => r.gateway !== null)
    .map(r => ({
      date: new Date(r.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      health_check: r.gateway!.health_check_ms
    }))

  return (
    <div className="benchmark-charts">
      {/* Time Range Selector */}
      <div className="chart-controls">
        <span className="chart-controls-label">Time Range:</span>
        <button
          onClick={() => setTimeRange('24h')}
          className={timeRange === '24h' ? 'active' : ''}
        >
          24h
        </button>
        <button
          onClick={() => setTimeRange('7d')}
          className={timeRange === '7d' ? 'active' : ''}
        >
          7d
        </button>
        <button
          onClick={() => setTimeRange('30d')}
          className={timeRange === '30d' ? 'active' : ''}
        >
          30d
        </button>
        <button
          onClick={() => setTimeRange('all')}
          className={timeRange === 'all' ? 'active' : ''}
        >
          All
        </button>
        <span className="chart-data-points">{filtered.length} data points</span>
      </div>

      {/* Ollama Performance Charts */}
      {ollamaData.length > 0 && (
        <div className="chart-section">
          <h4>🦙 Ollama Performance</h4>
          <div className="chart-grid">
            {/* Latency Chart */}
            <div className="chart-container">
              <h5>Query Latency (ms)</h5>
              <ResponsiveContainer width="100%" height={180}>
                <LineChart data={ollamaData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                  <XAxis
                    dataKey="date"
                    stroke="#888"
                    style={{ fontSize: '10px' }}
                  />
                  <YAxis stroke="#888" style={{ fontSize: '10px' }} />
                  <Tooltip
                    contentStyle={{
                      background: 'var(--surface)',
                      border: '1px solid var(--border)',
                      borderRadius: '4px',
                      fontSize: '11px'
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: '11px' }} />
                  <Line
                    type="monotone"
                    dataKey="latency"
                    stroke="#4caf50"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    name="Latency (ms)"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* Throughput Chart */}
            <div className="chart-container">
              <h5>Tokens/second</h5>
              <ResponsiveContainer width="100%" height={180}>
                <LineChart data={ollamaData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                  <XAxis
                    dataKey="date"
                    stroke="#888"
                    style={{ fontSize: '10px' }}
                  />
                  <YAxis stroke="#888" style={{ fontSize: '10px' }} />
                  <Tooltip
                    contentStyle={{
                      background: 'var(--surface)',
                      border: '1px solid var(--border)',
                      borderRadius: '4px',
                      fontSize: '11px'
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: '11px' }} />
                  <Line
                    type="monotone"
                    dataKey="tokens_per_sec"
                    stroke="#2196f3"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    name="Tokens/s"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {/* RAG Service Performance Charts */}
      {ragData.length > 0 && (
        <div className="chart-section">
          <h4>🔍 RAG Service Performance</h4>
          <div className="chart-grid">
            {/* Throughput Chart */}
            <div className="chart-container">
              <h5>Throughput (queries/sec)</h5>
              <ResponsiveContainer width="100%" height={180}>
                <LineChart data={ragData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                  <XAxis
                    dataKey="date"
                    stroke="#888"
                    style={{ fontSize: '10px' }}
                  />
                  <YAxis stroke="#888" style={{ fontSize: '10px' }} />
                  <Tooltip
                    contentStyle={{
                      background: 'var(--surface)',
                      border: '1px solid var(--border)',
                      borderRadius: '4px',
                      fontSize: '11px'
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: '11px' }} />
                  <Line
                    type="monotone"
                    dataKey="throughput"
                    stroke="#00bcd4"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    name="QPS"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* Batch Performance Chart */}
            <div className="chart-container">
              <h5>Batch Performance (ms)</h5>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={ragData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                  <XAxis
                    dataKey="date"
                    stroke="#888"
                    style={{ fontSize: '10px' }}
                  />
                  <YAxis stroke="#888" style={{ fontSize: '10px' }} />
                  <Tooltip
                    contentStyle={{
                      background: 'var(--surface)',
                      border: '1px solid var(--border)',
                      borderRadius: '4px',
                      fontSize: '11px'
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: '11px' }} />
                  <Bar dataKey="batch_10" fill="#ff9800" name="Batch 10" />
                  <Bar dataKey="batch_32" fill="#ff5722" name="Batch 32" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {/* Gateway Performance Chart */}
      {gatewayData.length > 0 && (
        <div className="chart-section">
          <h4>🚪 Gateway Performance</h4>
          <div className="chart-container full-width">
            <h5>Health Check Latency (ms)</h5>
            <ResponsiveContainer width="100%" height={150}>
              <LineChart data={gatewayData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                <XAxis
                  dataKey="date"
                  stroke="#888"
                  style={{ fontSize: '10px' }}
                />
                <YAxis stroke="#888" style={{ fontSize: '10px' }} />
                <Tooltip
                  contentStyle={{
                    background: 'var(--surface)',
                    border: '1px solid var(--border)',
                    borderRadius: '4px',
                    fontSize: '11px'
                  }}
                />
                <Legend wrapperStyle={{ fontSize: '11px' }} />
                <Line
                  type="monotone"
                  dataKey="health_check"
                  stroke="#9c27b0"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  name="Health Check (ms)"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  )
}
