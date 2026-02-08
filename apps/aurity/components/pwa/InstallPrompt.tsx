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
      <div className="pwa-toast-wrapper">
        <div className="pwa-toast-card">
          <div className="pwa-toast-row">
            <IconBadge />
            <div className="flex-1 min-w-0">
              <Title />
              <p className="text-slate-400 text-sm mt-1">
                Agrega esta app a tu pantalla de inicio
              </p>
              <div className="pwa-ios-steps">
                <span>Toca</span>
                <Share className="w-4 h-4 text-blue-400" />
                <span>y luego</span>
                <span className="pwa-ios-badge">
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
    <div className="pwa-toast-wrapper">
      <div className="pwa-toast-card">
        <div className="pwa-toast-row">
          <IconBadge />
          <div className="flex-1 min-w-0">
            <Title />
            <p className="text-slate-400 text-sm mt-1">
              Instala la app para acceso rapido y uso offline
            </p>
            <div className="pwa-btn-row">
              <button
                onClick={handleInstall}
                className="pwa-btn-install"
              >
                Instalar
              </button>
              <button
                onClick={handleDismiss}
                className="pwa-btn-dismiss"
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
    <div className="pwa-icon-badge">
      <Download className="w-6 h-6 text-white" />
    </div>
  );
}

function Title() {
  return <h3 className="pwa-title">Instalar AURITY</h3>;
}

function CloseButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="pwa-btn-close"
      aria-label="Cerrar"
    >
      <X className="w-5 h-5" />
    </button>
  );
}
