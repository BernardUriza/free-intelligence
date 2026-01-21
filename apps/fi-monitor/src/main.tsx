import React, { useState, useEffect } from 'react'
import ReactDOM from 'react-dom/client'
import { invoke } from '@tauri-apps/api/core'
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

  // Show wizard if setup not completed
  if (!setupState?.completed) {
    return <SetupWizard />;
  }

  // Show main app if setup completed
  return <App setupState={setupState} />;
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>,
)
