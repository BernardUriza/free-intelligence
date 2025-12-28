'use client';

// =============================================================================
// PWA Install Prompt Component - SOLID Refactor
// =============================================================================
// Single Responsibility: Only handles UI for install prompt
// Dependency Inversion: Uses context instead of direct hook calls
// =============================================================================

import { useState, useEffect } from 'react';
import { usePWAInstall } from '@/lib/pwa/context';
import { X, Download, Share, Plus } from 'lucide-react';

const DISMISS_STORAGE_KEY = 'pwa-install-dismissed';
const DISMISS_DURATION_MS = 7 * 24 * 60 * 60 * 1000; // 7 days

export function InstallPrompt() {
  const {
    isInstallable,
    isInstalled,
    isIOS,
    isStandalone,
    promptInstall,
    dismissInstallPrompt,
    enabled,
  } = usePWAInstall();

  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    if (!enabled) return;

    // Check if previously dismissed
    const dismissedTime = localStorage.getItem(DISMISS_STORAGE_KEY);
    if (dismissedTime && Date.now() - parseInt(dismissedTime, 10) < DISMISS_DURATION_MS) {
      return;
    }

    // Show after delay if conditions met
    const timer = setTimeout(() => {
      if (!isInstalled && !isStandalone && (isInstallable || isIOS)) {
        setIsVisible(true);
      }
    }, 5000);

    return () => clearTimeout(timer);
  }, [enabled, isInstallable, isInstalled, isIOS, isStandalone]);

  const handleInstall = async () => {
    const success = await promptInstall();
    if (success) setIsVisible(false);
  };

  const handleDismiss = () => {
    setIsVisible(false);
    dismissInstallPrompt();
    localStorage.setItem(DISMISS_STORAGE_KEY, String(Date.now()));
  };

  if (!isVisible || !enabled) return null;

  // iOS: Manual instructions
  if (isIOS) {
    return (
      <div className="fixed bottom-4 left-4 right-4 z-50 animate-in slide-in-from-bottom duration-300">
        <div className="bg-slate-800 border border-slate-700 rounded-2xl p-4 shadow-xl">
          <div className="flex items-start gap-3">
            <IconBadge />
            <div className="flex-1 min-w-0">
              <Title />
              <p className="text-slate-400 text-sm mt-1">
                Agrega esta app a tu pantalla de inicio
              </p>
              <div className="mt-3 flex items-center gap-2 text-slate-300 text-sm">
                <span>Toca</span>
                <Share className="w-4 h-4 text-blue-400" />
                <span>y luego</span>
                <span className="inline-flex items-center gap-1 bg-slate-700 px-2 py-0.5 rounded">
                  <Plus className="w-3 h-3" />
                  <span>Agregar</span>
                </span>
              </div>
            </div>
            <CloseButton onClick={handleDismiss} />
          </div>
        </div>
      </div>
    );
  }

  // Android/Chrome/Desktop
  return (
    <div className="fixed bottom-4 left-4 right-4 z-50 animate-in slide-in-from-bottom duration-300">
      <div className="bg-slate-800 border border-slate-700 rounded-2xl p-4 shadow-xl">
        <div className="flex items-start gap-3">
          <IconBadge />
          <div className="flex-1 min-w-0">
            <Title />
            <p className="text-slate-400 text-sm mt-1">
              Instala la app para acceso rapido y uso offline
            </p>
            <div className="mt-3 flex gap-2">
              <button
                onClick={handleInstall}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors"
              >
                Instalar
              </button>
              <button
                onClick={handleDismiss}
                className="px-4 py-2 text-slate-400 hover:text-slate-300 text-sm font-medium transition-colors"
              >
                Ahora no
              </button>
            </div>
          </div>
          <CloseButton onClick={handleDismiss} />
        </div>
      </div>
    </div>
  );
}

// Sub-components (Single Responsibility)
function IconBadge() {
  return (
    <div className="flex-shrink-0 w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center">
      <Download className="w-6 h-6 text-white" />
    </div>
  );
}

function Title() {
  return <h3 className="text-white font-semibold text-base">Instalar AURITY</h3>;
}

function CloseButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="flex-shrink-0 p-1 text-slate-500 hover:text-slate-300 transition-colors"
      aria-label="Cerrar"
    >
      <X className="w-5 h-5" />
    </button>
  );
}
