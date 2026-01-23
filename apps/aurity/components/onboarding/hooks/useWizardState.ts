/**
 * useWizardState - Hybrid persistence hook for wizard state
 *
 * In desktop mode: Uses Tauri commands to persist to filesystem (~/.aurity/config/wizard-state.json)
 * In web/fallback: Uses localStorage as fallback
 *
 * Handles automatic migration from localStorage to filesystem on first desktop run.
 */

import { useState, useEffect, useCallback } from 'react';
import { isDesktop } from '@/lib/config/deployment';

// Storage key for localStorage (legacy + fallback)
const STORAGE_KEY = 'aurity_desktop_setup_complete';
const STORAGE_KEY_FI_MONITOR = 'aurity_fi_monitor_installed';

// Tauri invoke helper - only available in desktop mode
const invokeTauri = async <T,>(cmd: string, args?: Record<string, unknown>): Promise<T | null> => {
  if (typeof window !== 'undefined' && '__TAURI__' in window) {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      return await invoke<T>(cmd, args);
    } catch (error) {
      console.error(`[useWizardState] Tauri command ${cmd} failed:`, error);
      throw error;
    }
  }
  return null;
};

export interface WizardState {
  version: number;
  desktop_setup_completed: boolean;
  desktop_setup_completed_at: string | null;
  fi_monitor_installed: boolean | null;
}

interface UseWizardStateResult {
  /** Whether the wizard state has been loaded */
  isLoading: boolean;
  /** Whether the desktop setup has been completed */
  isCompleted: boolean;
  /** Full wizard state */
  state: WizardState | null;
  /** Mark the desktop setup as complete */
  markComplete: (fiMonitorInstalled: boolean) => Promise<void>;
  /** Reset the wizard state (for development/testing) */
  reset: () => Promise<void>;
  /** Refresh the state from storage */
  refresh: () => Promise<void>;
}

/**
 * Hook to manage wizard state with hybrid persistence
 * - Desktop: Filesystem via Tauri
 * - Web/Fallback: localStorage
 */
export function useWizardState(): UseWizardStateResult {
  const [isLoading, setIsLoading] = useState(true);
  const [state, setState] = useState<WizardState | null>(null);

  // Load state from storage
  const loadState = useCallback(async () => {
    setIsLoading(true);
    console.log('[useWizardState] Loading state...');

    try {
      const desktop = isDesktop();
      console.log('[useWizardState] isDesktop:', desktop);

      if (desktop) {
        // Try to load from filesystem via Tauri
        console.log('[useWizardState] Calling get_wizard_state...');
        const tauriState = await invokeTauri<WizardState>('get_wizard_state');
        console.log('[useWizardState] Tauri state:', tauriState);

        if (tauriState) {
          // Check if we need to migrate from localStorage
          const localStorageComplete = localStorage.getItem(STORAGE_KEY) === 'true';
          console.log('[useWizardState] localStorage complete:', localStorageComplete);

          if (!tauriState.desktop_setup_completed && localStorageComplete) {
            // Migration: localStorage has data but filesystem doesn't
            console.log('[useWizardState] Migrating from localStorage to filesystem');
            const fiMonitorInstalled = localStorage.getItem(STORAGE_KEY_FI_MONITOR) === 'true';
            // Tauri 2.0 uses camelCase on JS side, converts to snake_case for Rust
            const migratedState = await invokeTauri<WizardState>('mark_desktop_setup_complete', {
              fiMonitorInstalled: fiMonitorInstalled,
            });

            if (migratedState) {
              setState(migratedState);
              // Clear localStorage after successful migration
              localStorage.removeItem(STORAGE_KEY);
              localStorage.removeItem(STORAGE_KEY_FI_MONITOR);
              console.log('[useWizardState] Migration complete, localStorage cleared');
            } else {
              setState(tauriState);
            }
          } else {
            setState(tauriState);
          }
        } else {
          // Tauri available but returned null - use localStorage fallback
          loadFromLocalStorage();
        }
      } else {
        // Not desktop - use localStorage
        loadFromLocalStorage();
      }
    } catch (error) {
      console.error('[useWizardState] Error loading state, falling back to localStorage:', error);
      loadFromLocalStorage();
    } finally {
      setIsLoading(false);
      console.log('[useWizardState] Loading complete');
    }
  }, []);

  // Load from localStorage (fallback)
  const loadFromLocalStorage = () => {
    const isComplete = localStorage.getItem(STORAGE_KEY) === 'true';
    const fiMonitorInstalled = localStorage.getItem(STORAGE_KEY_FI_MONITOR) === 'true';

    setState({
      version: 0, // localStorage version
      desktop_setup_completed: isComplete,
      desktop_setup_completed_at: null,
      fi_monitor_installed: isComplete ? fiMonitorInstalled : null,
    });
  };

  // Mark setup as complete
  const markComplete = useCallback(async (fiMonitorInstalled: boolean) => {
    try {
      if (isDesktop()) {
        // Save to filesystem via Tauri (camelCase for Tauri 2.0)
        const newState = await invokeTauri<WizardState>('mark_desktop_setup_complete', {
          fiMonitorInstalled: fiMonitorInstalled,
        });

        if (newState) {
          setState(newState);
          // Filesystem es el source of truth - LIMPIAR localStorage
          // Esto evita que la migración automática recree el archivo si se borra
          localStorage.removeItem(STORAGE_KEY);
          localStorage.removeItem(STORAGE_KEY_FI_MONITOR);
          return;
        }
      }

      // Fallback to localStorage
      localStorage.setItem(STORAGE_KEY, 'true');
      localStorage.setItem(STORAGE_KEY_FI_MONITOR, fiMonitorInstalled.toString());
      setState({
        version: 0,
        desktop_setup_completed: true,
        desktop_setup_completed_at: new Date().toISOString(),
        fi_monitor_installed: fiMonitorInstalled,
      });
    } catch (error) {
      console.error('[useWizardState] Error marking complete, using localStorage fallback:', error);
      localStorage.setItem(STORAGE_KEY, 'true');
      localStorage.setItem(STORAGE_KEY_FI_MONITOR, fiMonitorInstalled.toString());
      setState({
        version: 0,
        desktop_setup_completed: true,
        desktop_setup_completed_at: new Date().toISOString(),
        fi_monitor_installed: fiMonitorInstalled,
      });
    }
  }, []);

  // Reset wizard state
  const reset = useCallback(async () => {
    try {
      if (isDesktop()) {
        // Delete from filesystem via Tauri
        await invokeTauri<boolean>('reset_wizard_state');
      }

      // Also clear localStorage
      localStorage.removeItem(STORAGE_KEY);
      localStorage.removeItem(STORAGE_KEY_FI_MONITOR);

      setState({
        version: 0,
        desktop_setup_completed: false,
        desktop_setup_completed_at: null,
        fi_monitor_installed: null,
      });

      console.log('[useWizardState] Wizard state reset');
    } catch (error) {
      console.error('[useWizardState] Error resetting state:', error);
      // Still clear localStorage even if Tauri fails
      localStorage.removeItem(STORAGE_KEY);
      localStorage.removeItem(STORAGE_KEY_FI_MONITOR);
      setState({
        version: 0,
        desktop_setup_completed: false,
        desktop_setup_completed_at: null,
        fi_monitor_installed: null,
      });
    }
  }, []);

  // Load state on mount
  useEffect(() => {
    loadState();
  }, [loadState]);

  return {
    isLoading,
    isCompleted: state?.desktop_setup_completed ?? false,
    state,
    markComplete,
    reset,
    refresh: loadState,
  };
}

/**
 * Standalone function to reset wizard state (for use outside React components)
 * Useful for menu items, keyboard shortcuts, etc.
 */
export async function resetWizardState(): Promise<void> {
  try {
    if (isDesktop() && typeof window !== 'undefined' && '__TAURI__' in window) {
      const { invoke } = await import('@tauri-apps/api/core');
      await invoke('reset_wizard_state');
    }
  } catch (error) {
    console.error('[resetWizardState] Tauri reset failed:', error);
  }

  // Always clear localStorage
  localStorage.removeItem(STORAGE_KEY);
  localStorage.removeItem(STORAGE_KEY_FI_MONITOR);

  // Reload the page to show the wizard
  window.location.reload();
}
