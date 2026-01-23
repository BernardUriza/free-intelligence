'use client';

import { useEffect } from 'react';

/**
 * DesktopReadySignal - Emits 'frontend-ready' event to Tauri backend
 *
 * This component signals to the Rust backend that React has mounted,
 * allowing it to close the splashscreen at the right moment.
 *
 * Without this signal, the splash would close before the UI is ready,
 * causing the wizard to appear in a small window (splash dimensions).
 *
 * Note: Uses emitTo('main', ...) to target the specific window listener
 * in Tauri 2.0 (global emit() doesn't reach window-specific listeners).
 */
export function DesktopReadySignal() {
  useEffect(() => {
    const signalReady = async () => {
      // Only emit in Tauri desktop environment
      if (typeof window !== 'undefined' && '__TAURI__' in window) {
        try {
          const { emitTo } = await import('@tauri-apps/api/event');
          // Emit to 'main' window specifically (where the listener is)
          await emitTo('main', 'frontend-ready', {});
          console.log('[Layout] Frontend ready signal emitted to main window');
        } catch (e) {
          console.error('[Layout] Failed to emit frontend-ready:', e);
        }
      }
    };
    signalReady();
  }, []);

  // This component renders nothing - it's purely for side effects
  return null;
}
