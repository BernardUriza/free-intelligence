'use client';

// =============================================================================
// PWA Context - SOLID Architecture
// =============================================================================
// Single Responsibility: Manages PWA state and provides it to the app
// Open/Closed: Extensible via configuration without modifying core
// Dependency Inversion: Components depend on context, not implementations
// =============================================================================

import React, { createContext, useContext, useEffect, useMemo, ReactNode } from 'react';
import { useInstallPrompt } from '@/hooks/useInstallPrompt';
import { useOnlineStatus } from '@/hooks/useOnlineStatus';
import { useServiceWorker } from '@/hooks/useServiceWorker';
import { initSyncManager } from './sync';

// =============================================================================
// Types & Interfaces
// =============================================================================

export interface PWAConfig {
  /** Enable install prompt */
  enableInstallPrompt?: boolean;
  /** Enable offline indicator */
  enableOfflineIndicator?: boolean;
  /** Enable update notifications */
  enableUpdatePrompt?: boolean;
  /** Delay before showing install prompt (ms) */
  installPromptDelay?: number;
  /** Show iOS manual install instructions */
  showIOSInstructions?: boolean;
  /** Position for offline indicator */
  offlineIndicatorPosition?: 'top' | 'bottom';
}

export interface PWAState {
  // Install state
  isInstallable: boolean;
  isInstalled: boolean;
  isIOS: boolean;
  isStandalone: boolean;
  platform: 'android' | 'ios' | 'desktop' | 'unknown';
  promptInstall: () => Promise<boolean>;
  dismissInstallPrompt: () => void;

  // Online state
  isOnline: boolean;
  wasOffline: boolean;
  lastOnline: Date | null;
  checkConnection: () => Promise<boolean>;

  // Service Worker state
  swRegistered: boolean;
  updateAvailable: boolean;
  swInstalling: boolean;
  updateServiceWorker: () => Promise<void>;
  skipWaiting: () => void;

  // Config
  config: Required<PWAConfig>;
}

// =============================================================================
// Default Configuration
// =============================================================================

const defaultConfig: Required<PWAConfig> = {
  enableInstallPrompt: true,
  enableOfflineIndicator: true,
  enableUpdatePrompt: true,
  installPromptDelay: 5000,
  showIOSInstructions: true,
  offlineIndicatorPosition: 'top',
};

// =============================================================================
// Context
// =============================================================================

const PWAContext = createContext<PWAState | null>(null);

// =============================================================================
// Provider Component
// =============================================================================

interface PWAProviderProps {
  children: ReactNode;
  config?: PWAConfig;
}

export function PWAProvider({ children, config: userConfig }: PWAProviderProps) {
  // Merge user config with defaults
  const config = useMemo(
    () => ({ ...defaultConfig, ...userConfig }),
    [userConfig]
  );

  // Use hooks
  const installPrompt = useInstallPrompt();
  const onlineStatus = useOnlineStatus();
  const serviceWorker = useServiceWorker();

  // Initialize sync manager
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const cleanup = initSyncManager();
    return cleanup;
  }, []);

  // Compose state
  const state = useMemo<PWAState>(
    () => ({
      // Install
      isInstallable: installPrompt.isInstallable,
      isInstalled: installPrompt.isInstalled,
      isIOS: installPrompt.isIOS,
      isStandalone: installPrompt.isStandalone,
      platform: installPrompt.platform,
      promptInstall: installPrompt.promptInstall,
      dismissInstallPrompt: installPrompt.dismissPrompt,

      // Online
      isOnline: onlineStatus.isOnline,
      wasOffline: onlineStatus.wasOffline,
      lastOnline: onlineStatus.lastOnline,
      checkConnection: onlineStatus.checkConnection,

      // Service Worker
      swRegistered: serviceWorker.isRegistered,
      updateAvailable: serviceWorker.updateAvailable,
      swInstalling: serviceWorker.isInstalling,
      updateServiceWorker: serviceWorker.update,
      skipWaiting: serviceWorker.skipWaiting,

      // Config
      config,
    }),
    [installPrompt, onlineStatus, serviceWorker, config]
  );

  return <PWAContext.Provider value={state}>{children}</PWAContext.Provider>;
}

// =============================================================================
// Hook
// =============================================================================

export function usePWA(): PWAState {
  const context = useContext(PWAContext);

  if (!context) {
    throw new Error('usePWA must be used within a PWAProvider');
  }

  return context;
}

// =============================================================================
// Selective Hooks (Interface Segregation)
// =============================================================================

export function usePWAInstall() {
  const { isInstallable, isInstalled, isIOS, isStandalone, platform, promptInstall, dismissInstallPrompt, config } = usePWA();
  return { isInstallable, isInstalled, isIOS, isStandalone, platform, promptInstall, dismissInstallPrompt, enabled: config.enableInstallPrompt };
}

export function usePWAOnline() {
  const { isOnline, wasOffline, lastOnline, checkConnection, config } = usePWA();
  return { isOnline, wasOffline, lastOnline, checkConnection, enabled: config.enableOfflineIndicator };
}

export function usePWAUpdate() {
  const { updateAvailable, swInstalling, skipWaiting, updateServiceWorker, config } = usePWA();
  return { updateAvailable, swInstalling, skipWaiting, updateServiceWorker, enabled: config.enableUpdatePrompt };
}
