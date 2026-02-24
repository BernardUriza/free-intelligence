import { useEffect, useState } from 'react';
import { useSetup } from './useSetup';
import { getVersion } from '@tauri-apps/api/app';
import './styles/setup-wizard/index.css';

export function SetupWizard() {
  const {
    screen,
    missingDeps,
    progress,
    error,
    installDependencies,
    skipSetup,
    retryInstall,
    proceedToApp,
  } = useSetup();

  const [appVersion, setAppVersion] = useState('1.0.0');

  useEffect(() => {
    getVersion().then(v => setAppVersion(v)).catch(() => {});
  }, []);

  // Auto-proceed to app after 2 seconds on READY screen
  useEffect(() => {
    if (screen === 'READY') {
      const timer = setTimeout(() => {
        proceedToApp();
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [screen, proceedToApp]);

  return (
    <div className="setup-wizard">
      <div className="setup-container">
        {screen === 'CHECKING' && <CheckingScreen />}
        {screen === 'NOT_INSTALLED' && <NotInstalledScreen missingDeps={missingDeps} onInstall={installDependencies} onSkip={skipSetup} />}
        {screen === 'INSTALLING' && <InstallingScreen progress={progress} />}
        {screen === 'READY' && <ReadyScreen />}
        {screen === 'ERROR' && <ErrorScreen error={error} onRetry={retryInstall} onSkip={skipSetup} />}
        {screen === 'SKIPPED' && <SkippedScreen onProceed={proceedToApp} />}
      </div>
      <div className="setup-version">v{appVersion}</div>
    </div>
  );
}

function CheckingScreen() {
  return (
    <>
      <div className="setup-header">
        <div className="setup-icon">🦙</div>
        <h1 className="setup-title">Bienvenido</h1>
        <p className="setup-subtitle">Verificando dependencias...</p>
      </div>
      <div className="setup-body">
        <div className="setup-spinner"></div>
      </div>
    </>
  );
}

interface NotInstalledScreenProps {
  missingDeps: { ollama: boolean; python: boolean };
  onInstall: () => void;
  onSkip: () => void;
}

function NotInstalledScreen({ missingDeps, onInstall, onSkip }: NotInstalledScreenProps) {
  const missingList = [];
  if (missingDeps.python) missingList.push('Python 3.14');
  if (missingDeps.ollama) missingList.push('Ollama');

  const estimatedSize = (missingDeps.python ? 30 : 0) + (missingDeps.ollama ? 200 : 0);
  const estimatedTime = missingDeps.python && missingDeps.ollama ? '3-5 minutos' : '2-3 minutos';

  return (
    <>
      <div className="setup-header">
        <div className="setup-icon">{missingDeps.python && missingDeps.ollama ? '🐍🦙' : missingDeps.python ? '🐍' : '🦙'}</div>
        <h1 className="setup-title">Dependencias Requeridas</h1>
        <p className="setup-subtitle">FI Monitor necesita {missingList.join(' y ')} para funcionar</p>
      </div>
      <div className="setup-body">
        <div className="setup-info">
          {missingDeps.python && (
            <div className="setup-info-item">
              <span className="icon">🐍</span>
              <span>Python 3.14 (~30 MB)</span>
            </div>
          )}
          {missingDeps.ollama && (
            <div className="setup-info-item">
              <span className="icon">🦙</span>
              <span>Ollama (~200 MB)</span>
            </div>
          )}
          <div className="setup-info-item">
            <span className="icon">📦</span>
            <span>Tamaño total: ~{estimatedSize} MB</span>
          </div>
          <div className="setup-info-item">
            <span className="icon">⏱️</span>
            <span>Tiempo: {estimatedTime}</span>
          </div>
          <div className="setup-info-item">
            <span className="icon">🔒</span>
            <span>Instalación silenciosa (sin interacción)</span>
          </div>
        </div>
      </div>
      <div className="setup-actions">
        <button className="setup-btn setup-btn-primary" onClick={onInstall}>
          Instalar Ahora
        </button>
        <button className="setup-btn setup-btn-secondary" onClick={onSkip}>
          Omitir
        </button>
      </div>
    </>
  );
}

interface InstallingScreenProps {
  progress: string[];
}

function InstallingScreen({ progress }: InstallingScreenProps) {
  const progressPercent = Math.min(100, (progress.length / 5) * 100);

  return (
    <>
      <div className="setup-header">
        <div className="setup-icon">🦙</div>
        <h1 className="setup-title">Instalando Ollama</h1>
        <p className="setup-subtitle">Por favor espera, esto tomará 2-3 minutos</p>
      </div>
      <div className="setup-body">
        <div style={{ width: '100%' }}>
          <div className="setup-progress">
            <div className="setup-progress-bar" style={{ width: `${progressPercent}%` }}></div>
          </div>
          <div className="setup-progress-log">
            {progress.map((msg, i) => (
              <div key={i} className={`setup-progress-log-item ${msg.includes('✓') ? 'success' : ''}`}>
                {msg}
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}

function ReadyScreen() {
  return (
    <>
      <div className="setup-header">
        <div className="setup-icon">✅</div>
        <h1 className="setup-title">¡Todo Listo!</h1>
        <p className="setup-subtitle">Ollama instalado correctamente</p>
      </div>
      <div className="setup-body">
        <div className="setup-success-icon">✓</div>
        <p style={{ color: 'var(--text-dim)', fontSize: '13px' }}>
          Iniciando FI Monitor...
        </p>
      </div>
    </>
  );
}

interface ErrorScreenProps {
  error: string | null;
  onRetry: () => void;
  onSkip: () => void;
}

function ErrorScreen({ error, onRetry, onSkip }: ErrorScreenProps) {
  return (
    <>
      <div className="setup-header">
        <div className="setup-icon">⚠️</div>
        <h1 className="setup-title">Error de Instalación</h1>
      </div>
      <div className="setup-body">
        <div className="setup-error">
          <div className="setup-error-title">La instalación falló</div>
          <div className="setup-error-message">{error || 'Error desconocido'}</div>
        </div>
        <div className="setup-suggestions">
          <div className="setup-suggestions-title">Posibles causas:</div>
          <ul className="setup-suggestions-list">
            <li>Permisos insuficientes (intenta ejecutar como administrador)</li>
            <li>Antivirus bloqueando la instalación</li>
            <li>Espacio en disco insuficiente</li>
          </ul>
        </div>
      </div>
      <div className="setup-actions">
        <button className="setup-btn setup-btn-primary" onClick={onRetry}>
          Reintentar
        </button>
        <button className="setup-btn setup-btn-secondary" onClick={onSkip}>
          Omitir
        </button>
      </div>
      <div className="setup-link">
        💡 Instalación manual: <a href="https://ollama.com/download" target="_blank" rel="noopener noreferrer">ollama.com/download</a>
      </div>
    </>
  );
}

interface SkippedScreenProps {
  onProceed: () => void;
}

function SkippedScreen({ onProceed }: SkippedScreenProps) {
  // Auto-proceed after 3 seconds
  useEffect(() => {
    const timer = setTimeout(() => {
      onProceed();
    }, 3000);
    return () => clearTimeout(timer);
  }, [onProceed]);

  return (
    <>
      <div className="setup-header">
        <div className="setup-icon">ℹ️</div>
        <h1 className="setup-title">Instalación Omitida</h1>
        <p className="setup-subtitle">Modo degradado hasta instalar Ollama manualmente</p>
      </div>
      <div className="setup-body">
        <div className="setup-info">
          <div className="setup-info-item">
            <span className="icon">⚠️</span>
            <span>Algunas funciones estarán deshabilitadas</span>
          </div>
          <div className="setup-info-item">
            <span className="icon">🦙</span>
            <span>Instala Ollama para funcionalidad completa</span>
          </div>
        </div>
      </div>
      <div className="setup-actions">
        <button className="setup-btn setup-btn-primary" onClick={onProceed}>
          Entendido
        </button>
      </div>
      <div className="setup-link">
        Descarga: <a href="https://ollama.com/download" target="_blank" rel="noopener noreferrer">ollama.com/download</a>
      </div>
    </>
  );
}
