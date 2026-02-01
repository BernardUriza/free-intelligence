import React, { useState, useEffect } from 'react'
import ReactDOM from 'react-dom/client'
import { invoke, isTauriContext } from './lib/tauri-adapter'
import App from './App'
import { SetupWizard } from './SetupWizard'
import './styles.css'

interface SetupState {
  completed: boolean;
  ollamaInstalled: boolean;
  pythonInstalled: boolean;
  lastCheck: string | null;
  skipped: boolean;
}

function Root() {
  const [setupState, setSetupState] = useState<SetupState | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadSetupState() {
      try {
        const state = await invoke<SetupState>('get_setup_state');
        setSetupState(state);
      } catch (err) {
        console.error('[FI Monitor] Failed to load setup state:', err);
        // Default to showing wizard on error
        setSetupState({
          completed: false,
          ollamaInstalled: false,
          pythonInstalled: false,
          lastCheck: null,
          skipped: false,
        });
      } finally {
        setLoading(false);
      }
    }

    loadSetupState();
  }, []);

  if (loading) {
    return (
      <div className="app loading">
        <div className="spinner"></div>
      </div>
    );
  }

  // 🔧 DEV MODE: Skip wizard en web browser para debugging con Chrome DevTools
  const isWebBrowser = !isTauriContext();

  // Show wizard if setup not completed (solo en Tauri)
  if (!isWebBrowser && !setupState?.completed) {
    return <SetupWizard />;
  }

  // Show main app (en Tauri si setup OK, en Chrome siempre)
  return <App setupState={setupState || {
    completed: true,
    ollamaInstalled: false,
    pythonInstalled: false,
    lastCheck: null,
    skipped: true
  }} />;
}

// 🛡️ Singleton pattern: Evita crear múltiples roots durante HMR
let root: ReturnType<typeof ReactDOM.createRoot> | null = null

function renderApp() {
  const container = document.getElementById('root')!

  if (!root) {
    root = ReactDOM.createRoot(container)
  }

  root.render(
    <React.StrictMode>
      <Root />
    </React.StrictMode>
  )
}

renderApp()

// HMR: Reutilizar root existente
if (import.meta.hot) {
  import.meta.hot.accept(() => {
    renderApp()  // Re-render, NO re-create root
  })
}
