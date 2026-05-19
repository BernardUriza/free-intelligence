import { useState, useEffect, useCallback, useRef } from 'react'
import { getVersion, invoke, isTauriContext } from './lib/tauri-adapter'
import { useServiceStatus } from './hooks/useServiceStatus'
import { useTunnelConfig } from './hooks/useTunnelConfig'
import { useBenchmarks } from './hooks/useBenchmarks'
import { useLLMTesting } from './hooks/useLLMTesting'
import { ServicesTab } from './components/tabs/ServicesTab'
import { TunnelTab } from './components/tabs/TunnelTab'
import { ConfigTab } from './components/tabs/ConfigTab'
import { TestingTab } from './components/tabs/TestingTab'
import { BenchmarksTab } from './components/tabs/BenchmarksTab'
import type { SetupState, TabId, Tab } from './types/monitor'

interface AppProps {
  setupState: SetupState
}

export default function App({ setupState }: AppProps) {
  const [copiedUrl, setCopiedUrl] = useState(false)
  const [showModelManager, setShowModelManager] = useState(false)
  const [appVersion, setAppVersion] = useState('1.0.0')
  const [activeTab, setActiveTab] = useState<TabId>('services')
  const [serviceToast, setServiceToast] = useState<string | null>(null)
  const prevStatus = useRef<{ rag: boolean; gateway: boolean } | null>(null)

  // Hooks
  const {
    status,
    loading,
    error,
    setError,
    actionLoading,
    setActionLoading,
    ragStats,
    handleAction,
  } = useServiceStatus()

  const {
    tunnelPort,
    setTunnelPort,
    tunnelPortError,
    setTunnelPortError,
    savedTunnelPort,
    tunnelFileContent,
    handleSaveTunnelPort,
  } = useTunnelConfig(status?.tunnel_running, status?.tunnel_url)

  const {
    benchmarkResults,
    isBenchmarking,
    runBenchmark,
  } = useBenchmarks(setError)

  const {
    testResult,
    autoTest,
    setAutoTest,
    nextTestIn,
    handleTestOllama,
    handleTestLLMHealth,
  } = useLLMTesting(
    status?.ollama_running ?? false,
    setActionLoading,
    setError,
  )

  // Get app version from Tauri
  useEffect(() => {
    if (!isTauriContext()) {
      setAppVersion('1.0.6-browser')
      return
    }
    getVersion().then(v => setAppVersion(v)).catch(() => {})
  }, [])

  // Detect service transitions (off -> on) and show toast
  useEffect(() => {
    const ragOn = status?.rag_service_running ?? false
    const gatewayOn = status?.gateway_running ?? false

    if (prevStatus.current !== null) {
      const msgs: string[] = []
      if (ragOn && !prevStatus.current.rag) msgs.push('RAG Service')
      if (gatewayOn && !prevStatus.current.gateway) msgs.push('Gateway')
      if (msgs.length > 0) {
        setServiceToast(`${msgs.join(' + ')} online`)
        setTimeout(() => setServiceToast(null), 4000)
      }
    }
    prevStatus.current = { rag: ragOn, gateway: gatewayOn }
  }, [status?.rag_service_running, status?.gateway_running])

  // Open in Browser handler
  const handleOpenInBrowser = useCallback(async () => {
    if (isTauriContext()) {
      try {
        const url = await invoke<string | null>('get_browser_url')
        if (url) window.open(url, '_blank')
      } catch {
        // Fallback: if the command fails, try localhost:1430
        window.open('http://localhost:1430', '_blank')
      }
    }
  }, [])

  // Redirect to services if Tunnel tab disappears (Local mode)
  useEffect(() => {
    const isCloudflared = status?.tunnel_url?.startsWith('https://') ?? false
    if (activeTab === 'tunnel' && !isCloudflared) {
      setActiveTab('services')
    }
  }, [activeTab, status?.tunnel_url])

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

  // Tab configuration (conditional - Tunnel tab solo visible en modo Cloudflared)
  const isCloudflaredMode = status?.tunnel_url?.startsWith('https://') ?? false
  const tabs: Tab[] = [
    { id: 'services', label: 'Services', icon: '\u{1F50C}' },
    ...(isCloudflaredMode ? [{ id: 'tunnel' as TabId, label: 'Tunnel', icon: '\u{1F517}' }] : []),
    { id: 'config', label: 'Config', icon: '\u2699\uFE0F' },
    { id: 'testing', label: 'Testing', icon: '\u{1F9EA}' },
    { id: 'benchmarks', label: 'Benchmarks', icon: '\u26A1' },
  ]

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="icon">{'\u26A1'}</span>
          <span className="title">FI Monitor</span>
        </div>
        <div className="system-info">
          <span className="host">{status?.system_info.hostname}</span>
          {isTauriContext() && (
            <button
              className="browser-btn"
              onClick={handleOpenInBrowser}
              title="Open in Chrome (DevTools available)"
            >
              {'\u{1F310}'} Browser
            </button>
          )}
        </div>
      </header>

      {error && <div className="toast error" onClick={() => setError(null)}>{'\u26A0\uFE0F'} {error}</div>}
      {serviceToast && <div className="toast success">{'\u2705'} {serviceToast}</div>}

      {setupState.skipped && (!setupState.ollamaInstalled || !setupState.pythonInstalled) && (
        <div className="toast warning" style={{ cursor: 'default' }}>
          {!setupState.pythonInstalled && !setupState.ollamaInstalled && '\u{1F40D}\u{1F999} Python 3.14 y Ollama no detectados'}
          {!setupState.pythonInstalled && setupState.ollamaInstalled && '\u{1F40D} Python 3.14 no detectado'}
          {setupState.pythonInstalled && !setupState.ollamaInstalled && '\u{1F999} Ollama no detectado'}
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
          {activeTab === 'services' && (
            <ServicesTab
              status={status}
              ragStats={ragStats}
              actionLoading={actionLoading}
              handleAction={handleAction}
              showModelManager={showModelManager}
              setShowModelManager={setShowModelManager}
            />
          )}
          {activeTab === 'tunnel' && (
            <TunnelTab
              status={status}
              actionLoading={actionLoading}
              handleAction={handleAction}
              savedTunnelPort={savedTunnelPort}
              tunnelFileContent={tunnelFileContent}
              copiedUrl={copiedUrl}
              handleCopyUrl={handleCopyUrl}
            />
          )}
          {activeTab === 'config' && (
            <ConfigTab
              status={status}
              tunnelPort={tunnelPort}
              setTunnelPort={setTunnelPort}
              tunnelPortError={tunnelPortError}
              setTunnelPortError={setTunnelPortError}
              savedTunnelPort={savedTunnelPort}
              tunnelOn={tunnelOn}
              handleSaveTunnelPort={handleSaveTunnelPort}
            />
          )}
          {activeTab === 'testing' && (
            <TestingTab
              ollamaOn={ollamaOn}
              testResult={testResult}
              actionLoading={actionLoading}
              autoTest={autoTest}
              setAutoTest={setAutoTest}
              nextTestIn={nextTestIn}
              handleTestOllama={handleTestOllama}
              handleTestLLMHealth={handleTestLLMHealth}
            />
          )}
          {activeTab === 'benchmarks' && (
            <BenchmarksTab
              status={status}
              benchmarkResults={benchmarkResults}
              isBenchmarking={isBenchmarking}
              runBenchmark={runBenchmark}
            />
          )}
        </div>
      </div>

      <footer className="statusbar">
        <span className={`dot ${ollamaOn ? 'green' : 'gray'}`} title="Ollama" />
        <span className="status-label">Ollama</span>
        <span className={`dot ${(status?.rag_service_running ?? false) ? 'green' : 'gray'}`} title="RAG" />
        <span className="status-label">RAG</span>
        <span className={`dot ${(status?.gateway_running ?? false) ? 'green' : 'gray'}`} title="Gateway" />
        <span className="status-label">GW</span>
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
