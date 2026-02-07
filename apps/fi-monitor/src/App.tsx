import { useState, useEffect, useCallback } from 'react'
import { ModelManager } from './components/ModelManager'
import { BenchmarkCharts } from './components/BenchmarkCharts'
import { EnvVarEditor } from './components/EnvVarEditor'
import { TestSuiteLibrary } from './components/TestSuiteLibrary'
import { invoke, listen, getVersion, isTauriContext } from './lib/tauri-adapter'

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
  rag_metadata?: any | null
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

interface RagStats {
  gpu_memory_used_mb: number
  gpu_memory_total_mb: number
  gpu_device: string
  model_name: string
  embeddings_count: number
  avg_query_ms: number
  throughput_qps: number
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
  const [showModelManager, setShowModelManager] = useState(false)
  const [ragStats, setRagStats] = useState<RagStats | null>(null)

  // Tab state
  type TabId = 'services' | 'tunnel' | 'config' | 'testing' | 'benchmarks'

  interface Tab {
    id: TabId
    label: string
    icon: string
  }

  const [activeTab, setActiveTab] = useState<TabId>('services')
  const [tunnelPort, setTunnelPort] = useState('11400')  // Default Gateway
  const [tunnelPortError, setTunnelPortError] = useState<string | null>(null)
  const [savedTunnelPort, setSavedTunnelPort] = useState('11400')
  const [tunnelFileContent, setTunnelFileContent] = useState<string>('')

  // Get app version from Tauri
  useEffect(() => {
    if (!isTauriContext()) {
      setAppVersion('1.0.6-browser')
      return
    }
    getVersion().then(v => setAppVersion(v)).catch(() => {})
  }, [])

  // Load tunnel port on mount
  useEffect(() => {
    if (!isTauriContext()) {
      console.warn('[App] Skipping tunnel port load (not in Tauri context)')
      return
    }
    invoke<number>('get_tunnel_port')
      .then(port => {
        setTunnelPort(String(port))
        setSavedTunnelPort(String(port))
      })
      .catch(err => console.error('[FI Monitor] Failed to load tunnel port:', err))
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
    if (!isTauriContext()) {
      console.warn('[App] Browser mode: detecting services via HTTP')
      setLoading(false)

      // Detect services directly via HTTP in browser mode
      const detectServices = async () => {
        let ollamaRunning = false
        let ollamaModels: string[] = []
        let ragRunning = false

        // Check Ollama (http://localhost:11434/api/tags)
        try {
          const ollamaRes = await fetch('http://localhost:11434/api/tags', {
            signal: AbortSignal.timeout(2000)
          })
          if (ollamaRes.ok) {
            const data = await ollamaRes.json()
            ollamaRunning = true
            ollamaModels = data.models?.map((m: any) => m.name) || []
            console.log('[App] Ollama detected:', ollamaModels.length, 'models')
          }
        } catch (err) {
          console.warn('[App] Ollama not detected:', err)
        }

        // Check RAG Service (http://localhost:11435/rag/health)
        try {
          const ragRes = await fetch('http://localhost:11435/rag/health', {
            signal: AbortSignal.timeout(2000)
          })
          ragRunning = ragRes.ok
          console.log('[App] RAG Service detected:', ragRunning)
        } catch (err) {
          console.warn('[App] RAG Service not detected:', err)
        }

        setStatus({
          ollama_running: ollamaRunning,
          ollama_models: ollamaModels,
          tunnel_running: false,
          tunnel_url: null,
          rag_service_running: ragRunning,
          gateway_running: false,
          system_info: { platform: 'browser', hostname: 'localhost' }
        })
      }

      detectServices()
      const interval = setInterval(detectServices, 5000) // Poll every 5s
      return () => clearInterval(interval)
    }

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

  // Redirect to services if Tunnel tab disappears (Local mode)
  useEffect(() => {
    const isCloudflared = status?.tunnel_url?.startsWith('https://') ?? false
    if (activeTab === 'tunnel' && !isCloudflared) {
      setActiveTab('services')
    }
  }, [activeTab, status?.tunnel_url])

  // Fetch RAG stats every 5 seconds (when active)
  useEffect(() => {
    if (!isTauriContext()) {
      console.warn('[App] Skipping RAG stats polling (not in Tauri context)')
      return
    }

    if (!status?.rag_service_running) {
      setRagStats(null)
      return
    }

    const fetchRagStats = async () => {
      try {
        const stats = await invoke<RagStats>('get_rag_stats')
        setRagStats(stats)
      } catch (err) {
        console.error('[FI Monitor] Failed to fetch RAG stats:', err)
        setRagStats(null)
      }
    }

    fetchRagStats()
    const interval = setInterval(fetchRagStats, 5000)
    return () => clearInterval(interval)
  }, [status?.rag_service_running])

  const handleAction = async (action: string, command: string) => {
    if (!isTauriContext()) {
      setError('Action not available in browser mode')
      return
    }

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
      let result: TestResult

      if (isTauriContext()) {
        // Native mode: use Tauri command
        result = await invoke<TestResult>('test_ollama')
      } else {
        // Browser mode: HTTP fallback
        const questions = [
          { category: 'math', prompt: '¿Cuál es la raíz cuadrada de 144? Responde solo el número.' },
          { category: 'anatomy', prompt: 'Explica brevemente qué es el hígado y su función principal.' },
          { category: 'math', prompt: '¿Cuál es la raíz cuadrada de 256? Responde solo el número.' },
          { category: 'anatomy', prompt: 'Explica brevemente qué es el corazón y su función principal.' },
          { category: 'math', prompt: '¿Cuál es la raíz cuadrada de 625? Responde solo el número.' },
          { category: 'anatomy', prompt: 'Explica brevemente qué son los pulmones y su función.' }
        ]

        const now = Math.floor(Date.now() / 1000)
        const idx = now % questions.length
        const { category, prompt } = questions[idx]

        const start = Date.now()
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), 60000) // 60s timeout

        const response = await fetch('http://localhost:11434/api/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            model: 'qwen3:1.7b',
            prompt: prompt,
            stream: false
          }),
          signal: controller.signal
        })

        clearTimeout(timeoutId)
        const elapsed_ms = Date.now() - start

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }

        const data = await response.json()

        result = {
          category,
          question: prompt,
          answer: data.response?.trim() || '',
          elapsed_ms,
          timestamp: new Date().toISOString(),
          rag_metadata: null
        }
      }

      setTestResult(result)
    } catch (err) {
      setError(String(err))
    } finally {
      setActionLoading(null)
    }
  }, [status?.ollama_running])

  // Smoke test handler (simple health check)
  const handleTestLLMHealth = useCallback(async () => {
    setActionLoading('smoke-test')
    setError(null)

    try {
      interface SmokeTestResult {
        success: boolean
        latency_ms: number
        response: string
        error?: string
      }

      let result: SmokeTestResult

      if (isTauriContext()) {
        // Native mode: use Tauri command (faster, with Rust error handling)
        result = await invoke<SmokeTestResult>('test_llm_health')
      } else {
        // Browser mode: direct HTTP fallback (works without Tauri)
        const start = Date.now()

        try {
          const controller = new AbortController()
          const timeoutId = setTimeout(() => controller.abort(), 15000) // 15s timeout (allows Ollama cold start)

          const response = await fetch('http://localhost:11434/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              model: 'qwen2.5-coder:3b',
              prompt: 'What is 2+2? Answer with just the number, nothing else.',
              stream: false
            }),
            signal: controller.signal
          })

          clearTimeout(timeoutId)
          const latency_ms = Date.now() - start

          if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`)
          }

          const data = await response.json()
          const answer = data.response?.trim() || ''
          const success = answer.includes('4')

          result = {
            success,
            latency_ms,
            response: answer,
            error: success ? undefined : `Expected '4' in response, got: ${answer}`
          }
        } catch (err: any) {
          const latency_ms = Date.now() - start
          result = {
            success: false,
            latency_ms,
            response: '',
            error: err.name === 'AbortError'
              ? 'Request timeout (15s) - Ollama may be loading the model'
              : `HTTP request failed: ${err.message}`
          }
        }
      }

      // Convert to TestResult format for display
      if (result.success) {
        setTestResult({
          category: 'smoke',
          question: 'What is 2+2?',
          answer: `✅ LLM Health OK\n\nResponse: ${result.response}\nLatency: ${result.latency_ms}ms${isTauriContext() ? '' : ' (browser mode)'}`,
          elapsed_ms: result.latency_ms,
          timestamp: new Date().toISOString(),
          rag_metadata: null
        })
      } else {
        setError(result.error || 'Smoke test failed')
      }
    } catch (err) {
      setError(String(err))
    } finally {
      setActionLoading(null)
    }
  }, [])

  const runBenchmark = useCallback(async () => {
    if (!isTauriContext()) {
      setError('Benchmark not available in browser mode')
      return
    }

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
    if (!isTauriContext()) {
      console.warn('[App] Skipping benchmark listener (not in Tauri context)')
      return
    }

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

  const loadTunnelFile = async () => {
    if (!isTauriContext()) {
      setTunnelFileContent('Not available in browser mode')
      return
    }

    try {
      const content = await invoke<string>('read_tunnel_file')
      // Format JSON for better readability
      const parsed = JSON.parse(content)
      setTunnelFileContent(JSON.stringify(parsed, null, 2))
    } catch (error) {
      console.error('Failed to read tunnel file:', error)
      setTunnelFileContent(`Error: ${String(error)}`)
    }
  }

  // Auto-load tunnel file (always try, even when tunnel is OFF)
  useEffect(() => {
    loadTunnelFile()
  }, [status?.tunnel_running, status?.tunnel_url])

  if (loading) {
    return <div className="app loading"><div className="spinner" /><span>Conectando...</span></div>
  }

  const ollamaOn = status?.ollama_running ?? false
  const tunnelOn = status?.tunnel_running ?? false

  // Tab configuration (conditional - Tunnel tab solo visible en modo Cloudflared)
  const isCloudflaredMode = status?.tunnel_url?.startsWith('https://') ?? false
  const tabs: Tab[] = [
    { id: 'services', label: 'Services', icon: '🔌' },
    ...(isCloudflaredMode ? [{ id: 'tunnel' as TabId, label: 'Tunnel', icon: '🔗' }] : []),
    { id: 'config', label: 'Config', icon: '⚙️' },
    { id: 'testing', label: 'Testing', icon: '🧪' },
    { id: 'benchmarks', label: 'Benchmarks', icon: '⚡' },
  ]

  // Services section (Topology + Control for all services)
  const renderServicesTab = () => {
    const ragOn = status?.rag_service_running ?? false
    const gatewayOn = status?.gateway_running ?? false

    // Service topology data
    const services = [
      {
        name: 'Ollama',
        port: 11434,
        icon: '🦙',
        running: ollamaOn,
        description: 'LLM Engine'
      },
      {
        name: 'RAG',
        port: 11435,
        icon: '🔍',
        running: ragOn,
        description: 'Embeddings'
      },
      {
        name: 'Gateway',
        port: 11400,
        icon: '🚪',
        running: gatewayOn,
        description: 'Router'
      }
    ]

    return (
      <div className="flex flex-col gap-4 p-4">
        {/* Services Topology (READ-ONLY) */}
        <div className="bg-app-surface rounded-lg border border-app-border p-2">
          <div className="flex items-center gap-1 mb-1">
            <span className="text-xs">🗺️</span>
            <span className="text-xs font-medium text-app-text">Services Topology</span>
          </div>

          <div className="services-topology">
            {services.map(service => (
              <div
                key={service.port}
                className={`service-mini ${service.running ? 'active' : 'inactive'}`}
              >
                <div className="service-mini-icon">{service.icon}</div>
                <div className="service-mini-body">
                  <div className="service-mini-name">{service.name}</div>
                  <div className="service-mini-port">:{service.port}</div>
                  <div className="service-mini-desc">{service.description}</div>
                </div>
                <div className={`service-mini-status ${service.running ? 'on' : 'off'}`}>
                  {service.running ? '🟢' : '⚪'}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Service Control Cards */}
        <div className="services-grid">
          {/* Ollama */}
          <div className={`service-card ${ollamaOn ? 'active' : ''}`} style={{ flexDirection: 'column', alignItems: 'stretch' }}>
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
              <div className="service-icon">🦙</div>
              <div style={{ flex: 1 }}>
                <div className="service-name">Ollama</div>
                <div className={`service-status ${ollamaOn ? 'on' : 'off'}`}>
                  {ollamaOn ? '● Activo' : '○ Inactivo'}
                </div>
              </div>
              <button
                className={`action-btn ${ollamaOn ? 'stop' : 'start'}`}
                onClick={() => handleAction(ollamaOn ? 'ollama-stop' : 'ollama-start', ollamaOn ? 'stop_ollama' : 'start_ollama')}
                disabled={!!actionLoading}
              >
                {actionLoading?.includes('ollama') ? '...' : ollamaOn ? '■' : '▶'}
              </button>
            </div>

            {/* Body */}
            <div>
              {ollamaOn && status?.ollama_models && status.ollama_models.length > 0 && (
                <div className="models" style={{ marginBottom: '8px' }}>{status.ollama_models.slice(0, 2).join(', ')}</div>
              )}
              {ollamaOn && (
                <button
                  className="models-btn"
                  onClick={() => setShowModelManager(!showModelManager)}
                  style={{
                    marginBottom: '8px',
                    padding: '4px 8px',
                    fontSize: '11px',
                    background: 'var(--surface)',
                    border: '1px solid var(--border)',
                    borderRadius: '3px',
                    cursor: 'pointer',
                    color: 'var(--text-dim)'
                  }}
                >
                  📦 {showModelManager ? 'Hide' : 'Show'} Models
                </button>
              )}

              {/* Logs Viewer - Disabled (get_service_logs not implemented) */}
              {/* {ollamaOn && (
                <LogsViewer serviceName="ollama" serviceDisplayName="Ollama" />
              )} */}
            </div>
          </div>

          {/* RAG Service */}
          <div className={`service-card ${ragOn ? 'active' : ''} ${!ollamaOn ? 'disabled' : ''}`} style={{ flexDirection: 'column', alignItems: 'stretch' }}>
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
              <div className="service-icon">🔍</div>
              <div style={{ flex: 1 }}>
                <div className="service-name">RAG Service</div>
                <div className={`service-status ${ragOn ? 'on' : 'off'}`}>
                  {ragOn ? '● Activo' : '○ Inactivo'}
                </div>
              </div>
            </div>

            {/* Stats (cuando está activo) */}
            {ragOn && ragStats && (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '11px', color: 'var(--text-dim)' }}>
                <div>
                  <div style={{ fontWeight: 600, color: 'var(--text)', marginBottom: '2px' }}>GPU Memory</div>
                  <div>{ragStats.gpu_memory_used_mb} MB / {(ragStats.gpu_memory_total_mb / 1024).toFixed(0)} GB</div>
                  <div style={{ marginTop: '2px', fontSize: '10px' }}>{ragStats.gpu_device.toUpperCase()}</div>
                </div>
                <div>
                  <div style={{ fontWeight: 600, color: 'var(--text)', marginBottom: '2px' }}>Model</div>
                  <div>{ragStats.model_name}</div>
                </div>
                <div>
                  <div style={{ fontWeight: 600, color: 'var(--text)', marginBottom: '2px' }}>Embeddings</div>
                  <div>{ragStats.embeddings_count.toLocaleString()} chunks</div>
                </div>
                <div>
                  <div style={{ fontWeight: 600, color: 'var(--text)', marginBottom: '2px' }}>Performance</div>
                  <div>{ragStats.avg_query_ms.toFixed(1)}ms avg</div>
                  <div>{ragStats.throughput_qps.toFixed(0)} QPS</div>
                </div>
              </div>
            )}

            {/* Loading state */}
            {ragOn && !ragStats && (
              <div style={{ fontSize: '11px', color: 'var(--text-dim)', textAlign: 'center', padding: '12px' }}>
                Loading stats...
              </div>
            )}

            {/* Inactive state */}
            {!ragOn && (
              <div style={{ fontSize: '11px', color: 'var(--text-dim)', textAlign: 'center', padding: '12px' }}>
                Auto-starts with Ollama
              </div>
            )}
          </div>
        </div>

        {/* Model Manager (conditional) */}
        {showModelManager && ollamaOn && <ModelManager />}
      </div>
    )
  }

  // Tunnel section
  const handleSaveTunnelPort = async () => {
    if (!isTauriContext()) {
      setTunnelPortError('Not available in browser mode')
      return
    }

    setTunnelPortError(null)

    // Validación client-side
    const port = parseInt(tunnelPort, 10)
    if (isNaN(port)) {
      setTunnelPortError('Port must be a number')
      return
    }
    if (port < 1024 || port > 65535) {
      setTunnelPortError('Port must be between 1024-65535')
      return
    }

    try {
      await invoke('set_tunnel_port', { port })
      setSavedTunnelPort(tunnelPort)
      setTunnelPortError(null)
    } catch (err) {
      setTunnelPortError(String(err))
    }
  }

  const renderTunnelTab = () => {
    return (
      <div className="flex gap-4 p-4 h-full">
        {/* ===== COLUMN 1: Tunnel Controls ===== */}
        <div className="flex flex-col gap-4 flex-1">
          {/* Tunnel Service Card */}
          <div className={`service-card ${tunnelOn ? 'active' : ''} ${!status?.ollama_running ? 'disabled' : ''}`}>
            <div className="service-icon">🔗</div>
            <div className="service-body">
              <div className="service-name">Tunnel</div>
              <div className={`service-status ${tunnelOn ? 'on' : 'off'}`}>
                {tunnelOn
                  ? status?.tunnel_url?.startsWith('https://')
                    ? '● Cloudflared'
                    : `● Local (${savedTunnelPort})`
                  : '○ Desconectado'}
              </div>
              {tunnelOn && status?.tunnel_url?.startsWith('https://') && (
                <div className="tunnel-url-box" onClick={handleCopyUrl} title="Click para copiar">
                  <span className="url-text">{status.tunnel_url.replace('https://', '')}</span>
                  <span className="copy-icon">{copiedUrl ? '✓' : '📋'}</span>
                </div>
              )}
              {tunnelOn && status?.tunnel_url?.startsWith('https://') && !status.tunnel_url.includes('trycloudflare') && (
                <div className="tunnel-url-pending">⏳ Obteniendo URL...</div>
              )}
            </div>
            <button
              className={`action-btn ${tunnelOn ? 'stop' : 'start'}`}
              onClick={() => handleAction(tunnelOn ? 'tunnel-stop' : 'tunnel-start', tunnelOn ? 'stop_tunnel' : 'start_tunnel')}
              disabled={!!actionLoading || !status?.ollama_running}
            >
              {actionLoading?.includes('tunnel') ? '...' : tunnelOn ? '■' : '▶'}
            </button>
          </div>

          {/* Warning section */}
          {!status?.ollama_running && (
            <div className="bg-app-surface rounded-lg border border-app-warning p-4 text-sm text-app-text-dim">
              ⚠️ Start Ollama first to enable the tunnel
            </div>
          )}
        </div>

        {/* ===== COLUMN 2: File Viewer ===== */}
        <div className="flex flex-col flex-1">
          <div className="bg-app-surface rounded-lg border border-app-border p-4 h-full flex flex-col">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-base">📄</span>
              <span className="text-sm font-medium text-app-text">tunnel-url.json</span>
            </div>
            {tunnelFileContent ? (
              <textarea
                readOnly
                value={tunnelFileContent}
                className="flex-1 bg-app-bg text-app-text text-xs font-mono p-3 rounded border border-app-border resize-none focus:outline-none focus:ring-1 focus:ring-app-accent"
                style={{ minHeight: '200px' }}
              />
            ) : (
              <div className="flex-1 flex items-center justify-center text-app-text-dim text-sm">
                No file yet - start tunnel to create
              </div>
            )}
          </div>
        </div>
      </div>
    )
  }

  // Config section - Port Configuration
  const renderConfigTab = () => {
    const portChanged = tunnelPort !== savedTunnelPort
    const portValid = !isNaN(parseInt(tunnelPort, 10)) &&
                      parseInt(tunnelPort, 10) >= 1024 &&
                      parseInt(tunnelPort, 10) <= 65535

    // Port occupation detection
    const isPortOccupied = (port: number): boolean => {
      if (port === 11434) return status?.ollama_running || false
      if (port === 11435) return status?.rag_service_running || false
      if (port === 11400) return status?.gateway_running || false
      return false
    }

    // Port selection handler with smart validation
    const handlePortSelect = (port: number) => {
      if (tunnelOn) {
        setTunnelPortError('Stop tunnel first to change port')
        return
      }
      if (isPortOccupied(port)) {
        setTunnelPortError(`Port ${port} is in use by another service`)
        return
      }
      setTunnelPort(String(port))
      setTunnelPortError(null)
    }

    // Port options for selection (with conflict detection)
    const portOptions = [
      {
        port: 11400,
        label: 'Gateway',
        description: 'Enruta /api → Ollama, /rag → RAG',
        recommended: true,
        occupied: isPortOccupied(11400)
      },
      {
        port: 11434,
        label: 'Ollama Direct',
        description: 'Bypass Gateway - Direct LLM access',
        recommended: false,
        occupied: isPortOccupied(11434)
      },
      {
        port: 11435,
        label: 'RAG Direct',
        description: 'Bypass Gateway - Direct embeddings access',
        recommended: false,
        occupied: isPortOccupied(11435)
      }
    ]

    return (
      <>
      <div className="grid grid-cols-2 gap-3 p-3">
        {/* ===== Port Configuration (RADIO CARDS) - Left Column ===== */}
        <div className="bg-app-surface rounded-lg border border-app-border p-3 flex flex-col">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className="text-sm">🔌</span>
              <span className="text-xs font-medium text-app-text">Tunnel Port Configuration</span>
            </div>
            {portChanged && (
              <span className="text-xs text-app-warning">● Unsaved</span>
            )}
          </div>

          {/* Radio button cards for presets */}
          <div className="port-options-grid">
            {portOptions.map(option => {
              const isSelected = parseInt(tunnelPort) === option.port
              const isDisabled = tunnelOn || option.occupied

              return (
                <div
                  key={option.port}
                  className={`
                    port-option
                    ${isSelected ? 'selected' : ''}
                    ${isDisabled ? 'disabled' : ''}
                  `}
                  onClick={() => !isDisabled && handlePortSelect(option.port)}
                >
                  <div className="port-option-header">
                    <div className="port-option-radio">
                      {isSelected ? '⦿' : '○'}
                    </div>
                    <div className="port-option-title">
                      {option.label} ({option.port})
                      {option.recommended && (
                        <span className="port-option-badge recommended">✓ Recommended</span>
                      )}
                      {option.occupied && (
                        <span className="port-option-badge occupied">⚠️ Occupied</span>
                      )}
                    </div>
                  </div>
                  <div className="port-option-description">
                    {option.description}
                  </div>
                </div>
              )
            })}
          </div>

          {/* Custom port input */}
          <div className="port-option custom" style={{ marginTop: '6px' }}>
            <div className="port-option-header">
              <div className="port-option-radio">
                {!portOptions.find(opt => opt.port === parseInt(tunnelPort)) ? '⦿' : '○'}
              </div>
              <div className="port-option-title">Custom Port</div>
            </div>
            <div className="flex items-center gap-2 mt-2">
              <input
                type="number"
                value={tunnelPort}
                onChange={(e) => {
                  setTunnelPort(e.target.value)
                  setTunnelPortError(null)
                }}
                className={`
                  flex-1 bg-app-bg border rounded px-2 py-1.5 text-xs text-app-text
                  focus:outline-none focus:border-app-accent
                  ${tunnelPortError ? 'border-red-500' : 'border-app-border'}
                `}
                placeholder="1024-65535"
                min="1024"
                max="65535"
                disabled={tunnelOn}
              />
              <button
                onClick={handleSaveTunnelPort}
                disabled={!portChanged || !portValid || tunnelOn}
                className={`
                  px-3 py-1.5 rounded text-xs font-medium transition-colors
                  ${portChanged && portValid && !tunnelOn
                    ? 'bg-app-accent text-white hover:bg-app-accent-bright'
                    : 'bg-app-surface text-app-text-dim cursor-not-allowed'
                  }
                `}
              >
                Save
              </button>
            </div>
          </div>

          {tunnelPortError && (
            <div className="text-xs text-red-500 mt-2 p-1.5 bg-red-500 bg-opacity-10 rounded border border-red-500 border-opacity-30">
              ⚠️ {tunnelPortError}
            </div>
          )}

          {tunnelOn && portChanged && (
            <div className="text-xs text-app-warning mt-2 p-1.5 bg-app-warning bg-opacity-10 rounded border border-app-warning border-opacity-30">
              ⚠️ Stop tunnel and restart to apply port changes
            </div>
          )}
        </div>

        {/* Info section */}
        <div className="bg-app-surface rounded-lg border border-app-border p-3">
          <div className="text-xs text-app-text-dim leading-relaxed">
            <div className="font-semibold text-app-text mb-2">💡 Port Information</div>
            <div className="space-y-1">
              <div><span className="text-app-accent">Gateway (11400)</span> - Routes /api to Ollama and /rag to RAG Service</div>
              <div><span className="text-app-accent">Ollama (11434)</span> - Direct LLM access, bypasses Gateway</div>
              <div><span className="text-app-accent">RAG (11435)</span> - Direct embeddings access, bypasses Gateway</div>
            </div>
            <div className="mt-3 text-app-warning">
              ⚠️ Changes require tunnel restart to take effect
            </div>
          </div>
        </div>
      </div>

      {/* Environment Variables Editor */}
      <EnvVarEditor />
      </>
    )
  }

  // Testing section
  const renderTestingTab = () => (
    <div className="p-4">
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

      {/* Smoke Test (Quick Health Check) */}
      <div className="test-section mt-4">
        <div className="test-header">
          <div className="test-title">
            <span className="icon">🔬</span>
            <span>Smoke Test (Health Check)</span>
          </div>
          <button
            className="test-btn"
            onClick={handleTestLLMHealth}
            disabled={actionLoading === 'smoke-test' || !ollamaOn}
            title="Quick 2+2 test to verify LLM is responding (works in browser mode)"
          >
            {actionLoading === 'smoke-test' ? '⏳' : '▶'}
          </button>
        </div>
        <div className="test-placeholder text-sm text-gray-400">
          {ollamaOn ? 'Quick sanity check: asks LLM "What is 2+2?" (HTTP direct, works everywhere)' : 'Start Ollama first'}
        </div>
      </div>

      {/* Test Suite Library */}
      <TestSuiteLibrary />
    </div>
  )

  // Benchmarks section
  const renderBenchmarksTab = () => (
    <div className="p-4">
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

      {/* Historical Performance Graphs */}
      <BenchmarkCharts />
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

      {/* Main Layout: Sidebar + Content */}
      <div className="flex-1 flex flex-row min-h-0 overflow-hidden">
        {/* Sidebar Navigation */}
        <div className="sidebar-nav">
          <ul className="flex flex-col gap-1">
            {tabs.map(tab => (
              <li key={tab.id}>
                <button
                  onClick={() => setActiveTab(tab.id)}
                  className={`
                    sidebar-tab
                    ${activeTab === tab.id ? 'active' : ''}
                  `}
                  aria-current={activeTab === tab.id ? 'page' : undefined}
                >
                  <span className="tab-icon">{tab.icon}</span>
                  <span className="tab-label">{tab.label}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>

        {/* Tab Content */}
        <div className="flex-1 flex flex-col min-h-0 overflow-y-auto">
          {activeTab === 'services' && renderServicesTab()}
          {activeTab === 'tunnel' && renderTunnelTab()}
          {activeTab === 'config' && renderConfigTab()}
          {activeTab === 'testing' && renderTestingTab()}
          {activeTab === 'benchmarks' && renderBenchmarksTab()}
        </div>
      </div>

      <footer className="statusbar">
        <span className={`dot ${ollamaOn ? 'green' : 'gray'}`} />
        <span className="status-text">
          {ollamaOn
            ? isCloudflaredMode
              ? 'Listo (Cloudflared)'
              : 'Listo'
            : 'Detenido'}
        </span>
        <span className="version">v{appVersion}</span>
      </footer>
    </div>
  )
}
