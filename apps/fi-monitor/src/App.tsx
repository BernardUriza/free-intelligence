import { useState, useEffect, useCallback } from 'react'
import { invoke } from '@tauri-apps/api/core'
import { listen } from '@tauri-apps/api/event'

interface ServiceStatus {
  ollama_running: boolean
  ollama_models: string[]
  tunnel_running: boolean
  tunnel_url: string | null
  system_info: { platform: string; hostname: string }
}

interface TestResult {
  category: string
  question: string
  answer: string
  elapsed_ms: number
  timestamp: string
}

export default function App() {
  const [status, setStatus] = useState<ServiceStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [testResult, setTestResult] = useState<TestResult | null>(null)
  const [autoTest, setAutoTest] = useState(false)
  const [nextTestIn, setNextTestIn] = useState(60)
  const [copiedUrl, setCopiedUrl] = useState(false)

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

        <div className={`service-card ${tunnelOn ? 'active' : ''} ${!ollamaOn ? 'disabled' : ''}`}>
          <div className="service-icon">☁️</div>
          <div className="service-body">
            <div className="service-name">Tunnel</div>
            <div className={`service-status ${tunnelOn ? 'on' : 'off'}`}>
              {tunnelOn ? '● Conectado' : '○ Desconectado'}
            </div>
            {tunnelOn && status?.tunnel_url && (
              <div className="tunnel-url-box" onClick={handleCopyUrl} title="Click para copiar">
                <span className="url-text" title={status.tunnel_url}>{status.tunnel_url.replace('https://', '')}</span>
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
      </div>

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

      <footer className="statusbar">
        <span className={`dot ${ollamaOn ? 'green' : 'gray'}`} />
        <span className={`dot ${tunnelOn ? 'blue' : 'gray'}`} />
        <span className="status-text">{ollamaOn && tunnelOn ? 'Listo' : ollamaOn ? 'Tunnel pendiente' : 'Detenido'}</span>
        <span className="version">v1.0.1</span>
      </footer>
    </div>
  )
}
