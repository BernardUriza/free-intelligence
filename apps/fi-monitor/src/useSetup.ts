// React hook for setup wizard state management (Ollama + Python 3.14)
import { useState, useEffect } from 'react';
import { invoke, listen } from './lib/tauri-adapter';
import type { SetupState } from './types/monitor';

export type { SetupState };

export type SetupScreen =
  | 'CHECKING'
  | 'NOT_INSTALLED'
  | 'INSTALLING'
  | 'READY'
  | 'ERROR'
  | 'SKIPPED';

export interface OllamaInstallStatus {
  installed: boolean;
  version: string | null;
  install_path: string | null;
}

export interface PythonInstallStatus {
  installed: boolean;
  version: string | null;
  install_path: string | null;
}

interface MissingDeps {
  ollama: boolean;
  python: boolean;
}

export function useSetup() {
  const [screen, setScreen] = useState<SetupScreen>('CHECKING');
  const [setupState, setSetupState] = useState<SetupState>({
    completed: false,
    ollamaInstalled: false,
    pythonInstalled: false,
    lastCheck: null,
    skipped: false,
  });
  const [missingDeps, setMissingDeps] = useState<MissingDeps>({
    ollama: false,
    python: false,
  });
  const [progress, setProgress] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [currentInstalling, setCurrentInstalling] = useState<'ollama' | 'python' | null>(null);

  // Load setup state on mount
  useEffect(() => {
    loadSetupState();
  }, []);

  // Listen for installation progress events
  useEffect(() => {
    const unlistenOllama = listen<string>('ollama-install-status', (event) => {
      setProgress(prev => [...prev, `[Ollama] ${event.payload}`]);
    });

    const unlistenPython = listen<string>('python-install-status', (event) => {
      setProgress(prev => [...prev, `[Python] ${event.payload}`]);
    });

    return () => {
      unlistenOllama.then(fn => fn());
      unlistenPython.then(fn => fn());
    };
  }, []);

  async function loadSetupState() {
    try {
      const state = await invoke<SetupState>('get_setup_state');
      setSetupState(state);

      if (state.completed) {
        // Setup already completed, skip wizard
        return;
      }

      // Check which dependencies are missing
      await checkDependencies();
    } catch (err) {
      console.error('[Setup] Failed to load state:', err);
      setError(String(err));
      setScreen('ERROR');
    }
  }

  async function checkDependencies() {
    try {
      setScreen('CHECKING');

      const [ollamaStatus, pythonStatus] = await Promise.all([
        invoke<OllamaInstallStatus>('check_ollama_installed'),
        invoke<PythonInstallStatus>('check_python_installed'),
      ]);

      const missing: MissingDeps = {
        ollama: !ollamaStatus.installed,
        python: !pythonStatus.installed,
      };

      setMissingDeps(missing);

      if (!missing.ollama && !missing.python) {
        // Both installed, mark as ready
        await invoke('mark_setup_completed', {
          ollamaInstalled: true,
          pythonInstalled: true,
        });
        setScreen('READY');
        setSetupState(prev => ({
          ...prev,
          completed: true,
          ollamaInstalled: true,
          pythonInstalled: true,
        }));
      } else {
        // Show install prompt
        setScreen('NOT_INSTALLED');
      }
    } catch (err) {
      console.error('[Setup] Check dependencies failed:', err);
      setError(String(err));
      setScreen('ERROR');
    }
  }

  async function installDependencies() {
    try {
      setScreen('INSTALLING');
      setProgress(['Iniciando instalación...']);
      setError(null);

      let ollamaSuccess = !missingDeps.ollama; // Skip if already installed
      let pythonSuccess = !missingDeps.python; // Skip if already installed

      // Install Python first (required for RAG service)
      if (missingDeps.python) {
        setCurrentInstalling('python');
        setProgress(prev => [...prev, '=== Instalando Python 3.14 ===']);
        try {
          pythonSuccess = await invoke<boolean>('install_python_silent');
          if (pythonSuccess) {
            setProgress(prev => [...prev, '✓ Python 3.14 instalado correctamente']);
          }
        } catch (bundleErr) {
          setProgress(prev => [...prev, `Instalador bundleado no disponible, descargando...`]);
          try {
            pythonSuccess = await invoke<boolean>('download_and_install_python');
            if (pythonSuccess) {
              setProgress(prev => [...prev, '✓ Python 3.14 instalado correctamente (descarga)']);
            }
          } catch (downloadErr) {
            setProgress(prev => [...prev, `✗ Error instalando Python: ${downloadErr}`]);
            throw new Error(`Python installation failed: ${downloadErr}`);
          }
        }
      }

      // Install Ollama
      if (missingDeps.ollama) {
        setCurrentInstalling('ollama');
        setProgress(prev => [...prev, '=== Instalando Ollama ===']);
        try {
          ollamaSuccess = await invoke<boolean>('install_ollama_silent');
          if (ollamaSuccess) {
            setProgress(prev => [...prev, '✓ Ollama instalado correctamente']);
          }
        } catch (bundleErr) {
          setProgress(prev => [...prev, `Instalador bundleado no disponible, descargando...`]);
          try {
            ollamaSuccess = await invoke<boolean>('download_and_install_ollama');
            if (ollamaSuccess) {
              setProgress(prev => [...prev, '✓ Ollama instalado correctamente (descarga)']);
            }
          } catch (downloadErr) {
            setProgress(prev => [...prev, `✗ Error instalando Ollama: ${downloadErr}`]);
            throw new Error(`Ollama installation failed: ${downloadErr}`);
          }
        }
      }

      if (pythonSuccess && ollamaSuccess) {
        await invoke('mark_setup_completed', {
          ollamaInstalled: ollamaSuccess,
          pythonInstalled: pythonSuccess,
        });
        setScreen('READY');
        setSetupState(prev => ({
          ...prev,
          completed: true,
          ollamaInstalled: ollamaSuccess,
          pythonInstalled: pythonSuccess,
        }));
      } else {
        throw new Error('One or more installations failed');
      }
    } catch (err) {
      console.error('[Setup] Install failed:', err);
      setError(String(err));
      setScreen('ERROR');
    } finally {
      setCurrentInstalling(null);
    }
  }

  async function skipSetup() {
    try {
      await invoke('mark_setup_skipped');
      setScreen('SKIPPED');
      setSetupState(prev => ({ ...prev, completed: true, skipped: true }));
    } catch (err) {
      console.error('[Setup] Skip failed:', err);
      setError(String(err));
    }
  }

  async function retryInstall() {
    setError(null);
    setProgress([]);
    await installDependencies();
  }

  function proceedToApp() {
    // Reload to pick up updated setup state from backend
    console.log('[Setup] Proceeding to app - reloading window');
    window.location.reload();
  }

  return {
    screen,
    setupState,
    missingDeps,
    progress,
    error,
    currentInstalling,
    checkDependencies,
    installDependencies,
    skipSetup,
    retryInstall,
    proceedToApp,
  };
}
