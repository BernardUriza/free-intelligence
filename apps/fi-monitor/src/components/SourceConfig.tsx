import { useState, useEffect } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:9200'

interface OllamaConfig {
  source: 'tunnel' | 'local'
  tunnel_url: string
  local_url: string
}

interface ConnectionStatus {
  connected: boolean
  latency_ms: number | null
  error: string | null
}

export function SourceConfig() {
  const [config, setConfig] = useState<OllamaConfig>({
    source: 'local',
    tunnel_url: '',
    local_url: 'http://localhost:11434'
  })
  const [status, setStatus] = useState<ConnectionStatus>({
    connected: false,
    latency_ms: null,
    error: null
  })
  const [testing, setTesting] = useState(false)
  const [saving, setSaving] = useState(false)
  const [dirty, setDirty] = useState(false)

  // Load config on mount
  useEffect(() => {
    loadConfig()
  }, [])

  const loadConfig = async () => {
    try {
      const res = await fetch(`${API_URL}/admin/system/ollama/config`)
      if (res.ok) {
        const data = await res.json()
        setConfig(data)
        // Auto-test on load
        testConnection(data)
      }
    } catch (err) {
      console.error('Failed to load config:', err)
    }
  }

  const testConnection = async (configToTest?: OllamaConfig) => {
    setTesting(true)
    setStatus({ connected: false, latency_ms: null, error: null })

    const testConfig = configToTest || config
    const url = testConfig.source === 'tunnel' ? testConfig.tunnel_url : testConfig.local_url

    try {
      const res = await fetch(`${API_URL}/admin/system/ollama/test?url=${encodeURIComponent(url)}`)
      const data = await res.json()
      setStatus({
        connected: data.connected,
        latency_ms: data.latency_ms,
        error: data.error
      })
    } catch (err) {
      setStatus({
        connected: false,
        latency_ms: null,
        error: 'Failed to reach backend'
      })
    } finally {
      setTesting(false)
    }
  }

  const saveConfig = async () => {
    setSaving(true)
    try {
      const res = await fetch(`${API_URL}/admin/system/ollama/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      })
      if (res.ok) {
        setDirty(false)
        // Test after saving
        testConnection()
      }
    } catch (err) {
      console.error('Failed to save config:', err)
    } finally {
      setSaving(false)
    }
  }

  const handleSourceChange = (source: 'tunnel' | 'local') => {
    setConfig(prev => ({ ...prev, source }))
    setDirty(true)
  }

  const handleUrlChange = (field: 'tunnel_url' | 'local_url', value: string) => {
    setConfig(prev => ({ ...prev, [field]: value }))
    setDirty(true)
  }

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">Ollama Source</span>
        <span className={`status-badge ${status.connected ? 'success' : 'error'}`}>
          <span className={`status-dot ${status.connected ? 'running' : 'stopped'}`}></span>
          {testing ? 'Testing...' : status.connected ? 'Connected' : 'Disconnected'}
        </span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {/* Source Selection */}
        <div style={{ display: 'flex', gap: '1rem' }}>
          <label style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            cursor: 'pointer',
            padding: '0.5rem 1rem',
            background: config.source === 'tunnel' ? 'rgba(59, 130, 246, 0.2)' : 'var(--bg-card)',
            borderRadius: '0.375rem',
            border: config.source === 'tunnel' ? '1px solid var(--accent)' : '1px solid var(--border)'
          }}>
            <input
              type="radio"
              name="source"
              checked={config.source === 'tunnel'}
              onChange={() => handleSourceChange('tunnel')}
            />
            <span>Tunnel (Windows)</span>
          </label>

          <label style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            cursor: 'pointer',
            padding: '0.5rem 1rem',
            background: config.source === 'local' ? 'rgba(59, 130, 246, 0.2)' : 'var(--bg-card)',
            borderRadius: '0.375rem',
            border: config.source === 'local' ? '1px solid var(--accent)' : '1px solid var(--border)'
          }}>
            <input
              type="radio"
              name="source"
              checked={config.source === 'local'}
              onChange={() => handleSourceChange('local')}
            />
            <span>Local (localhost)</span>
          </label>
        </div>

        {/* URL Input */}
        <div>
          <label style={{
            display: 'block',
            fontSize: '0.75rem',
            color: 'var(--text-secondary)',
            marginBottom: '0.25rem'
          }}>
            {config.source === 'tunnel' ? 'Tunnel URL' : 'Local URL'}
          </label>
          <input
            type="text"
            value={config.source === 'tunnel' ? config.tunnel_url : config.local_url}
            onChange={(e) => handleUrlChange(
              config.source === 'tunnel' ? 'tunnel_url' : 'local_url',
              e.target.value
            )}
            placeholder={config.source === 'tunnel'
              ? 'https://xxx.trycloudflare.com'
              : 'http://localhost:11434'
            }
            style={{
              width: '100%',
              padding: '0.5rem 0.75rem',
              background: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderRadius: '0.375rem',
              color: 'var(--text-primary)',
              fontSize: '0.875rem'
            }}
          />
        </div>

        {/* Status Info */}
        {status.latency_ms !== null && (
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Latency: {status.latency_ms}ms
          </div>
        )}
        {status.error && (
          <div style={{ fontSize: '0.75rem', color: 'var(--error)' }}>
            {status.error}
          </div>
        )}

        {/* Actions */}
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            className="refresh-btn"
            onClick={() => testConnection()}
            disabled={testing}
            style={{ flex: 1 }}
          >
            {testing ? '...' : '⚡'} Test
          </button>
          <button
            className="refresh-btn"
            onClick={saveConfig}
            disabled={saving || !dirty}
            style={{
              flex: 1,
              background: dirty ? 'var(--success)' : 'var(--bg-card)',
              cursor: dirty ? 'pointer' : 'not-allowed'
            }}
          >
            {saving ? '...' : '💾'} Save
          </button>
        </div>
      </div>
    </div>
  )
}
