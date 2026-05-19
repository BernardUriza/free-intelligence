'use client';

import { useEffect, useState } from 'react';
import { createLogger } from '@/lib/internal/logger';

const log = createLogger('DesktopReady');

/**
 * DesktopReadySignal - Shows splash overlay until Tauri is ready
 *
 * This component:
 * 1. Shows a full-screen splash overlay with the Aurity logo
 * 2. Waits for the splash screen duration (15s) from Tauri
 * 3. Emits 'frontend-ready' signal to close the native splash
 * 4. Hides the overlay when Tauri closes the splash
 *
 * This ensures the user ALWAYS sees the splash branding, even if
 * Windows briefly flashes the main window during startup.
 */
export function DesktopReadySignal() {
  const [showOverlay, setShowOverlay] = useState(true);

  useEffect(() => {
    const signalReady = async () => {
      // Only emit in Tauri desktop environment
      if (typeof window !== 'undefined' && '__TAURI__' in window) {
        try {
          const { emitTo, listen } = await import('@tauri-apps/api/event');

          // Listen for when splash actually closes (then hide overlay)
          const unlisten = await listen('splash-closed', () => {
            log.info('Splash closed');
            setShowOverlay(false);
            unlisten();
          });

          await emitTo('main', 'frontend-ready', {});
          log.info('Frontend ready signal emitted');

          // Fallback: hide overlay after 20s if splash-closed never fires
          setTimeout(() => {
            setShowOverlay(false);
          }, 20000);
        } catch (e) {
          log.error('Failed to emit frontend-ready', { error: String(e) });
          // Hide overlay on error so app is usable
          setShowOverlay(false);
        }
      } else {
        // Not in Tauri, hide overlay immediately
        setShowOverlay(false);
      }
    };
    signalReady();
  }, []);

  // Don't show overlay if not needed
  if (!showOverlay) return null;

  // Full-screen splash overlay matching splashscreen.html style
  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 99999,
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'white',
        fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
      }}
    >
      <img
        src="/icons/icon-128x128.png"
        alt="Aurity"
        style={{
          width: 80,
          height: 80,
          borderRadius: 20,
          marginBottom: 20,
          objectFit: 'contain',
        }}
      />
      <h1 style={{ fontSize: 28, fontWeight: 600, marginBottom: 8 }}>Aurity</h1>
      <p style={{ fontSize: 14, opacity: 0.8, marginBottom: 30 }}>Medical AI Assistant</p>
      <div
        style={{
          width: 200,
          height: 4,
          background: 'rgba(255, 255, 255, 0.2)',
          borderRadius: 2,
          overflow: 'hidden',
          marginBottom: 16,
        }}
      >
        <div
          style={{
            width: '30%',
            height: '100%',
            background: 'white',
            borderRadius: 2,
            animation: 'splashLoading 1.5s ease-in-out infinite',
          }}
        />
      </div>
      <p style={{ fontSize: 12, opacity: 0.7 }}>Iniciando...</p>
      <style>{`
        @keyframes splashLoading {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(400%); }
        }
      `}</style>
    </div>
  );
}
