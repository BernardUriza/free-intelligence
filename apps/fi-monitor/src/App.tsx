import { useState, useEffect, useCallback } from 'react'
import { invoke } from '@tauri-apps/api/core'
import { listen } from '@tauri-apps/api/event'
import { getVersion } from '@tauri-apps/api/app'

interface ServiceStatus {
  ollama_running: boolean
  ollama_models: string[]
  tunnel_running: boolean
  tunnel_url: string | null
  rag_service_running: boolean
  gateway_running: boolean
  system_info: { platform: string; hostname: string }
}

interface TestResult {
  category: string
  question: string
  answer: string
  elapsed_ms: number
  timestamp: string
}

interface SetupState {
  completed: boolean
  ollamaInstalled: boolean
  pythonInstalled: boolean
  lastCheck: string | null
  skipped: boolean
}

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

interface AppProps {
  setupState: SetupState
}

export default function App({ setupState }: AppProps) {
  const [status, setStatus] = useState<ServiceStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [testResult, setTestResult] = useState<TestResult | null>(null)
  const [autoTest, setAutoTest] = useState(false)
  const [nextTestIn, setNextTestIn] = useState(60)
  const [copiedUrl, setCopiedUrl] = useState(false)
  const [appVersion, setAppVersion] = useState('1.0.0')
  const [benchmarkResults, setBenchmarkResults] = useState<BenchmarkSuite | null>(null)
  const [isBenchmarking, setIsBenchmarking] = useState(false)

  // Tab state
  type TabId = 'services' | 'tunnel' | 'testing' | 'benchmarks'

  interface Tab {
    id: TabId
    label: string
    icon: string
  }

  const [activeTab, setActiveTab] = useState<TabId>('services')
  const [tunnelPort, setTunnelPort] = useState('11434')

  // Get app version from Tauri
  useEffect(() => {
    getVersion().then(v => setAppVersion(v)).catch(() => {})
  }, [])

  const fetchStatus = useCallback(async () => {
    try {
      setError(null)
      const result = await invoke<ServiceStatus>('get_status')
      setStatus(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, 5000)
    const unlistenServices = listen('services-checked', () => fetchStatus())
    const unlistenTunnel = listen('tunnel-started', () => fetchStatus())
    const unlistenTunnelUrl = listen<string>('tunnel-url-found', (event) => {
      setStatus(prev => prev ? { ...prev, tunnel_url: event.payload } : prev)
    })
    return () => {
      clearInterval(interval)
      unlistenServices.then(fn => fn())
      unlistenTunnel.then(fn => fn())
      unlistenTunnelUrl.then(fn => fn())
    }
  }, [fetchStatus])

  const handleAction = async (action: string, command: string) => {
    setActionLoading(action)
    try {
      await invoke(command)
      await fetchStatus()
    } catch (err) {
      setError(String(err))
    } finally {
      setActionLoading(null)
    }
  }

  const handleTestOllama = useCallback(async () => {
    if (!status?.ollama_running) return
    setActionLoading('test')
    setError(null)
    try {
      const result = await invoke<TestResult>('test_ollama')
      setTestResult(result)
    } catch (err) {
      setError(String(err))
    } finally {
      setActionLoading(null)
    }
  }, [status?.ollama_running])

  const runBenchmark = useCallback(async () => {
    setIsBenchmarking(true)
    setError(null)
    try {
      const result = await invoke<BenchmarkSuite>('benchmark_all')
      setBenchmarkResults(result)
      // Load history for future features (historical graph, comparison)
      const history = await invoke<BenchmarkHistory>('get_benchmark_history')
      console.log('[FI Monitor] Benchmark history loaded:', history.results.length, 'results')
    } catch (err) {
      setError(String(err))
    } finally {
      setIsBenchmarking(false)
    }
  }, [])

  // Benchmark event listener
  useEffect(() => {
    const unlistenBenchmark = listen<BenchmarkSuite>('benchmark-complete', (event) => {
      setBenchmarkResults(event.payload)
    })
    return () => {
      unlistenBenchmark.then(fn => fn())
    }
  }, [])

  useEffect(() => {
    if (!autoTest || !status?.ollama_running) {
      setNextTestIn(60)
      return
    }
    const countdown = setInterval(() => {
      setNextTestIn(prev => {
        if (prev <= 1) { handleTestOllama(); return 60 }
        return prev - 1
      })
    }, 1000)
    return () => clearInterval(countdown)
  }, [autoTest, status?.ollama_running, handleTestOllama])

  const handleCopyUrl = async () => {
    if (status?.tunnel_url) {
      try {
        await navigator.clipboard.writeText(status.tunnel_url)
        setCopiedUrl(true)
        setTimeout(() => setCopiedUrl(false), 2000)
      } catch {
        setCopiedUrl(false)
      }
    }
  }

  if (loading) {
    return <div className="app loading"><div className="spinner" /><span>Conectando...</span></div>
  }

  const ollamaOn = status?.ollama_running ?? false
  const tunnelOn = status?.tunnel_running ?? false

  // Tab configuration
  const tabs: Tab[] = [
    { id: 'services', label: 'Services', icon: '🔌' },
    { id: 'tunnel', label: 'Tunnel', icon: '☁️' },
    { id: 'testing', label: 'Testing', icon: '🧪' },
    { id: 'benchmarks', label: 'Benchmarks', icon: '⚡' },
  ]

  // Services section (Ollama only)
  const renderServicesTab = () => (
    <div className="services-grid">
      <div className={`service-card ${ollamaOn ? 'active' : ''}`}>
        <div className="service-icon">🦙</div>
        <div className="service-body">
          <div className="service-name">Ollama</div>
          <div className={`service-status ${ollamaOn ? 'on' : 'off'}`}>
            {ollamaOn ? '● Activo' : '○ Inactivo'}
          </div>
          {ollamaOn && status?.ollama_models && status.ollama_models.length > 0 && (
            <div className="models">{status.ollama_models.slice(0, 2).join(', ')}</div>
          )}
        </div>
        <button
          className={`action-btn ${ollamaOn ? 'stop' : 'start'}`}
          onClick={() => handleAction(ollamaOn ? 'ollama-stop' : 'ollama-start', ollamaOn ? 'stop_ollama' : 'start_ollama')}
          disabled={!!actionLoading}
        >
          {actionLoading?.includes('ollama') ? '...' : ollamaOn ? '■' : '▶'}
        </button>
      </div>
    </div>
  )

  // Tunnel section
  const renderTunnelTab = () => (
    <div className="flex flex-col gap-4 p-4">
      {/* Tunnel service card */}
      <div className={`service-card ${tunnelOn ? 'active' : ''} ${!ollamaOn ? 'disabled' : ''}`}>
        <div className="service-icon">☁️</div>
        <div className="service-body">
          <div className="service-name">Cloudflare Tunnel</div>
          <div className={`service-status ${tunnelOn ? 'on' : 'off'}`}>
            {tunnelOn ? '● Conectado' : '○ Desconectado'}
          </div>
          {tunnelOn && status?.tunnel_url && (
            <div className="tunnel-url-box" onClick={handleCopyUrl} title="Click para copiar">
              <span className="url-text">{status.tunnel_url.replace('https://', '')}</span>
              <span className="copy-icon">{copiedUrl ? '✓' : '📋'}</span>
            </div>
          )}
          {tunnelOn && !status?.tunnel_url && (
            <div className="tunnel-url-pending">⏳ Obteniendo URL...</div>
          )}
        </div>
        <button
          className={`action-btn ${tunnelOn ? 'stop' : 'start'}`}
          onClick={() => handleAction(tunnelOn ? 'tunnel-stop' : 'tunnel-start', tunnelOn ? 'stop_tunnel' : 'start_tunnel')}
          disabled={!!actionLoading || !ollamaOn}
        >
          {actionLoading?.includes('tunnel') ? '...' : tunnelOn ? '■' : '▶'}
        </button>
      </div>

      {/* Port configuration */}
      <div className="bg-app-surface rounded-lg border border-app-border p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="text-base">🔌</span>
            <span className="text-sm font-medium text-app-text">Puerto Local</span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <input
            type="text"
            value={tunnelPort}
            onChange={(e) => setTunnelPort(e.target.value)}
            className="flex-1 bg-app-bg border border-app-border rounded px-3 py-2 text-sm text-app-text focus:outline-none focus:border-app-accent"
            placeholder="11434"
            disabled={tunnelOn}
          />
          <span className="text-xs text-app-text-dim">
            {tunnelOn ? '(reinicia tunnel para aplicar)' : 'Puerto para Ollama'}
          </span>
        </div>
        <div className="mt-3 text-xs text-app-text-dim">
          💡 El tunnel expone este puerto localmente. Ollama usa 11434 por defecto.
        </div>
      </div>

      {/* Info section */}
      {!ollamaOn && (
        <div className="bg-app-surface rounded-lg border border-app-warning p-4 text-sm text-app-text-dim">
          ⚠️ Inicia Ollama primero para habilitar el tunnel
        </div>
      )}
    </div>
  )

  // Testing section
  const renderTestingTab = () => (
    <div className="test-section">
      <div className="test-header">
        <div className="test-title">
          <span className="icon">🧪</span>
          <span>Test LLM</span>
        </div>
        <div className="test-controls">
          <label className="auto-toggle" title="Auto-test cada 60s">
            <input type="checkbox" checked={autoTest} onChange={() => setAutoTest(!autoTest)} disabled={!ollamaOn} />
            <span className="timer">{autoTest ? `${nextTestIn}s` : 'Auto'}</span>
          </label>
          <button className="test-btn" onClick={handleTestOllama} disabled={actionLoading === 'test' || !ollamaOn}>
            {actionLoading === 'test' ? '⏳' : '▶'}
          </button>
        </div>
      </div>

      {testResult ? (
        <div className="test-result">
          <div className="result-header">
            <span className={`cat ${testResult.category}`}>{testResult.category === 'math' ? '🔢' : '🫀'}</span>
            <span className="time">{testResult.elapsed_ms}ms</span>
          </div>
          <div className="result-q">{testResult.question}</div>
          <div className="result-a">{testResult.answer}</div>
        </div>
      ) : (
        <div className="test-placeholder">{ollamaOn ? 'Presiona ▶ para probar' : 'Inicia Ollama primero'}</div>
      )}
    </div>
  )

  // Benchmarks section
  const renderBenchmarksTab = () => (
    <div className="benchmark-section">
      <div className="benchmark-header">
        <div className="benchmark-title">
          <span className="icon">⚡</span>
          <span>Performance Benchmark</span>
        </div>
        <button
          className="benchmark-btn"
          onClick={runBenchmark}
          disabled={isBenchmarking || !status?.rag_service_running}
        >
          {isBenchmarking ? '⏳ Running...' : '▶ Run Suite'}
        </button>
      </div>

      {isBenchmarking && (
        <div className="benchmark-progress">
          Running benchmark suite... This may take 30-60 seconds.
        </div>
      )}

      {benchmarkResults && !isBenchmarking && (
        <>
          <table className="results-table">
            <thead>
              <tr>
                <th>Service</th>
                <th>Metric</th>
                <th>Value</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {benchmarkResults.rag_service && (
                <>
                  <tr>
                    <td rowSpan={6}>RAG Service</td>
                    <td>Single Query</td>
                    <td>{benchmarkResults.rag_service.single_query_ms}ms</td>
                    <td>{benchmarkResults.rag_service.single_query_ms < 50 ? '✅' : '⚠️'}</td>
                  </tr>
                  <tr>
                    <td>Batch 10</td>
                    <td>{benchmarkResults.rag_service.batch_10_ms}ms</td>
                    <td>{benchmarkResults.rag_service.batch_10_ms < 500 ? '✅' : '⚠️'}</td>
                  </tr>
                  <tr>
                    <td>Batch 32</td>
                    <td>{benchmarkResults.rag_service.batch_32_ms}ms</td>
                    <td>{benchmarkResults.rag_service.batch_32_ms < 1000 ? '✅' : '⚠️'}</td>
                  </tr>
                  <tr>
                    <td>Batch 100</td>
                    <td>{benchmarkResults.rag_service.batch_100_ms}ms</td>
                    <td>-</td>
                  </tr>
                  <tr>
                    <td>Throughput</td>
                    <td>{benchmarkResults.rag_service.throughput_qps.toFixed(0)} qps</td>
                    <td>{benchmarkResults.rag_service.throughput_qps > 200 ? '✅' : '⚠️'}</td>
                  </tr>
                  <tr>
                    <td>Device</td>
                    <td>{benchmarkResults.rag_service.device} ({benchmarkResults.rag_service.gpu_name || 'Unknown'})</td>
                    <td>{(benchmarkResults.rag_service.device === 'cuda' || benchmarkResults.rag_service.device === 'mps') ? '✅' : '❌'}</td>
                  </tr>
                </>
              )}
              {benchmarkResults.ollama && (
                <>
                  <tr>
                    <td rowSpan={2}>Ollama</td>
                    <td>Single Query</td>
                    <td>{benchmarkResults.ollama.single_query_ms}ms</td>
                    <td>-</td>
                  </tr>
                  <tr>
                    <td>Tokens/sec</td>
                    <td>{benchmarkResults.ollama.tokens_per_sec.toFixed(1)} t/s</td>
                    <td>{benchmarkResults.ollama.tokens_per_sec > 50 ? '✅' : '⚠️'}</td>
                  </tr>
                </>
              )}
              {benchmarkResults.gateway && (
                <tr>
                  <td>Gateway</td>
                  <td>Health Check</td>
                  <td>{benchmarkResults.gateway.health_check_ms}ms</td>
                  <td>{benchmarkResults.gateway.health_check_ms < 10 ? '✅' : '⚠️'}</td>
                </tr>
              )}
            </tbody>
          </table>

          <div className="benchmark-meta">
            <span>Total: {benchmarkResults.total_duration_ms}ms</span>
            <span>•</span>
            <span>{new Date(benchmarkResults.timestamp).toLocaleString()}</span>
          </div>
        </>
      )}

      {!benchmarkResults && !isBenchmarking && (
        <div className="benchmark-placeholder">
          {status?.rag_service_running ? 'Click "Run Suite" to start benchmarking' : 'Start RAG Service first'}
        </div>
      )}
    </div>
  )

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="icon">⚡</span>
          <span className="title">FI Monitor</span>
        </div>
        <div className="system-info">
          <span className="host">{status?.system_info.hostname}</span>
        </div>
      </header>

      {error && <div className="toast error" onClick={() => setError(null)}>⚠️ {error}</div>}

      {setupState.skipped && (!setupState.ollamaInstalled || !setupState.pythonInstalled) && (
        <div className="toast warning" style={{ cursor: 'default' }}>
          {!setupState.pythonInstalled && !setupState.ollamaInstalled && '🐍🦙 Python 3.14 y Ollama no detectados'}
          {!setupState.pythonInstalled && setupState.ollamaInstalled && '🐍 Python 3.14 no detectado'}
          {setupState.pythonInstalled && !setupState.ollamaInstalled && '🦙 Ollama no detectado'}
          . Instala manualmente para funcionalidad completa
        </div>
      )}

      {/* Tab Navigation */}
      <div className="border-b border-app-border">
        <ul className="flex -mb-px">
          {tabs.map(tab => (
            <li key={tab.id} className="mr-2">
              <button
                onClick={() => setActiveTab(tab.id)}
                className={`
                  inline-flex items-center gap-2 px-4 py-3
                  border-b-2 transition-all duration-200
                  text-sm font-medium
                  ${activeTab === tab.id
                    ? 'border-app-accent text-app-accent'
                    : 'border-transparent text-app-text-dim hover:text-app-text hover:border-app-border-bright'
                  }
                `}
                aria-current={activeTab === tab.id ? 'page' : undefined}
              >
                <span className="text-base">{tab.icon}</span>
                <span>{tab.label}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>

      {/* Tab Content */}
      <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
        {activeTab === 'services' && renderServicesTab()}
        {activeTab === 'tunnel' && renderTunnelTab()}
        {activeTab === 'testing' && renderTestingTab()}
        {activeTab === 'benchmarks' && renderBenchmarksTab()}
      </div>

      <footer className="statusbar">
        <span className={`dot ${ollamaOn && tunnelOn ? 'green' : ollamaOn || tunnelOn ? 'yellow' : 'gray'}`} />
        <span className="status-text">{ollamaOn && tunnelOn ? 'Listo' : ollamaOn ? 'Tunnel pendiente' : 'Detenido'}</span>
        <span className="version">v{appVersion}</span>
      </footer>
    </div>
  )
}
