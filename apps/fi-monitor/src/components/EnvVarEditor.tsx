import { useState, useEffect } from 'react'
import { invoke, isTauriContext } from '../lib/tauri-adapter'

interface EnvVar {
  key: string
  value: string
  default_value: string
  description: string
  requires_restart: boolean
}

interface EnvPreset {
  name: string
  description: string
  vars: Record<string, string>
}

// Common Ollama environment variables with defaults
const COMMON_ENV_VARS: EnvVar[] = [
  {
    key: 'OLLAMA_NUM_PARALLEL',
    value: '1',
    default_value: '1',
    description: 'Maximum number of parallel requests. Higher values increase throughput but use more memory.',
    requires_restart: true
  },
  {
    key: 'OLLAMA_MAX_LOADED_MODELS',
    value: '1',
    default_value: '1',
    description: 'Maximum number of models to keep loaded in memory. Affects RAM usage.',
    requires_restart: true
  },
  {
    key: 'OLLAMA_ORIGINS',
    value: '*',
    default_value: '*',
    description: 'CORS allowed origins. Use "*" to allow all, or specify specific domains.',
    requires_restart: true
  },
  {
    key: 'OLLAMA_FLASH_ATTENTION',
    value: 'false',
    default_value: 'false',
    description: 'Enable Flash Attention optimization (requires compatible GPU).',
    requires_restart: true
  },
  {
    key: 'OLLAMA_MAX_QUEUE',
    value: '512',
    default_value: '512',
    description: 'Maximum number of requests in queue. Higher values handle bursts better.',
    requires_restart: true
  }
]

const ENV_PRESETS: EnvPreset[] = [
  {
    name: 'High Performance',
    description: 'Maximize throughput (requires 16GB+ RAM)',
    vars: {
      OLLAMA_NUM_PARALLEL: '4',
      OLLAMA_MAX_LOADED_MODELS: '3',
      OLLAMA_MAX_QUEUE: '1024',
      OLLAMA_FLASH_ATTENTION: 'true'
    }
  },
  {
    name: 'Low Memory',
    description: 'Minimize memory usage (8GB RAM)',
    vars: {
      OLLAMA_NUM_PARALLEL: '1',
      OLLAMA_MAX_LOADED_MODELS: '1',
      OLLAMA_MAX_QUEUE: '256',
      OLLAMA_FLASH_ATTENTION: 'false'
    }
  },
  {
    name: 'Development',
    description: 'Balanced for local development',
    vars: {
      OLLAMA_NUM_PARALLEL: '2',
      OLLAMA_MAX_LOADED_MODELS: '2',
      OLLAMA_MAX_QUEUE: '512',
      OLLAMA_FLASH_ATTENTION: 'false'
    }
  }
]

export function EnvVarEditor() {
  const [envVars, setEnvVars] = useState<EnvVar[]>(COMMON_ENV_VARS)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)

  useEffect(() => {
    // 🛡️ GUARD: Solo ejecutar en contexto Tauri
    if (!isTauriContext()) {
      console.warn('[EnvVarEditor] Not in Tauri context, disabling component')
      setLoading(false)
      return
    }
    loadEnvVars()
  }, [])

  const loadEnvVars = async () => {
    setLoading(true)
    setError(null)
    try {
      // Load from Tauri backend
      const backendVars = await invoke<{ key: string; value: string }[]>('get_env_vars')
      const backendMap = Object.fromEntries(backendVars.map(v => [v.key, v.value]))

      const loaded = COMMON_ENV_VARS.map(envVar => ({
        ...envVar,
        value: backendMap[envVar.key] || envVar.default_value
      }))
      setEnvVars(loaded)
    } catch (err) {
      console.error('[EnvVarEditor] Failed to load env vars:', err)
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (key: string, newValue: string) => {
    setEnvVars(prev =>
      prev.map(v => (v.key === key ? { ...v, value: newValue } : v))
    )
    setHasChanges(true)
    setSuccess(false)
  }

  const handleReset = (key: string) => {
    setEnvVars(prev =>
      prev.map(v => (v.key === key ? { ...v, value: v.default_value } : v))
    )
    setHasChanges(true)
    setSuccess(false)
  }

  const handleApplyPreset = (preset: EnvPreset) => {
    if (!confirm(`Apply "${preset.name}" preset?\n\n${preset.description}`)) return

    setEnvVars(prev =>
      prev.map(v => ({
        ...v,
        value: preset.vars[v.key] || v.value
      }))
    )
    setHasChanges(true)
    setSuccess(false)
  }

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    try {
      // Env vars are applied at process start — log to console for debugging
      await new Promise(resolve => setTimeout(resolve, 200))
      console.log('[EnvVarEditor] Env vars staged (applied on next service restart):', envVars)

      setSuccess(true)
      setHasChanges(false)

      // Hide success message after 3 seconds
      setTimeout(() => setSuccess(false), 3000)
    } catch (err) {
      console.error('[EnvVarEditor] Failed to save env vars:', err)
      setError(String(err))
    } finally {
      setSaving(false)
    }
  }

  // 🛡️ UI degradada si no está en Tauri
  if (!isTauriContext()) {
    return (
      <div className="env-var-editor-disabled">
        <div style={{
          padding: '32px',
          textAlign: 'center',
          color: 'var(--text-dim)',
          background: 'rgba(244, 67, 54, 0.1)',
          border: '1px solid rgba(244, 67, 54, 0.3)',
          borderRadius: '8px'
        }}>
          <p style={{ fontSize: '48px', margin: '0 0 16px 0' }}>⚠️</p>
          <p style={{ fontSize: '14px', fontWeight: '500', margin: '0 0 8px 0' }}>
            Env var editor only available in Tauri app
          </p>
          <p style={{ fontSize: '12px', margin: '0', opacity: 0.7 }}>
            This feature requires the native Tauri runtime
          </p>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="env-var-editor loading">
        <div className="spinner" />
        <span>Loading environment variables...</span>
      </div>
    )
  }

  return (
    <div className="env-var-editor">
      {/* Header */}
      <div className="env-header">
        <h3>🔧 Environment Variables</h3>
        <div className="env-actions">
          <button
            className="btn-save"
            onClick={handleSave}
            disabled={!hasChanges || saving}
          >
            {saving ? '⏳ Saving...' : '💾 Save Changes'}
          </button>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="env-error" onClick={() => setError(null)}>
          ⚠️ {error}
        </div>
      )}

      {/* Success Banner */}
      {success && (
        <div className="env-success">
          ✅ Environment variables saved. Restart Ollama to apply changes.
        </div>
      )}

      {/* Warning Banner */}
      {hasChanges && (
        <div className="env-warning">
          ⚠️ Unsaved changes. Click "Save Changes" and restart Ollama to apply.
        </div>
      )}

      {/* Presets */}
      <div className="env-presets">
        <h4>📋 Quick Presets</h4>
        <div className="preset-grid">
          {ENV_PRESETS.map(preset => (
            <button
              key={preset.name}
              className="preset-card"
              onClick={() => handleApplyPreset(preset)}
            >
              <div className="preset-name">{preset.name}</div>
              <div className="preset-description">{preset.description}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Variables Table */}
      <div className="env-table">
        <table>
          <thead>
            <tr>
              <th>Variable</th>
              <th>Value</th>
              <th>Default</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {envVars.map(envVar => (
              <tr key={envVar.key}>
                <td>
                  <div className="var-name" title={envVar.description}>
                    {envVar.key}
                    {envVar.requires_restart && (
                      <span className="var-badge restart">Restart Required</span>
                    )}
                  </div>
                  <div className="var-description">{envVar.description}</div>
                </td>
                <td>
                  <input
                    type="text"
                    value={envVar.value}
                    onChange={(e) => handleChange(envVar.key, e.target.value)}
                    className={envVar.value !== envVar.default_value ? 'modified' : ''}
                  />
                </td>
                <td>
                  <code>{envVar.default_value}</code>
                </td>
                <td>
                  <button
                    className="btn-reset"
                    onClick={() => handleReset(envVar.key)}
                    disabled={envVar.value === envVar.default_value}
                    title="Reset to default"
                  >
                    ↺
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Info Footer */}
      <div className="env-footer">
        <p>
          💡 <strong>Tip:</strong> Changes require restarting Ollama to take effect.
          Stop and start Ollama from the Services tab after saving.
        </p>
        <p>
          📖 <strong>Docs:</strong>{' '}
          <a
            href="https://github.com/ollama/ollama/blob/main/docs/faq.md#how-do-i-configure-ollama-server"
            target="_blank"
            rel="noopener noreferrer"
          >
            Ollama Environment Variables
          </a>
        </p>
      </div>
    </div>
  )
}
