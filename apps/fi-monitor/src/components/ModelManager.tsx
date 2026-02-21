import { useState, useEffect, useCallback, type KeyboardEvent } from 'react';
import { invoke, listen } from '../lib/tauri-adapter';
import { Bot, Plus, Star, Trash2, AlertTriangle } from 'lucide-react';

// ── Types ────────────────────────────────────────────────────────────

interface OllamaModel {
  name: string;
  size: string;
  modified: string;
  digest: string;
}

// ── Constants ────────────────────────────────────────────────────────

const MODEL_PRESETS = ['llama3.3', 'gemma2', 'qwen2.5', 'mistral'] as const;

const PULL_EVENTS = {
  STARTED: 'model-pull-started',
  COMPLETED: 'model-pull-completed',
  FAILED: 'model-pull-failed',
} as const;

// ── Component ────────────────────────────────────────────────────────

export function ModelManager() {
  const [models, setModels] = useState<OllamaModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [pulling, setPulling] = useState<string | null>(null);
  const [newModel, setNewModel] = useState('');
  const [showPullDialog, setShowPullDialog] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadModels = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await invoke<OllamaModel[]>('list_ollama_models_detailed');
      setModels(result);
    } catch (err) {
      console.error('[ModelManager] Failed to load models:', err);
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadModels();
  }, [loadModels]);

  // Listen for pull events
  useEffect(() => {
    const listeners = [
      listen<string>(PULL_EVENTS.STARTED, (event) => {
        console.log('[ModelManager] Pull started:', event.payload);
        setPulling(event.payload);
        setError(null);
      }),
      listen<string>(PULL_EVENTS.COMPLETED, (event) => {
        console.log('[ModelManager] Pull completed:', event.payload);
        setPulling(null);
        loadModels();
      }),
      listen<string>(PULL_EVENTS.FAILED, (event) => {
        console.log('[ModelManager] Pull failed:', event.payload);
        setPulling(null);
        setError(event.payload);
      }),
    ];

    return () => {
      listeners.forEach((unlisten) => unlisten.then((fn) => fn()));
    };
  }, [loadModels]);

  const closePullDialog = useCallback(() => {
    setShowPullDialog(false);
    setNewModel('');
  }, []);

  const handlePullModel = useCallback(async () => {
    const trimmed = newModel.trim();
    if (!trimmed) return;

    setError(null);
    try {
      await invoke('pull_ollama_model', { modelName: trimmed });
      closePullDialog();
    } catch (err) {
      console.error('[ModelManager] Pull error:', err);
      setError(`Failed to pull model: ${err}`);
    }
  }, [newModel, closePullDialog]);

  const handleDeleteModel = useCallback(
    async (modelName: string) => {
      if (!confirm(`Delete model "${modelName}"?\n\nThis action cannot be undone.`)) {
        return;
      }

      setError(null);
      try {
        await invoke('delete_ollama_model', { modelName });
        loadModels();
      } catch (err) {
        console.error('[ModelManager] Delete error:', err);
        setError(`Failed to delete model: ${err}`);
      }
    },
    [loadModels],
  );

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter' && newModel.trim()) {
        handlePullModel();
      } else if (e.key === 'Escape') {
        closePullDialog();
      }
    },
    [newModel, handlePullModel, closePullDialog],
  );

  if (loading) {
    return (
      <div className="model-manager loading">
        <div className="spinner" />
        <span>Loading models...</span>
      </div>
    );
  }

  const isActive = (idx: number) => idx === 0;

  return (
    <div className="model-manager">
      {/* Header */}
      <div className="model-header">
        <span className="model-title">
          <Bot size={16} style={{ verticalAlign: 'middle' }} /> Installed Models
        </span>
        <button
          className="model-pull-btn"
          onClick={() => setShowPullDialog(true)}
          title="Pull new model from Ollama registry"
        >
          <Plus size={14} /> Pull New Model
        </button>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="model-error" onClick={() => setError(null)}>
          <AlertTriangle size={14} /> {error}
        </div>
      )}

      {/* Models List */}
      {models.length === 0 ? (
        <div className="model-empty">
          <p>No models installed yet.</p>
          <p>Click &quot;Pull New Model&quot; to download one.</p>
        </div>
      ) : (
        <div className="model-list">
          {models.map((model, idx) => (
            <div
              key={model.digest}
              className={`model-item ${isActive(idx) ? 'active' : ''}`}
            >
              <div className="model-info">
                <div className="model-name">
                  {isActive(idx) && (
                    <span className="model-badge">
                      <Star size={12} /> Active
                    </span>
                  )}
                  {model.name}
                </div>
                <div className="model-meta">
                  {model.size} &bull; {model.modified} &bull; {model.digest}
                </div>
              </div>
              <button
                className="model-delete-btn"
                onClick={() => handleDeleteModel(model.name)}
                disabled={isActive(idx)}
                title={isActive(idx) ? 'Cannot delete active model' : 'Delete model'}
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Pull Dialog */}
      {showPullDialog && (
        <div className="model-dialog-overlay" onClick={closePullDialog}>
          <div className="model-dialog" onClick={(e) => e.stopPropagation()}>
            <h3>Pull New Model</h3>
            <input
              type="text"
              placeholder="Model name (e.g., llama3.3, gemma2, qwen2.5)"
              value={newModel}
              onChange={(e) => setNewModel(e.target.value)}
              onKeyDown={handleKeyDown}
              autoFocus
            />
            <div className="model-dialog-actions">
              <button onClick={closePullDialog}>Cancel</button>
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
              {MODEL_PRESETS.map((preset) => (
                <button key={preset} onClick={() => setNewModel(preset)}>
                  {preset}
                </button>
              ))}
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
  );
}
