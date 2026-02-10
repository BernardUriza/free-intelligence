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

import { useState, useEffect, useRef } from 'react';
import { detectTauri, isBrowser } from '@/lib/environment';
import { Button } from '@/components/ui/button';
import { CheckCircle, Loader2, Download, Cloud, Shield, AlertTriangle, Lightbulb, Rocket } from 'lucide-react';
import { useWizardState, resetWizardState } from './hooks/useWizardState';

// Export function to reset wizard (for use in settings/menu)
export { resetWizardState as resetDesktopSetupWizard };

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
  const [appVersion, setAppVersion] = useState<string | null>(null);

  // Use ref to track if we've already checked (prevents double-run)
  const hasChecked = useRef(false);

  // Direct Tauri detection (no context dependency to avoid loops)
  const isTauri = isBrowser() && detectTauri();

  // Get app version from Tauri (only once)
  useEffect(() => {
    async function fetchVersion() {
      if (isTauri) {
        try {
          const { getVersion } = await import('@tauri-apps/api/app');
          const version = await getVersion();
          setAppVersion(version);
        } catch (e) {
          console.warn('[DesktopWizard] Could not get version:', e);
        }
      }
    }
    fetchVersion();
  }, [isTauri]);

  // Use the wizard state hook for persistent storage
  const { isLoading: isLoadingState, isCompleted, markComplete } = useWizardState();

  // Check if setup already completed (run only once)
  useEffect(() => {
    // Prevent double-execution
    if (hasChecked.current) return;

    // Wait for state to load
    if (isLoadingState) return;

    // Mark as checked
    hasChecked.current = true;

    // CRITICAL: Only show wizard if ACTUALLY running in Tauri
    if (!isTauri) {
      setShowWizard(false);
      return;
    }

    if (isCompleted) {
      setShowWizard(false);
      return;
    }

    // Setup not complete - show wizard and check FI Monitor
    setShowWizard(true);
    checkFiMonitor();
  }, [isTauri, isLoadingState, isCompleted]);

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
          setProgress(prev => [...prev, '[OK] FI Monitor instalado correctamente']);

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

  // Retry installation
  const retryInstallation = () => {
    setError(null);
    setProgress([]);
    checkFiMonitor();
  };

  // Mark setup as complete using the hook (persists to filesystem on desktop)
  const markSetupComplete = async (fiMonitorInstalled: boolean = true) => {
    console.log('[DesktopWizard] Marking setup complete, fiMonitorInstalled:', fiMonitorInstalled);
    try {
      await markComplete(fiMonitorInstalled);
      console.log('[DesktopWizard] Setup marked complete successfully');
    } catch (err) {
      console.error('[DesktopWizard] Failed to mark setup complete:', err);
    }
    setTimeout(() => setShowWizard(false), 2000);
  };

  if (!showWizard) {
    return null;
  }

  return (
    <div className="onb-overlay">
      <div className="onb-modal">

        {/* Header */}
        <div className="onb-header">
          <div className="onb-header-icon">
            <Shield className="onb-icon-lg onb-icon-white" />
          </div>
          <h1 className="onb-text-title">Bienvenido a Aurity Desktop</h1>
          <p className="onb-text-version">v{appVersion || '1.0.2'}</p>
          <p className="onb-text-muted">
            Configuremos tu asistente médico 100% offline
          </p>
        </div>

        {/* Content by screen */}
        {screen === 'CHECKING' && <CheckingScreen />}
        {screen === 'NOT_INSTALLED' && <NotInstalledScreen onInstall={installFiMonitor} />}
        {screen === 'INSTALLING' && <InstallingScreen progress={progress} />}
        {screen === 'READY' && <ReadyScreen />}
        {screen === 'ERROR' && <ErrorScreen error={error} onRetry={retryInstallation} />}

      </div>
    </div>
  );
}

// CHECKING - Verifying FI Monitor
function CheckingScreen() {
  return (
    <div className="onb-stack-lg">
      <div className="onb-checking-box">
        <Loader2 className="onb-icon-md onb-icon-cyan onb-icon-spin" />
        <div>
          <p className="onb-text-label">Verificando FI Monitor...</p>
          <p className="onb-text-muted">Un momento por favor</p>
        </div>
      </div>
    </div>
  );
}

// NOT_INSTALLED - Offer to install FI Monitor
interface NotInstalledScreenProps {
  onInstall: () => void;
}

function NotInstalledScreen({ onInstall }: NotInstalledScreenProps) {
  return (
    <div className="onb-stack-lg">
      <div className="onb-info-card">
        <div className="onb-row-mb">
          <Cloud className="onb-icon-md onb-icon-cyan" />
          <div>
            <p className="onb-text-label">FI Monitor Requerido</p>
            <p className="onb-text-body">Conectividad remota a tu IA local</p>
          </div>
        </div>

        <div className="onb-info-body">
          <p>FI Monitor gestiona:</p>
          <ul className="onb-list">
            <li>Instalación automática de Python 3.14</li>
            <li>Instalación automática de Ollama</li>
            <li>Túnel seguro para acceso remoto</li>
          </ul>
        </div>
      </div>

      <div className="onb-btn-row">
        <Button
          onClick={onInstall}
          className="onb-btn-primary"
        >
          <Download className="onb-icon-sm onb-icon-mr" />
          Instalar Ahora
        </Button>
      </div>

      <p className="onb-text-center-fine">
        FI Monitor es necesario para el funcionamiento de Aurity
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
    <div className="onb-stack-lg">
      <div className="onb-stack-md">
        <div className="onb-row">
          <Loader2 className="onb-icon-md onb-icon-cyan onb-icon-spin" />
          <div>
            <p className="onb-text-label">Instalando FI Monitor...</p>
            <p className="onb-text-muted">Por favor espera (1-2 minutos)</p>
          </div>
        </div>

        {/* Progress bar */}
        <div className="onb-progress-track">
          <div
            className="onb-progress-fill"
            style={{ width: `${progressPercent}%` }}
          />
        </div>

        {/* Progress log */}
        <div className="onb-progress-log">
          {progress.map((msg, i) => (
            <div
              key={i}
              className={
                msg.includes('[OK]') || msg.includes('correctamente')
                  ? 'onb-log-line-success'
                  : 'onb-log-line'
              }
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
    <div className="onb-ready-wrapper">
      <div className="onb-ready-icon">
        <CheckCircle className="onb-icon-xl onb-icon-emerald" />
      </div>

      <div>
        <h2 className="onb-ready-title">¡Todo Listo!</h2>
        <p className="onb-text-body">
          FI Monitor instalado correctamente
        </p>
      </div>

      <div className="onb-info-card">
        <p className="onb-ready-info">
          <Rocket className="onb-icon-sm" />
          Abriendo FI Monitor...
        </p>
        <p className="onb-ready-subtext">
          FI Monitor configurará Python y Ollama automáticamente
        </p>
      </div>

      <p className="onb-text-fine">
        Cerrando wizard en 2 segundos...
      </p>
    </div>
  );
}

// ERROR - Installation failed
interface ErrorScreenProps {
  error: string | null;
  onRetry: () => void;
}

function ErrorScreen({ error, onRetry }: ErrorScreenProps) {
  return (
    <div className="onb-stack-lg">
      <div className="onb-error-card">
        <div className="onb-row-mb">
          <div className="onb-error-icon">
            <AlertTriangle className="onb-icon-sm onb-icon-red" />
          </div>
          <div>
            <p className="onb-text-label">Error de Instalación</p>
            <p className="onb-error-detail">{error || 'Error desconocido'}</p>
          </div>
        </div>

        <div className="onb-info-body">
          <p className="onb-font-medium">Posibles causas:</p>
          <ul className="onb-list">
            <li>Permisos insuficientes</li>
            <li>Antivirus bloqueando instalación</li>
            <li>Sin conexión a internet</li>
          </ul>
        </div>
      </div>

      <div className="onb-btn-row">
        <Button
          onClick={onRetry}
          className="onb-btn-primary"
        >
          Reintentar
        </Button>
      </div>

      <div className="onb-hint-box">
        <p className="onb-hint-text">
          <Lightbulb className="onb-hint-icon" />
          <span><span className="onb-font-medium">Instalación manual:</span> Descarga FI Monitor desde{' '}
          <a
            href="https://github.com/BernardUriza/free-intelligence/releases"
            target="_blank"
            rel="noopener noreferrer"
            className="onb-link"
          >
            GitHub Releases
          </a></span>
        </p>
      </div>
    </div>
  );
}
