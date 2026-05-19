// =============================================================================
// Service Worker Hook
// =============================================================================
// Manages service worker registration and updates
// =============================================================================

import { useState, useEffect, useCallback } from 'react';
import { createLogger } from '@/lib/internal/logger';

const log = createLogger('ServiceWorker');

interface UseServiceWorkerReturn {
  /** Whether the service worker is registered */
  isRegistered: boolean;
  /** Whether an update is available */
  updateAvailable: boolean;
  /** Whether the service worker is installing */
  isInstalling: boolean;
  /** Registration object */
  registration: ServiceWorkerRegistration | null;
  /** Update the service worker */
  update: () => Promise<void>;
  /** Skip waiting and activate new service worker */
  skipWaiting: () => void;
}

export function useServiceWorker(): UseServiceWorkerReturn {
  const [registration, setRegistration] = useState<ServiceWorkerRegistration | null>(null);
  const [isRegistered, setIsRegistered] = useState(false);
  const [updateAvailable, setUpdateAvailable] = useState(false);
  const [isInstalling, setIsInstalling] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined' || !('serviceWorker' in navigator)) {
      return;
    }

    const registerSW = async () => {
      try {
        const reg = await navigator.serviceWorker.register('/sw.js');
        setRegistration(reg);
        setIsRegistered(true);

        log.info('Registered', { scope: reg.scope });

        // Check for updates
        reg.addEventListener('updatefound', () => {
          const newWorker = reg.installing;
          if (!newWorker) return;

          setIsInstalling(true);

          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed') {
              setIsInstalling(false);
              if (navigator.serviceWorker.controller) {
                // New update available
                setUpdateAvailable(true);
                log.info('New version available');
              }
            }
          });
        });
      } catch (error) {
        log.error('Registration failed', { error: String(error) });
      }
    };

    // Check if already registered
    navigator.serviceWorker.getRegistration().then((existingReg) => {
      if (existingReg) {
        setRegistration(existingReg);
        setIsRegistered(true);
      } else {
        registerSW();
      }
    });

    // Listen for controller change (new SW activated)
    navigator.serviceWorker.addEventListener('controllerchange', () => {
      log.info('Controller changed, reloading');
      window.location.reload();
    });
  }, []);

  const update = useCallback(async () => {
    if (registration) {
      await registration.update();
    }
  }, [registration]);

  const skipWaiting = useCallback(() => {
    if (registration?.waiting) {
      registration.waiting.postMessage({ type: 'SKIP_WAITING' });
    }
  }, [registration]);

  return {
    isRegistered,
    updateAvailable,
    isInstalling,
    registration,
    update,
    skipWaiting,
  };
}
