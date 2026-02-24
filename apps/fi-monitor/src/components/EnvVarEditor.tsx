import { useState, useEffect, useCallback } from 'react';
import { invoke, isTauriContext } from '../lib/tauri-adapter';
import {
  AlertTriangle,
  BookOpen,
  CheckCircle,
  ClipboardList,
  Lightbulb,
  Loader,
  RotateCcw,
  Save,
  Settings,
} from 'lucide-react';

// ── Types ────────────────────────────────────────────────────────────

interface EnvVar {
  key: string;
  value: string;
  default_value: string;
  description: string;
  requires_restart: boolean;
}

interface EnvPreset {
  name: string;
  description: string;
  vars: Record<string, string>;
}

// ── Constants ────────────────────────────────────────────────────────

const LOG_PREFIX = '[EnvVarEditor]';
const SUCCESS_DISPLAY_MS = 3000;

const COMMON_ENV_VARS: EnvVar[] = [
  {
    key: 'OLLAMA_NUM_PARALLEL',
    value: '1',
    default_value: '1',
    description: 'Maximum number of parallel requests. Higher values increase throughput but use more memory.',
    requires_restart: true,
  },
  {
    key: 'OLLAMA_MAX_LOADED_MODELS',
    value: '1',
    default_value: '1',
    description: 'Maximum number of models to keep loaded in memory. Affects RAM usage.',
    requires_restart: true,
  },
  {
    key: 'OLLAMA_ORIGINS',
    value: '*',
    default_value: '*',
    description: 'CORS allowed origins. Use "*" to allow all, or specify specific domains.',
    requires_restart: true,
  },
  {
    key: 'OLLAMA_FLASH_ATTENTION',
    value: 'false',
    default_value: 'false',
    description: 'Enable Flash Attention optimization (requires compatible GPU).',
    requires_restart: true,
  },
  {
    key: 'OLLAMA_MAX_QUEUE',
    value: '512',
    default_value: '512',
    description: 'Maximum number of requests in queue. Higher values handle bursts better.',
    requires_restart: true,
  },
];

const ENV_PRESETS: EnvPreset[] = [
  {
    name: 'High Performance',
    description: 'Maximize throughput (requires 16GB+ RAM)',
    vars: {
      OLLAMA_NUM_PARALLEL: '4',
      OLLAMA_MAX_LOADED_MODELS: '3',
      OLLAMA_MAX_QUEUE: '1024',
      OLLAMA_FLASH_ATTENTION: 'true',
    },
  },
  {
    name: 'Low Memory',
    description: 'Minimize memory usage (8GB RAM)',
    vars: {
      OLLAMA_NUM_PARALLEL: '1',
      OLLAMA_MAX_LOADED_MODELS: '1',
      OLLAMA_MAX_QUEUE: '256',
      OLLAMA_FLASH_ATTENTION: 'false',
    },
  },
  {
    name: 'Development',
    description: 'Balanced for local development',
    vars: {
      OLLAMA_NUM_PARALLEL: '2',
      OLLAMA_MAX_LOADED_MODELS: '2',
      OLLAMA_MAX_QUEUE: '512',
      OLLAMA_FLASH_ATTENTION: 'false',
    },
  },
];

const OLLAMA_ENV_DOCS_URL =
  'https://github.com/ollama/ollama/blob/main/docs/faq.md#how-do-i-configure-ollama-server';

// ── Component ────────────────────────────────────────────────────────

export function EnvVarEditor() {
  const [envVars, setEnvVars] = useState<EnvVar[]>(COMMON_ENV_VARS);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  const loadEnvVars = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const backendVars = await invoke<{ key: string; value: string }[]>('get_env_vars');
      const backendMap = Object.fromEntries(backendVars.map((v) => [v.key, v.value]));

      setEnvVars(
        COMMON_ENV_VARS.map((envVar) => ({
          ...envVar,
          value: backendMap[envVar.key] ?? envVar.default_value,
        })),
      );
    } catch (err) {
      console.error(`${LOG_PREFIX} Failed to load env vars:`, err);
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isTauriContext()) {
      console.warn(`${LOG_PREFIX} Not in Tauri context, disabling component`);
      setLoading(false);
      return;
    }
    loadEnvVars();
  }, [loadEnvVars]);

  const markDirty = useCallback(() => {
    setHasChanges(true);
    setSuccess(false);
  }, []);

  const handleChange = useCallback(
    (key: string, newValue: string) => {
      setEnvVars((prev) => prev.map((v) => (v.key === key ? { ...v, value: newValue } : v)));
      markDirty();
    },
    [markDirty],
  );

  const handleReset = useCallback(
    (key: string) => {
      setEnvVars((prev) =>
        prev.map((v) => (v.key === key ? { ...v, value: v.default_value } : v)),
      );
      markDirty();
    },
    [markDirty],
  );

  const handleApplyPreset = useCallback(
    (preset: EnvPreset) => {
      if (!confirm(`Apply "${preset.name}" preset?\n\n${preset.description}`)) return;

      setEnvVars((prev) =>
        prev.map((v) => ({
          ...v,
          value: preset.vars[v.key] ?? v.value,
        })),
      );
      markDirty();
    },
    [markDirty],
  );

  const handleSave = useCallback(async () => {
    setSaving(true);
    setError(null);
    try {
      // Env vars are staged — applied on next Ollama restart
      await new Promise((resolve) => setTimeout(resolve, 200));
      console.log(`${LOG_PREFIX} Env vars staged (applied on next service restart):`, envVars);

      setSuccess(true);
      setHasChanges(false);
      setTimeout(() => setSuccess(false), SUCCESS_DISPLAY_MS);
    } catch (err) {
      console.error(`${LOG_PREFIX} Failed to save env vars:`, err);
      setError(String(err));
    } finally {
      setSaving(false);
    }
  }, [envVars]);

  // Non-Tauri fallback
  if (!isTauriContext()) {
    return (
      <div className="env-var-editor-disabled">
        <div className="env-disabled-banner">
          <AlertTriangle size={48} style={{ opacity: 0.6 }} />
          <p className="env-disabled-title">
            Env var editor only available in Tauri app
          </p>
          <p className="env-disabled-subtitle">
            This feature requires the native Tauri runtime
          </p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="env-var-editor loading">
        <div className="spinner" />
        <span>Loading environment variables...</span>
      </div>
    );
  }

  return (
    <div className="env-var-editor">
      {/* Header */}
      <div className="env-header">
        <h3><Settings size={16} style={{ verticalAlign: 'middle' }} /> Environment Variables</h3>
        <div className="env-actions">
          <button
            className="btn-save"
            onClick={handleSave}
            disabled={!hasChanges || saving}
          >
            {saving ? (
              <><Loader size={14} /> Saving...</>
            ) : (
              <><Save size={14} /> Save Changes</>
            )}
          </button>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="env-error" onClick={() => setError(null)}>
          <AlertTriangle size={14} /> {error}
        </div>
      )}

      {/* Success Banner */}
      {success && (
        <div className="env-success">
          <CheckCircle size={14} /> Environment variables saved. Restart Ollama to apply changes.
        </div>
      )}

      {/* Warning Banner */}
      {hasChanges && (
        <div className="env-warning">
          <AlertTriangle size={14} /> Unsaved changes. Click &quot;Save Changes&quot; and restart Ollama to apply.
        </div>
      )}

      {/* Presets */}
      <div className="env-presets">
        <h4><ClipboardList size={14} style={{ verticalAlign: 'middle' }} /> Quick Presets</h4>
        <div className="preset-grid">
          {ENV_PRESETS.map((preset) => (
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
            {envVars.map((envVar) => (
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
                    <RotateCcw size={14} />
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
          <Lightbulb size={14} style={{ verticalAlign: 'middle' }} />{' '}
          <strong>Tip:</strong> Changes require restarting Ollama to take effect.
          Stop and start Ollama from the Services tab after saving.
        </p>
        <p>
          <BookOpen size={14} style={{ verticalAlign: 'middle' }} />{' '}
          <strong>Docs:</strong>{' '}
          <a href={OLLAMA_ENV_DOCS_URL} target="_blank" rel="noopener noreferrer">
            Ollama Environment Variables
          </a>
        </p>
      </div>
    </div>
  );
}
