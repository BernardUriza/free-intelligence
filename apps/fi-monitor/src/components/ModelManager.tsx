import { useState, useEffect } from 'react'
import { invoke } from '@tauri-apps/api/core'
import { listen } from '@tauri-apps/api/event'

interface OllamaModel {
  name: string
  size: string
  modified: string
  digest: string
}

export function ModelManager() {
  const [models, setModels] = useState<OllamaModel[]>([])
  const [loading, setLoading] = useState(true)
  const [pulling, setPulling] = useState<string | null>(null)
  const [newModel, setNewModel] = useState('')
  const [showPullDialog, setShowPullDialog] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadModels = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await invoke<OllamaModel[]>('list_ollama_models_detailed')
      setModels(result)
    } catch (err) {
      console.error('[ModelManager] Failed to load models:', err)
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadModels()
  }, [])

  // Listen for pull events
  useEffect(() => {
    const listeners: Promise<() => void>[] = []

    listeners.push(
      listen<string>('model-pull-started', (event) => {
        console.log('[ModelManager] Pull started:', event.payload)
        setPulling(event.payload)
        setError(null)
      })
    )

    listeners.push(
      listen<string>('model-pull-completed', (event) => {
        console.log('[ModelManager] Pull completed:', event.payload)
        setPulling(null)
        loadModels()
      })
    )

    listeners.push(
      listen<string>('model-pull-failed', (event) => {
        console.log('[ModelManager] Pull failed:', event.payload)
        setPulling(null)
        setError(event.payload)
      })
    )

    return () => {
      listeners.forEach(unlisten => unlisten.then(fn => fn()))
    }
  }, [])

  const handlePullModel = async () => {
    if (!newModel.trim()) return

    setError(null)
    try {
      await invoke('pull_ollama_model', { modelName: newModel.trim() })
      setShowPullDialog(false)
      setNewModel('')
    } catch (err) {
      console.error('[ModelManager] Pull error:', err)
      setError(`Failed to pull model: ${err}`)
    }
  }

  const handleDeleteModel = async (modelName: string) => {
    if (!confirm(`Delete model "${modelName}"?\n\nThis action cannot be undone.`)) return

    setError(null)
    try {
      await invoke('delete_ollama_model', { modelName })
      loadModels()
    } catch (err) {
      console.error('[ModelManager] Delete error:', err)
      setError(`Failed to delete model: ${err}`)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && newModel.trim()) {
      handlePullModel()
    } else if (e.key === 'Escape') {
      setShowPullDialog(false)
      setNewModel('')
    }
  }

  if (loading) {
    return (
      <div className="model-manager loading">
        <div className="spinner" />
        <span>Loading models...</span>
      </div>
    )
  }

  return (
    <div className="model-manager">
      {/* Header */}
      <div className="model-header">
        <span className="model-title">🦙 Installed Models</span>
        <button
          className="model-pull-btn"
          onClick={() => setShowPullDialog(true)}
          title="Pull new model from Ollama registry"
        >
          + Pull New Model
        </button>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="model-error" onClick={() => setError(null)}>
          ⚠️ {error}
        </div>
      )}

      {/* Models List */}
      {models.length === 0 ? (
        <div className="model-empty">
          <p>No models installed yet.</p>
          <p>Click "Pull New Model" to download one.</p>
        </div>
      ) : (
        <div className="model-list">
          {models.map((model, idx) => (
            <div key={model.digest} className={`model-item ${idx === 0 ? 'active' : ''}`}>
              <div className="model-info">
                <div className="model-name">
                  {idx === 0 && <span className="model-badge">⭐ Active</span>}
                  {model.name}
                </div>
                <div className="model-meta">
                  {model.size} • {model.modified} • {model.digest}
                </div>
              </div>
              <button
                className="model-delete-btn"
                onClick={() => handleDeleteModel(model.name)}
                disabled={idx === 0} // Prevent deleting active model
                title={idx === 0 ? "Cannot delete active model" : "Delete model"}
              >
                🗑️
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Pull Dialog */}
      {showPullDialog && (
        <div className="model-dialog-overlay" onClick={() => setShowPullDialog(false)}>
          <div className="model-dialog" onClick={(e) => e.stopPropagation()}>
            <h3>Pull New Model</h3>
            <input
              type="text"
              placeholder="Model name (e.g., llama3.3, gemma2, qwen2.5)"
              value={newModel}
              onChange={(e) => setNewModel(e.target.value)}
              onKeyDown={handleKeyPress}
              autoFocus
            />
            <div className="model-dialog-actions">
              <button onClick={() => {
                setShowPullDialog(false)
                setNewModel('')
              }}>
                Cancel
              </button>
              <button
                onClick={handlePullModel}
                disabled={!newModel.trim()}
                className="primary"
              >
                Pull
              </button>
            </div>
            <div className="model-presets">
              <span>Quick presets:</span>
              <button onClick={() => setNewModel('llama3.3')}>llama3.3</button>
              <button onClick={() => setNewModel('gemma2')}>gemma2</button>
              <button onClick={() => setNewModel('qwen2.5')}>qwen2.5</button>
              <button onClick={() => setNewModel('mistral')}>mistral</button>
            </div>
          </div>
        </div>
      )}

      {/* Pull Progress */}
      {pulling && (
        <div className="model-pull-progress">
          <div className="spinner small" />
          <span>Pulling {pulling}... This may take several minutes.</span>
        </div>
      )}
    </div>
  )
}
