'use client';

/**
 * DesktopSetupWizard - First-run experience for Aurity Desktop
 *
 * Checks for required dependencies (Ollama, models) and guides users
 * through setup if needed. Only shows in desktop mode.
 *
 * Flow:
 * 1. Check Ollama connection (localhost:11434)
 * 2. Check if required model exists (qwen3:1.7b)
 * 3. Show setup instructions if missing
 * 4. Mark setup complete in localStorage
 */

import { useState, useEffect, useCallback } from 'react';
import { isDesktop } from '@/lib/config/deployment';
import { Button } from '@/components/ui/button';
import { CheckCircle, XCircle, Loader2, Download, Terminal, ExternalLink } from 'lucide-react';

const STORAGE_KEY = 'aurity_desktop_setup_complete';
const OLLAMA_HOST = 'http://localhost:11434';
const REQUIRED_MODEL = 'qwen3:1.7b';

interface SetupStatus {
  ollamaInstalled: boolean | null;
  ollamaRunning: boolean | null;
  modelAvailable: boolean | null;
  checking: boolean;
}

export function DesktopSetupWizard() {
  const [showWizard, setShowWizard] = useState(false);
  const [status, setStatus] = useState<SetupStatus>({
    ollamaInstalled: null,
    ollamaRunning: null,
    modelAvailable: null,
    checking: true,
  });
  const [pullingModel, setPullingModel] = useState(false);
  const [pullProgress, setPullProgress] = useState('');

  const checkOllama = useCallback(async () => {
    setStatus(prev => ({ ...prev, checking: true }));

    try {
      // Check if Ollama is running
      const tagsRes = await fetch(`${OLLAMA_HOST}/api/tags`, {
        signal: AbortSignal.timeout(3000),
      });

      if (!tagsRes.ok) {
        setStatus({
          ollamaInstalled: null,
          ollamaRunning: false,
          modelAvailable: false,
          checking: false,
        });
        return;
      }

      const tagsData = await tagsRes.json();
      const models = tagsData.models || [];
      const hasModel = models.some((m: { name: string }) =>
        m.name.startsWith(REQUIRED_MODEL.split(':')[0])
      );

      setStatus({
        ollamaInstalled: true,
        ollamaRunning: true,
        modelAvailable: hasModel,
        checking: false,
      });

      // If everything is ready, mark complete
      if (hasModel) {
        localStorage.setItem(STORAGE_KEY, 'true');
        setShowWizard(false);
      }
    } catch {
      // Ollama not running or not installed
      setStatus({
        ollamaInstalled: null,
        ollamaRunning: false,
        modelAvailable: false,
        checking: false,
      });
    }
  }, []);

  const pullModel = async () => {
    setPullingModel(true);
    setPullProgress('Iniciando descarga...');

    try {
      const res = await fetch(`${OLLAMA_HOST}/api/pull`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: REQUIRED_MODEL, stream: true }),
      });

      if (!res.body) {
        throw new Error('No response body');
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = decoder.decode(value);
        const lines = text.split('\n').filter(Boolean);

        for (const line of lines) {
          try {
            const json = JSON.parse(line);
            if (json.status) {
              if (json.completed && json.total) {
                const pct = Math.round((json.completed / json.total) * 100);
                setPullProgress(`${json.status}: ${pct}%`);
              } else {
                setPullProgress(json.status);
              }
            }
          } catch {
            // Ignore parse errors
          }
        }
      }

      setPullProgress('Modelo descargado!');
      await checkOllama();
    } catch (err) {
      setPullProgress(`Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setPullingModel(false);
    }
  };

  useEffect(() => {
    // Only show wizard in desktop mode
    if (!isDesktop()) {
      setShowWizard(false);
      return;
    }

    // Check if already completed
    const completed = localStorage.getItem(STORAGE_KEY);
    if (completed === 'true') {
      setShowWizard(false);
      return;
    }

    // Show wizard and check status
    setShowWizard(true);
    checkOllama();
  }, [checkOllama]);

  // Don't render if not in desktop mode or setup is complete
  if (!showWizard) return null;

  const allReady = status.ollamaRunning && status.modelAvailable;

  return (
    <div className="fixed inset-0 z-[100] bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl max-w-lg w-full p-6 space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="w-16 h-16 mx-auto bg-gradient-to-br from-purple-500 to-cyan-500 rounded-2xl flex items-center justify-center">
            <span className="text-3xl">🏥</span>
          </div>
          <h1 className="text-2xl font-bold text-white">Bienvenido a Aurity Desktop</h1>
          <p className="text-slate-400 text-sm">
            Configuremos tu asistente médico 100% offline
          </p>
        </div>

        {/* Status Checks */}
        <div className="space-y-3">
          {/* Ollama Status */}
          <div className="flex items-center justify-between p-3 bg-slate-800 rounded-lg">
            <div className="flex items-center gap-3">
              {status.checking ? (
                <Loader2 className="w-5 h-5 text-slate-400 animate-spin" />
              ) : status.ollamaRunning ? (
                <CheckCircle className="w-5 h-5 text-emerald-500" />
              ) : (
                <XCircle className="w-5 h-5 text-red-500" />
              )}
              <div>
                <p className="text-white font-medium">Ollama</p>
                <p className="text-slate-400 text-xs">Motor de IA local</p>
              </div>
            </div>
            {!status.ollamaRunning && !status.checking && (
              <a
                href="https://ollama.com/download"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-xs text-cyan-400 hover:text-cyan-300"
              >
                <Download className="w-4 h-4" />
                Instalar
                <ExternalLink className="w-3 h-3" />
              </a>
            )}
          </div>

          {/* Model Status */}
          <div className="flex items-center justify-between p-3 bg-slate-800 rounded-lg">
            <div className="flex items-center gap-3">
              {status.checking ? (
                <Loader2 className="w-5 h-5 text-slate-400 animate-spin" />
              ) : status.modelAvailable ? (
                <CheckCircle className="w-5 h-5 text-emerald-500" />
              ) : (
                <XCircle className="w-5 h-5 text-amber-500" />
              )}
              <div>
                <p className="text-white font-medium">Modelo {REQUIRED_MODEL}</p>
                <p className="text-slate-400 text-xs">~1.2 GB de descarga</p>
              </div>
            </div>
            {status.ollamaRunning && !status.modelAvailable && !status.checking && (
              <Button
                onClick={pullModel}
                disabled={pullingModel}
                size="sm"
                className="bg-purple-600 hover:bg-purple-500 text-white text-xs"
              >
                {pullingModel ? (
                  <Loader2 className="w-4 h-4 animate-spin mr-1" />
                ) : (
                  <Download className="w-4 h-4 mr-1" />
                )}
                Descargar
              </Button>
            )}
          </div>

          {/* Pull Progress */}
          {pullingModel && (
            <div className="p-3 bg-slate-800/50 rounded-lg">
              <p className="text-sm text-slate-300 font-mono">{pullProgress}</p>
            </div>
          )}
        </div>

        {/* Instructions if Ollama not running */}
        {!status.ollamaRunning && !status.checking && (
          <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700">
            <p className="text-sm text-slate-300 mb-3">
              Para usar Aurity Desktop, necesitas Ollama corriendo:
            </p>
            <div className="space-y-2 font-mono text-xs">
              <div className="flex items-center gap-2 text-slate-400">
                <Terminal className="w-4 h-4" />
                <code className="bg-slate-900 px-2 py-1 rounded">brew install ollama</code>
              </div>
              <div className="flex items-center gap-2 text-slate-400">
                <Terminal className="w-4 h-4" />
                <code className="bg-slate-900 px-2 py-1 rounded">ollama serve</code>
              </div>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3">
          <Button
            onClick={checkOllama}
            variant="outline"
            className="flex-1 border-slate-600 text-slate-300 hover:bg-slate-800"
            disabled={status.checking}
          >
            {status.checking ? (
              <Loader2 className="w-4 h-4 animate-spin mr-2" />
            ) : null}
            Verificar de nuevo
          </Button>

          {allReady && (
            <Button
              onClick={() => {
                localStorage.setItem(STORAGE_KEY, 'true');
                setShowWizard(false);
              }}
              className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white"
            >
              <CheckCircle className="w-4 h-4 mr-2" />
              Comenzar
            </Button>
          )}
        </div>

        {/* Skip Option */}
        <p className="text-center text-xs text-slate-500">
          <button
            onClick={() => {
              localStorage.setItem(STORAGE_KEY, 'skipped');
              setShowWizard(false);
            }}
            className="hover:text-slate-400 underline"
          >
            Omitir configuración (avanzado)
          </button>
        </p>
      </div>
    </div>
  );
}
