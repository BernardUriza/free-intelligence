'use client';

/**
 * DesktopSetupWizard - First-run experience for Aurity Desktop
 *
 * Checks for required dependencies and guides users through setup.
 * Only shows in desktop mode.
 *
 * Flow:
 * 1. Install FI Monitor - REQUIRED (cloud connectivity)
 * 2. Check WSL status (Windows only) - Required for backend
 * 3. Check backend health (via WSL on Windows)
 * 4. Check Ollama connection (localhost:11434)
 * 5. Check if required model exists (qwen3:1.7b)
 * 6. Mark setup complete in localStorage
 *
 * Note: License check happens AFTER wizard completion, when user attempts login.
 */

import { useState, useEffect, useCallback } from 'react';
import { isDesktop } from '@/lib/config/deployment';
import { Button } from '@/components/ui/button';
import { 
  CheckCircle, XCircle, Loader2, Download, Terminal, 
  ExternalLink, Cloud, CloudOff, Server, Monitor, Settings 
} from 'lucide-react';

const STORAGE_KEY = 'aurity_desktop_setup_complete';
const OLLAMA_HOST = 'http://localhost:11434';
const REQUIRED_MODEL = 'qwen3:1.7b';

// Export function to reset wizard (for use in settings/menu)
export function resetDesktopSetupWizard() {
  localStorage.removeItem(STORAGE_KEY);
  // Force page reload to show wizard
  window.location.reload();
}

// Detect if running on Windows
const isWindows = typeof navigator !== 'undefined' && navigator.platform?.toLowerCase().includes('win');

// Tauri invoke helper - only available in desktop mode
const invokeTauri = async <T,>(cmd: string, args?: Record<string, unknown>): Promise<T | null> => {
  console.log(`[DesktopWizard] Invoking Tauri command: ${cmd}`, args);
  if (typeof window !== 'undefined' && '__TAURI__' in window) {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      const result = await invoke<T>(cmd, args);
      console.log(`[DesktopWizard] Command ${cmd} result:`, result);
      return result;
    } catch (error) {
      console.error(`[DesktopWizard] Command ${cmd} failed:`, error);
      throw error; // Re-throw to let caller handle it
    }
  }
  console.warn(`[DesktopWizard] Tauri not available, command ${cmd} skipped`);
  return null;
};

interface PythonStatus {
  installed: boolean;
  version: string | null;
  pip_available: boolean;
  fi_monitor_deps_installed: boolean;
}

interface FiMonitorStatus {
  installed: boolean;
  running: boolean;
  version: string | null;
  install_path: string | null;
}

interface WslStatus {
  installed: boolean;
  distro: string | null;
  version: number | null;
  backend_installed: boolean;
  backend_running: boolean;
}

interface SetupStatus {
  // WSL & Backend (Windows only)
  wslInstalled: boolean | null;
  wslDistro: string | null;
  backendInstalled: boolean | null;
  backendRunning: boolean | null;
  // Ollama
  ollamaInstalled: boolean | null;
  ollamaRunning: boolean | null;
  modelAvailable: boolean | null;
  // FI Monitor
  fiMonitorInstalled: boolean | null;
  fiMonitorRunning: boolean | null;
  // State
  checking: boolean;
}

export function DesktopSetupWizard() {
  const [showWizard, setShowWizard] = useState(false);
  const [status, setStatus] = useState<SetupStatus>({
    wslInstalled: null,
    wslDistro: null,
    backendInstalled: null,
    backendRunning: null,
    ollamaInstalled: null,
    ollamaRunning: null,
    modelAvailable: null,
    fiMonitorInstalled: null,
    fiMonitorRunning: null,
    checking: true,
  });
  const [pullingModel, setPullingModel] = useState(false);
  const [pullProgress, setPullProgress] = useState('');
  const [installingFiMonitor, setInstallingFiMonitor] = useState(false);
  const [fiMonitorProgress, setFiMonitorProgress] = useState('');
  const [installingWsl, setInstallingWsl] = useState(false);
  const [wslProgress, setWslProgress] = useState('');
  const [settingUpBackend, setSettingUpBackend] = useState(false);
  const [backendProgress, setBackendProgress] = useState('');
  const [pythonStatus, setPythonStatus] = useState<PythonStatus | null>(null);

  // Check WSL status (Windows only)
  const checkWsl = useCallback(async () => {
    if (!isWindows) {
      // On non-Windows, WSL is not needed
      setStatus(prev => ({
        ...prev,
        wslInstalled: true, // Mark as "not needed"
        backendInstalled: true,
        backendRunning: true,
      }));
      return;
    }

    try {
      const wslStatus = await invokeTauri<WslStatus>('check_wsl_status');
      if (wslStatus) {
        setStatus(prev => ({
          ...prev,
          wslInstalled: wslStatus.installed,
          wslDistro: wslStatus.distro,
          backendInstalled: wslStatus.backend_installed,
          backendRunning: wslStatus.backend_running,
        }));
      }
    } catch (err) {
      console.error('Failed to check WSL status:', err);
      setStatus(prev => ({
        ...prev,
        wslInstalled: false,
        backendInstalled: false,
        backendRunning: false,
      }));
    }
  }, []);

  // Install WSL (requires admin)
  const installWsl = async () => {
    setInstallingWsl(true);
    setWslProgress('Iniciando instalación de WSL...');

    try {
      const result = await invokeTauri<string>('install_wsl');
      setWslProgress(result || 'Instalación iniciada. Puede requerir reinicio.');
      
      // Recheck after a delay
      setTimeout(() => {
        checkWsl();
        setInstallingWsl(false);
      }, 5000);
    } catch (err) {
      setWslProgress(`Error: ${err instanceof Error ? err.message : 'Unknown'}`);
      setInstallingWsl(false);
    }
  };

  // Setup backend in WSL
  const setupBackend = async () => {
    setSettingUpBackend(true);
    setBackendProgress('Configurando backend...');

    try {
      // Listen for progress events
      const { listen } = await import('@tauri-apps/api/event');
      const unlisten = await listen<string>('wsl-setup-progress', (event) => {
        setBackendProgress(event.payload);
      });

      const result = await invokeTauri<string>('setup_wsl_backend');
      
      unlisten();

      if (result) {
        setBackendProgress('¡Backend configurado!');
        await checkWsl();
      } else {
        setBackendProgress('Error en configuración');
      }
    } catch (err) {
      setBackendProgress(`Error: ${err instanceof Error ? err.message : 'Unknown'}`);
    } finally {
      setSettingUpBackend(false);
    }
  };

  // Start backend in WSL
  const startBackend = async () => {
    setBackendProgress('Iniciando backend...');
    try {
      await invokeTauri<string>('start_wsl_backend');
      setBackendProgress('Backend iniciando...');
      
      // Check health after delay
      setTimeout(async () => {
        const healthy = await invokeTauri<boolean>('check_wsl_backend_health');
        if (healthy) {
          setBackendProgress('¡Backend corriendo!');
          setStatus(prev => ({ ...prev, backendRunning: true }));
        } else {
          setBackendProgress('Backend iniciando (puede tardar)...');
        }
      }, 3000);
    } catch (err) {
      setBackendProgress(`Error: ${err instanceof Error ? err.message : 'Unknown'}`);
    }
  };

  // Check FI Monitor status via Tauri command
  const checkFiMonitor = useCallback(async () => {
    try {
      const fiStatus = await invokeTauri<FiMonitorStatus>('check_fi_monitor_installed');
      if (fiStatus) {
        setStatus(prev => ({
          ...prev,
          fiMonitorInstalled: fiStatus.installed,
          fiMonitorRunning: fiStatus.running,
        }));
      }
    } catch {
      // FI Monitor check failed - not critical, just mark as not installed
      setStatus(prev => ({
        ...prev,
        fiMonitorInstalled: false,
        fiMonitorRunning: false,
      }));
    }
  }, []);

  // Install FI Monitor via Tauri command
  const installFiMonitor = async () => {
    console.log('[DesktopWizard] Starting FI Monitor installation...');
    setInstallingFiMonitor(true);
    setFiMonitorProgress('Iniciando instalación...');

    try {
      // Listen for progress events
      console.log('[DesktopWizard] Setting up event listeners...');
      const { listen } = await import('@tauri-apps/api/event');
      
      const unlisten = await listen<{ percentage: number }>('fi-monitor-download-progress', (event) => {
        console.log('[DesktopWizard] Download progress:', event.payload);
        setFiMonitorProgress(`Descargando: ${Math.round(event.payload.percentage)}%`);
      });

      const unlisten2 = await listen<string>('fi-monitor-install-status', (event) => {
        console.log('[DesktopWizard] Install status:', event.payload);
        setFiMonitorProgress(event.payload);
      });

      console.log('[DesktopWizard] Calling install_fi_monitor_full...');
      // Run full install
      const result = await invokeTauri<boolean>('install_fi_monitor_full');
      console.log('[DesktopWizard] Install result:', result);
      
      unlisten();
      unlisten2();

      if (result) {
        setFiMonitorProgress('¡FI Monitor instalado!');
        await checkFiMonitor();
      } else {
        setFiMonitorProgress('Error en instalación (result was null/false)');
      }
    } catch (err) {
      console.error('[DesktopWizard] FI Monitor install error:', err);
      setFiMonitorProgress(`Error: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setInstallingFiMonitor(false);
    }
  };

  // Launch FI Monitor if installed but not running
  const launchFiMonitor = async () => {
    try {
      await invokeTauri('launch_fi_monitor');
      // Wait a bit and recheck
      setTimeout(() => checkFiMonitor(), 2000);
    } catch (err) {
      console.error('Failed to launch FI Monitor:', err);
    }
  };

  const checkOllama = useCallback(async () => {
    setStatus(prev => ({ ...prev, checking: true }));

    // First check WSL on Windows
    await checkWsl();

    try {
      // Check if Ollama is running
      const tagsRes = await fetch(`${OLLAMA_HOST}/api/tags`, {
        signal: AbortSignal.timeout(3000),
      });

      if (!tagsRes.ok) {
        setStatus(prev => ({
          ...prev,
          ollamaInstalled: null,
          ollamaRunning: false,
          modelAvailable: false,
          checking: false,
        }));
        return;
      }

      const tagsData = await tagsRes.json();
      const models = tagsData.models || [];
      const hasModel = models.some((m: { name: string }) =>
        m.name.startsWith(REQUIRED_MODEL.split(':')[0])
      );

      setStatus(prev => ({
        ...prev,
        ollamaInstalled: true,
        ollamaRunning: true,
        modelAvailable: hasModel,
        checking: false,
      }));

      // Also check FI Monitor status
      await checkFiMonitor();

      // If everything is ready (including backend on Windows), mark complete
      if (hasModel && (!isWindows || status.backendRunning)) {
        localStorage.setItem(STORAGE_KEY, 'true');
        setShowWizard(false);
      }
    } catch {
      // Ollama not running or not installed
      setStatus(prev => ({
        ...prev,
        ollamaInstalled: null,
        ollamaRunning: false,
        modelAvailable: false,
        checking: false,
      }));
      // Still check FI Monitor
      await checkFiMonitor();
    }
  }, [checkFiMonitor, checkWsl, status.backendRunning]);

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

  // Check Python installation status
  useEffect(() => {
    const checkPython = async () => {
      if (typeof window !== 'undefined' && '__TAURI__' in window) {
        try {
          const status = await invokeTauri<PythonStatus>('check_python_installation');
          if (status) {
            setPythonStatus(status);
          }
        } catch (err) {
          console.error('[DesktopWizard] Failed to check Python status:', err);
        }
      }
    };
    checkPython();
  }, []);

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

  const allReady = status.fiMonitorInstalled && status.ollamaRunning && status.modelAvailable &&
    (!isWindows || status.backendRunning);

  return (
    <div className="fixed inset-0 z-[100] bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl max-w-lg w-full p-6 space-y-6 my-4">
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

          {/* FI Monitor Status - Cloud Connectivity (REQUIRED - STEP 1) */}
          <div className="flex items-center justify-between p-3 bg-cyan-900/20 rounded-lg border-2 border-cyan-600">
            <div className="flex items-center gap-3">
              {status.checking ? (
                <Loader2 className="w-5 h-5 text-slate-400 animate-spin" />
              ) : status.fiMonitorInstalled && status.fiMonitorRunning ? (
                <Cloud className="w-5 h-5 text-cyan-500" />
              ) : status.fiMonitorInstalled ? (
                <CloudOff className="w-5 h-5 text-amber-500" />
              ) : (
                <CloudOff className="w-5 h-5 text-slate-500" />
              )}
              <div>
                <p className="text-white font-medium">
                  FI Monitor
                  <span className="ml-2 text-xs text-cyan-400 font-bold">PASO 1 - Requerido</span>
                </p>
                <p className="text-slate-300 text-xs">
                  {status.fiMonitorRunning
                    ? '✅ Conectividad cloud activa'
                    : status.fiMonitorInstalled
                      ? '⚠️ Instalado pero no corriendo'
                      : 'Conexión remota a tu IA local'}
                </p>
              </div>
            </div>
            {!status.checking && (
              <>
                {!status.fiMonitorInstalled && (
                  <Button
                    onClick={installFiMonitor}
                    disabled={installingFiMonitor}
                    size="sm"
                    className="bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold"
                  >
                    {installingFiMonitor ? (
                      <Loader2 className="w-4 h-4 animate-spin mr-1" />
                    ) : (
                      <Download className="w-4 h-4 mr-1" />
                    )}
                    Instalar Ahora
                  </Button>
                )}
                {status.fiMonitorInstalled && !status.fiMonitorRunning && (
                  <Button
                    onClick={launchFiMonitor}
                    size="sm"
                    className="bg-cyan-600 hover:bg-cyan-500 text-white text-xs"
                  >
                    <Cloud className="w-4 h-4 mr-1" />
                    Iniciar
                  </Button>
                )}
                {status.fiMonitorInstalled && status.fiMonitorRunning && (
                  <CheckCircle className="w-5 h-5 text-cyan-500" />
                )}
              </>
            )}
          </div>

          {/* FI Monitor Install Progress */}
          {installingFiMonitor && (
            <div className="p-3 bg-cyan-900/20 rounded-lg border border-cyan-800">
              <p className="text-sm text-cyan-300 font-mono">{fiMonitorProgress}</p>
            </div>
          )}

          {/* WSL Status (Windows only) */}
          {isWindows && (
            <>
              <div className="flex items-center justify-between p-3 bg-slate-800 rounded-lg">
                <div className="flex items-center gap-3">
                  {status.checking ? (
                    <Loader2 className="w-5 h-5 text-slate-400 animate-spin" />
                  ) : status.wslInstalled ? (
                    <CheckCircle className="w-5 h-5 text-emerald-500" />
                  ) : (
                    <XCircle className="w-5 h-5 text-red-500" />
                  )}
                  <div>
                    <p className="text-white font-medium">WSL (Windows Subsystem for Linux)</p>
                    <p className="text-slate-400 text-xs">
                      {status.wslDistro 
                        ? `Distro: ${status.wslDistro}` 
                        : 'Requerido para el backend'}
                    </p>
                  </div>
                </div>
                {!status.wslInstalled && !status.checking && (
                  <Button
                    onClick={installWsl}
                    disabled={installingWsl}
                    size="sm"
                    className="bg-blue-600 hover:bg-blue-500 text-white text-xs"
                  >
                    {installingWsl ? (
                      <Loader2 className="w-4 h-4 animate-spin mr-1" />
                    ) : (
                      <Download className="w-4 h-4 mr-1" />
                    )}
                    Instalar WSL
                  </Button>
                )}
              </div>

              {/* WSL Install Progress */}
              {installingWsl && (
                <div className="p-3 bg-blue-900/20 rounded-lg border border-blue-800">
                  <p className="text-sm text-blue-300 font-mono">{wslProgress}</p>
                </div>
              )}

              {/* Backend Status (WSL) */}
              {status.wslInstalled && (
                <div className="flex items-center justify-between p-3 bg-slate-800 rounded-lg">
                  <div className="flex items-center gap-3">
                    {status.checking ? (
                      <Loader2 className="w-5 h-5 text-slate-400 animate-spin" />
                    ) : status.backendRunning ? (
                      <CheckCircle className="w-5 h-5 text-emerald-500" />
                    ) : status.backendInstalled ? (
                      <Settings className="w-5 h-5 text-amber-500" />
                    ) : (
                      <Server className="w-5 h-5 text-slate-500" />
                    )}
                    <div>
                      <p className="text-white font-medium">Backend FastAPI</p>
                      <p className="text-slate-400 text-xs">
                        {status.backendRunning 
                          ? 'Corriendo en puerto 7001'
                          : status.backendInstalled 
                            ? 'Instalado, listo para iniciar'
                            : 'Se ejecuta en WSL'}
                      </p>
                    </div>
                  </div>
                  {!status.checking && (
                    <>
                      {!status.backendInstalled && (
                        <Button
                          onClick={setupBackend}
                          disabled={settingUpBackend}
                          size="sm"
                          className="bg-purple-600 hover:bg-purple-500 text-white text-xs"
                        >
                          {settingUpBackend ? (
                            <Loader2 className="w-4 h-4 animate-spin mr-1" />
                          ) : (
                            <Settings className="w-4 h-4 mr-1" />
                          )}
                          Configurar
                        </Button>
                      )}
                      {status.backendInstalled && !status.backendRunning && (
                        <Button
                          onClick={startBackend}
                          size="sm"
                          className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs"
                        >
                          <Server className="w-4 h-4 mr-1" />
                          Iniciar
                        </Button>
                      )}
                    </>
                  )}
                </div>
              )}

              {/* Backend Setup Progress */}
              {(settingUpBackend || backendProgress) && (
                <div className="p-3 bg-purple-900/20 rounded-lg border border-purple-800">
                  <p className="text-sm text-purple-300 font-mono">{backendProgress}</p>
                </div>
              )}

              {/* Divider */}
              <div className="border-t border-slate-700 my-2" />
            </>
          )}

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

          {/* Python 3.14 Runtime Status */}
          {pythonStatus && (
            <div className="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
              <div className="flex items-center gap-2">
                <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-500" />
                <span className="font-medium text-green-800 dark:text-green-300">Python 3.14 Runtime</span>
              </div>
              <p className="text-sm text-green-700 dark:text-green-400 mt-1">
                ✅ {pythonStatus.version || 'Python installed'}
                {pythonStatus.fi_monitor_deps_installed && ' (fi-monitor dependencies ready)'}
              </p>
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
