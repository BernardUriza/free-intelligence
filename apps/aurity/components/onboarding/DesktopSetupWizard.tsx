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
import { CheckCircle, Loader2, Download, Cloud, Shield, AlertTriangle, Lightbulb, Rocket, ShieldAlert, WifiOff, FolderLock, SkipForward } from 'lucide-react';
import { useWizardState, resetWizardState } from './hooks/useWizardState';
import { createLogger } from '@/lib/internal/logger';

const log = createLogger('DesktopWizard');

// Export function to reset wizard (for use in settings/menu)
export { resetWizardState as resetDesktopSetupWizard };

// Tauri invoke helper - only available in desktop mode
const invokeTauri = async <T,>(cmd: string, args?: Record<string, unknown>): Promise<T | null> => {
  log.debug('Invoking Tauri command', { cmd });
  if (typeof window !== 'undefined' && '__TAURI__' in window) {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      const result = await invoke<T>(cmd, args);
      return result;
    } catch (error) {
      log.error('Tauri command failed', { cmd, error: String(error) });
      throw error;
    }
  }
  log.warn('Tauri not available, command skipped', { cmd });
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
  const [downloadPercent, setDownloadPercent] = useState<number>(0);
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
          log.warn('Could not get version', { error: String(e) });
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
      log.error('Failed to check FI Monitor', { error: String(err) });
      const errorMsg = extractErrorMessage(err);
      // Only treat as "not installed" if the error is clearly about absence.
      // Any other Tauri error (permissions, crash) must surface to the user.
      const isNotInstalled = errorMsg.toLowerCase().includes('not installed')
        || errorMsg.toLowerCase().includes('no instalado');
      if (isNotInstalled) {
        setScreen('NOT_INSTALLED');
      } else {
        setError(errorMsg || 'No se pudo verificar el estado de FI Monitor.');
        setScreen('ERROR');
      }
    }
  };

  // Install FI Monitor
  const installFiMonitor = async () => {
    setScreen('INSTALLING');
    setProgress(['Descargando FI Monitor...']);
    setDownloadPercent(0);

    try {
      // Listen for progress events
      if (typeof window !== 'undefined' && '__TAURI__' in window) {
        const { listen } = await import('@tauri-apps/api/event');

        const unlistenStatus = await listen<string>('fi-monitor-install-status', (event) => {
          setProgress(prev => [...prev, event.payload]);
        });

        const unlistenProgress = await listen<{ percentage: number }>('fi-monitor-download-progress', (event) => {
          setDownloadPercent(Math.round(event.payload.percentage));
        });

        // Start installation
        const result = await invokeTauri<boolean>('install_fi_monitor_full');

        unlistenStatus();
        unlistenProgress();

        if (result) {
          setProgress(prev => [...prev, '[OK] FI Monitor instalado correctamente']);

          // Launch FI Monitor (it will show its own wizard for Python + Ollama)
          setTimeout(async () => {
            await launchFiMonitor();
            setScreen('READY');
            markSetupComplete();
          }, 2000);
        } else {
          setError('La instalación no se completó. Es posible que tu antivirus haya bloqueado el proceso o que falten permisos. Intenta desactivar temporalmente tu antivirus y vuelve a intentar.');
          setScreen('ERROR');
        }
      }
    } catch (err) {
      log.error('Installation failed', { error: String(err) });
      // Tauri invoke errors can be strings, Error objects, or objects with message property
      const errorMsg = extractErrorMessage(err);
      setError(errorMsg);
      setScreen('ERROR');
    }
  };

  // Launch FI Monitor application
  const launchFiMonitor = async () => {
    try {
      await invokeTauri<boolean>('launch_fi_monitor');
      log.info('FI Monitor launched');
    } catch (err) {
      log.error('Failed to launch FI Monitor', { error: String(err) });
    }
  };

  // Retry installation
  const retryInstallation = () => {
    setError(null);
    setProgress([]);
    checkFiMonitor();
  };

  // Skip wizard (user will set up later)
  const skipSetup = async () => {
    await markSetupComplete(false);
  };

  // Mark setup as complete using the hook (persists to filesystem on desktop)
  const markSetupComplete = async (fiMonitorInstalled: boolean = true) => {
    try {
      await markComplete(fiMonitorInstalled);
      log.info('Setup marked complete', { fiMonitorInstalled });
    } catch (err) {
      log.error('Failed to mark setup complete', { error: String(err) });
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
        {screen === 'INSTALLING' && <InstallingScreen progress={progress} downloadPercent={downloadPercent} />}
        {screen === 'READY' && <ReadyScreen />}
        {screen === 'ERROR' && <ErrorScreen error={error} onRetry={retryInstallation} onSkip={skipSetup} />}

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
  downloadPercent: number;
}

function InstallingScreen({ progress, downloadPercent }: InstallingScreenProps) {
  // Use real download % when available, fall back to step-based estimate for other phases
  const progressPercent = downloadPercent > 0
    ? downloadPercent
    : Math.min(90, (progress.length / 5) * 100);

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

/// Extract a readable error message from Tauri invoke errors.
/// Tauri 2.x serializes Rust enums as: { "VariantName": "message" }
/// e.g. MonitorError::DownloadFailed("x") → { "DownloadFailed": "x" }
function extractErrorMessage(err: unknown): string {
  if (err instanceof Error) return err.message;
  if (typeof err === 'string') return err;
  if (err && typeof err === 'object') {
    if ('message' in err) return String((err as { message: unknown }).message);
    // Rust enum serialization: { "DownloadFailed": "msg" } or { "InstallFailed": "msg" }
    const values = Object.values(err as Record<string, unknown>);
    if (values.length === 1 && typeof values[0] === 'string') return values[0];
  }
  return 'Error desconocido al instalar. Revisa tu conexión e intenta de nuevo.';
}

/// Classify the error to show specific, actionable guidance
type ErrorType = 'permission' | 'antivirus' | 'network' | 'not-found' | 'unknown';

function classifyError(error: string | null): ErrorType {
  if (!error) return 'unknown';
  const lower = error.toLowerCase();
  if (lower.includes('permiso') || lower.includes('permission') || lower.includes('denied') || lower.includes('access') || lower.includes('código: 5')) return 'permission';
  if (lower.includes('antivirus') || lower.includes('bloqueando') || lower.includes('blocked')) return 'antivirus';
  if (lower.includes('download') || lower.includes('network') || lower.includes('internet') || lower.includes('conexi') || lower.includes('fetch') || lower.includes('timeout') || lower.includes('status: 4') || lower.includes('status: 5')) return 'network';
  if (lower.includes('not found') || lower.includes('no encontr') || lower.includes('no such file')) return 'not-found';
  return 'unknown';
}

const ERROR_GUIDANCE: Record<ErrorType, { icon: typeof AlertTriangle; title: string; steps: string[] }> = {
  permission: {
    icon: FolderLock,
    title: 'Permisos insuficientes',
    steps: [
      'Haz clic derecho en el instalador y selecciona "Ejecutar como administrador"',
      'Si estás en una PC corporativa, pide a tu equipo de TI que autorice la instalación',
      'Verifica que tu usuario tenga permisos de escritura en la carpeta de usuario',
    ],
  },
  antivirus: {
    icon: ShieldAlert,
    title: 'Antivirus bloqueando la instalación',
    steps: [
      'Desactiva temporalmente tu antivirus (Windows Defender, Avast, Norton, etc.)',
      'Agrega una excepción para la carpeta %LOCALAPPDATA%\\FI Monitor',
      'Vuelve a activar el antivirus después de instalar',
    ],
  },
  network: {
    icon: WifiOff,
    title: 'Error de conexión',
    steps: [
      'Verifica que tienes conexión a internet',
      'Si usas VPN o proxy, intenta desactivarlo temporalmente',
      'La descarga es de ~50 MB, verifica que tu red no bloquee descargas grandes',
    ],
  },
  'not-found': {
    icon: AlertTriangle,
    title: 'Archivo no encontrado',
    steps: [
      'La instalación de Aurity Desktop puede estar incompleta',
      'Reinstala Aurity Desktop desde la página de descargas',
      'Si el problema persiste, descarga FI Monitor manualmente',
    ],
  },
  unknown: {
    icon: AlertTriangle,
    title: 'Error de instalación',
    steps: [
      'Reinicia la aplicación e intenta de nuevo',
      'Si tu antivirus bloquea la instalación, agrega una excepción temporal',
      'Verifica que tienes conexión a internet estable',
      'Si el problema persiste, descarga FI Monitor manualmente desde GitHub',
    ],
  },
};

// ERROR - Installation failed
interface ErrorScreenProps {
  error: string | null;
  onRetry: () => void;
  onSkip: () => void;
}

function ErrorScreen({ error, onRetry, onSkip }: ErrorScreenProps) {
  const errorType = classifyError(error);
  const guidance = ERROR_GUIDANCE[errorType];
  const GuidanceIcon = guidance.icon;

  return (
    <div className="onb-stack-lg">
      <div className="onb-error-card">
        <div className="onb-row-mb">
          <div className="onb-error-icon">
            <GuidanceIcon className="onb-icon-sm onb-icon-red" />
          </div>
          <div>
            <p className="onb-text-label">{guidance.title}</p>
            {error && error !== guidance.title && (
              <p className="onb-error-detail">{error}</p>
            )}
          </div>
        </div>

        <div className="onb-info-body">
          <p className="onb-font-medium">Solución:</p>
          <ol className="onb-list" style={{ listStyleType: 'decimal' }}>
            {guidance.steps.map((step, i) => (
              <li key={i}>{step}</li>
            ))}
          </ol>
        </div>
      </div>

      <div className="onb-btn-row">
        <Button
          onClick={onRetry}
          className="onb-btn-primary"
        >
          Reintentar
        </Button>
        <Button
          onClick={onSkip}
          variant="outline"
          className="onb-btn-secondary"
        >
          <SkipForward className="onb-icon-sm onb-icon-mr" />
          Configurar después
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
