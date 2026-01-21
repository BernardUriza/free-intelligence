'use client';

/**
 * DesktopSetupWizard - Simplified first-run experience for Aurity Desktop
 *
 * Only checks for FI Monitor installation.
 * FI Monitor handles Python + Ollama setup in its own wizard.
 *
 * Flow:
 * 1. CHECKING → Verify FI Monitor installed
 * 2. NOT_INSTALLED → Offer to install FI Monitor
 * 3. INSTALLING → Download/install FI Monitor with progress
 * 4. READY → Launch FI Monitor (which shows its own Python/Ollama wizard)
 */

import { useState, useEffect } from 'react';
import { isDesktop } from '@/lib/config/deployment';
import { Button } from '@/components/ui/button';
import { CheckCircle, Loader2, Download, Cloud } from 'lucide-react';

const STORAGE_KEY = 'aurity_desktop_setup_complete';

// Export function to reset wizard (for use in settings/menu)
export function resetDesktopSetupWizard() {
  localStorage.removeItem(STORAGE_KEY);
  window.location.reload();
}

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
      throw error;
    }
  }
  console.warn(`[DesktopWizard] Tauri not available, command ${cmd} skipped`);
  return null;
};

interface FiMonitorStatus {
  installed: boolean;
  running: boolean;
  version: string | null;
  install_path: string | null;
}

type Screen = 'CHECKING' | 'NOT_INSTALLED' | 'INSTALLING' | 'READY' | 'ERROR';

export function DesktopSetupWizard() {
  const [showWizard, setShowWizard] = useState(false);
  const [screen, setScreen] = useState<Screen>('CHECKING');
  const [progress, setProgress] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Check if setup already completed
  useEffect(() => {
    if (!isDesktop()) {
      setShowWizard(false);
      return;
    }

    const setupComplete = localStorage.getItem(STORAGE_KEY);
    if (setupComplete === 'true') {
      setShowWizard(false);
      return;
    }

    // Setup not complete - show wizard and check FI Monitor
    setShowWizard(true);
    checkFiMonitor();
  }, []);

  // Check if FI Monitor is installed
  const checkFiMonitor = async () => {
    setScreen('CHECKING');

    try {
      const status = await invokeTauri<FiMonitorStatus>('check_fi_monitor_installed');

      if (status?.installed && status?.running) {
        // FI Monitor is installed and running - setup complete!
        setScreen('READY');
        markSetupComplete();
      } else if (status?.installed) {
        // Installed but not running - launch it
        await launchFiMonitor();
        setScreen('READY');
        markSetupComplete();
      } else {
        // Not installed - offer to install
        setScreen('NOT_INSTALLED');
      }
    } catch (err) {
      console.error('[DesktopWizard] Failed to check FI Monitor:', err);
      setScreen('NOT_INSTALLED');
    }
  };

  // Install FI Monitor
  const installFiMonitor = async () => {
    setScreen('INSTALLING');
    setProgress(['Descargando FI Monitor...']);

    try {
      // Listen for progress events
      if (typeof window !== 'undefined' && '__TAURI__' in window) {
        const { listen } = await import('@tauri-apps/api/event');

        const unlisten = await listen<string>('fi-monitor-install-status', (event) => {
          setProgress(prev => [...prev, event.payload]);
        });

        // Start installation
        const result = await invokeTauri<boolean>('install_fi_monitor_full');

        unlisten();

        if (result) {
          setProgress(prev => [...prev, '✅ FI Monitor instalado correctamente']);

          // Launch FI Monitor (it will show its own wizard for Python + Ollama)
          setTimeout(async () => {
            await launchFiMonitor();
            setScreen('READY');
            markSetupComplete();
          }, 2000);
        } else {
          setError('La instalación falló. Por favor intenta de nuevo.');
          setScreen('ERROR');
        }
      }
    } catch (err) {
      console.error('[DesktopWizard] Installation failed:', err);
      setError(err instanceof Error ? err.message : 'Error desconocido');
      setScreen('ERROR');
    }
  };

  // Launch FI Monitor application
  const launchFiMonitor = async () => {
    try {
      await invokeTauri<boolean>('launch_fi_monitor');
      console.log('[DesktopWizard] FI Monitor launched');
    } catch (err) {
      console.error('[DesktopWizard] Failed to launch FI Monitor:', err);
    }
  };

  // Skip installation (degraded mode)
  const skipInstallation = () => {
    markSetupComplete();
    setShowWizard(false);
  };

  // Retry installation
  const retryInstallation = () => {
    setError(null);
    setProgress([]);
    checkFiMonitor();
  };

  // Mark setup as complete in localStorage
  const markSetupComplete = () => {
    localStorage.setItem(STORAGE_KEY, 'true');
    setTimeout(() => setShowWizard(false), 2000);
  };

  if (!showWizard) {
    return null;
  }

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

        {/* Content by screen */}
        {screen === 'CHECKING' && <CheckingScreen />}
        {screen === 'NOT_INSTALLED' && <NotInstalledScreen onInstall={installFiMonitor} onSkip={skipInstallation} />}
        {screen === 'INSTALLING' && <InstallingScreen progress={progress} />}
        {screen === 'READY' && <ReadyScreen />}
        {screen === 'ERROR' && <ErrorScreen error={error} onRetry={retryInstallation} onSkip={skipInstallation} />}

      </div>
    </div>
  );
}

// CHECKING - Verifying FI Monitor
function CheckingScreen() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-center gap-3 p-4 bg-slate-800 rounded-lg">
        <Loader2 className="w-6 h-6 text-cyan-500 animate-spin" />
        <div>
          <p className="text-white font-medium">Verificando FI Monitor...</p>
          <p className="text-slate-400 text-sm">Un momento por favor</p>
        </div>
      </div>
    </div>
  );
}

// NOT_INSTALLED - Offer to install FI Monitor
interface NotInstalledScreenProps {
  onInstall: () => void;
  onSkip: () => void;
}

function NotInstalledScreen({ onInstall, onSkip }: NotInstalledScreenProps) {
  return (
    <div className="space-y-4">
      <div className="p-4 bg-cyan-900/20 rounded-lg border border-cyan-700">
        <div className="flex items-center gap-3 mb-3">
          <Cloud className="w-6 h-6 text-cyan-500" />
          <div>
            <p className="text-white font-medium">FI Monitor Requerido</p>
            <p className="text-slate-300 text-sm">Conectividad remota a tu IA local</p>
          </div>
        </div>

        <div className="space-y-2 text-sm text-slate-300">
          <p>FI Monitor gestiona:</p>
          <ul className="list-disc list-inside space-y-1 ml-2">
            <li>Instalación automática de Python 3.14</li>
            <li>Instalación automática de Ollama</li>
            <li>Túnel seguro para acceso remoto</li>
          </ul>
        </div>
      </div>

      <div className="flex gap-3">
        <Button
          onClick={onInstall}
          className="flex-1 bg-cyan-600 hover:bg-cyan-500 text-white"
        >
          <Download className="w-4 h-4 mr-2" />
          Instalar Ahora
        </Button>
        <Button
          onClick={onSkip}
          variant="outline"
          className="border-slate-600 text-slate-300 hover:bg-slate-800"
        >
          Omitir
        </Button>
      </div>

      <p className="text-xs text-slate-500 text-center">
        ⚠️ Sin FI Monitor, algunas funciones estarán deshabilitadas
      </p>
    </div>
  );
}

// INSTALLING - Installing FI Monitor with progress
interface InstallingScreenProps {
  progress: string[];
}

function InstallingScreen({ progress }: InstallingScreenProps) {
  const progressPercent = Math.min(100, (progress.length / 5) * 100);

  return (
    <div className="space-y-4">
      <div className="space-y-3">
        <div className="flex items-center gap-3">
          <Loader2 className="w-6 h-6 text-cyan-500 animate-spin" />
          <div>
            <p className="text-white font-medium">Instalando FI Monitor...</p>
            <p className="text-slate-400 text-sm">Por favor espera (1-2 minutos)</p>
          </div>
        </div>

        {/* Progress bar */}
        <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-cyan-600 to-cyan-400 transition-all duration-300"
            style={{ width: `${progressPercent}%` }}
          />
        </div>

        {/* Progress log */}
        <div className="max-h-48 overflow-y-auto p-3 bg-slate-800 rounded-lg border border-slate-700">
          {progress.map((msg, i) => (
            <div
              key={i}
              className={`text-xs font-mono mb-1 ${
                msg.includes('✅') || msg.includes('✓')
                  ? 'text-emerald-400'
                  : 'text-slate-300'
              }`}
            >
              {msg}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// READY - FI Monitor installed successfully
function ReadyScreen() {
  return (
    <div className="space-y-4 text-center">
      <div className="w-16 h-16 mx-auto bg-emerald-500/20 rounded-full flex items-center justify-center">
        <CheckCircle className="w-10 h-10 text-emerald-500" />
      </div>

      <div>
        <h2 className="text-xl font-bold text-white mb-2">¡Todo Listo!</h2>
        <p className="text-slate-300 text-sm">
          FI Monitor instalado correctamente
        </p>
      </div>

      <div className="p-4 bg-cyan-900/20 rounded-lg border border-cyan-700">
        <p className="text-sm text-cyan-300">
          🚀 Abriendo FI Monitor...
        </p>
        <p className="text-xs text-slate-400 mt-2">
          FI Monitor configurará Python y Ollama automáticamente
        </p>
      </div>

      <p className="text-xs text-slate-500">
        Cerrando wizard en 2 segundos...
      </p>
    </div>
  );
}

// ERROR - Installation failed
interface ErrorScreenProps {
  error: string | null;
  onRetry: () => void;
  onSkip: () => void;
}

function ErrorScreen({ error, onRetry, onSkip }: ErrorScreenProps) {
  return (
    <div className="space-y-4">
      <div className="p-4 bg-red-900/20 rounded-lg border border-red-700">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 bg-red-500/20 rounded-full flex items-center justify-center">
            <span className="text-xl">⚠️</span>
          </div>
          <div>
            <p className="text-white font-medium">Error de Instalación</p>
            <p className="text-red-300 text-sm mt-1">{error || 'Error desconocido'}</p>
          </div>
        </div>

        <div className="space-y-2 text-sm text-slate-300">
          <p className="font-medium">Posibles causas:</p>
          <ul className="list-disc list-inside space-y-1 ml-2">
            <li>Permisos insuficientes</li>
            <li>Antivirus bloqueando instalación</li>
            <li>Sin conexión a internet</li>
          </ul>
        </div>
      </div>

      <div className="flex gap-3">
        <Button
          onClick={onRetry}
          className="flex-1 bg-cyan-600 hover:bg-cyan-500 text-white"
        >
          Reintentar
        </Button>
        <Button
          onClick={onSkip}
          variant="outline"
          className="border-slate-600 text-slate-300 hover:bg-slate-800"
        >
          Omitir
        </Button>
      </div>

      <div className="p-3 bg-slate-800 rounded-lg">
        <p className="text-xs text-slate-400">
          💡 <span className="font-medium">Instalación manual:</span> Descarga FI Monitor desde{' '}
          <a
            href="https://github.com/BernardUriza/free-intelligence/releases"
            target="_blank"
            rel="noopener noreferrer"
            className="text-cyan-400 hover:underline"
          >
            GitHub Releases
          </a>
        </p>
      </div>
    </div>
  );
}
