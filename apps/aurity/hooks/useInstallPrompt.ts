// =============================================================================
// PWA Install Prompt Hook
// =============================================================================
// Manages the PWA install prompt for Android/Chrome/Desktop
// =============================================================================

import { useState, useEffect, useCallback } from 'react';

interface BeforeInstallPromptEvent extends Event {
  readonly platforms: string[];
  readonly userChoice: Promise<{
    outcome: 'accepted' | 'dismissed';
    platform: string;
  }>;
  prompt(): Promise<void>;
}

interface UseInstallPromptReturn {
  /** Whether the install prompt is available */
  isInstallable: boolean;
  /** Whether the app is already installed */
  isInstalled: boolean;
  /** Whether we're on iOS (needs manual install instructions) */
  isIOS: boolean;
  /** Whether we're in standalone mode (installed PWA) */
  isStandalone: boolean;
  /** Trigger the install prompt */
  promptInstall: () => Promise<boolean>;
  /** Dismiss the install prompt */
  dismissPrompt: () => void;
  /** Platform info */
  platform: 'android' | 'ios' | 'desktop' | 'unknown';
}

export function useInstallPrompt(): UseInstallPromptReturn {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [isInstalled, setIsInstalled] = useState(false);
  const [isStandalone, setIsStandalone] = useState(false);

  // Detect platform
  const detectPlatform = useCallback((): 'android' | 'ios' | 'desktop' | 'unknown' => {
    if (typeof window === 'undefined') return 'unknown';

    const ua = navigator.userAgent.toLowerCase();
    if (/iphone|ipad|ipod/.test(ua)) return 'ios';
    if (/android/.test(ua)) return 'android';
    if (/windows|macintosh|linux/.test(ua)) return 'desktop';
    return 'unknown';
  }, []);

  const [platform] = useState(detectPlatform);
  const isIOS = platform === 'ios';

  useEffect(() => {
    if (typeof window === 'undefined') return;

    // Check if already in standalone mode
    const checkStandalone = () => {
      const standalone =
        window.matchMedia('(display-mode: standalone)').matches ||
        (window.navigator as any).standalone === true ||
        document.referrer.includes('android-app://');

      setIsStandalone(standalone);
      setIsInstalled(standalone);
    };

    checkStandalone();

    // Listen for the beforeinstallprompt event
    const handleBeforeInstallPrompt = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
    };

    // Listen for app installed event
    const handleAppInstalled = () => {
      setIsInstalled(true);
      setDeferredPrompt(null);
      console.log('[PWA] App was installed');
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    window.addEventListener('appinstalled', handleAppInstalled);

    // Check display mode changes
    const mediaQuery = window.matchMedia('(display-mode: standalone)');
    mediaQuery.addEventListener('change', checkStandalone);

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
      window.removeEventListener('appinstalled', handleAppInstalled);
      mediaQuery.removeEventListener('change', checkStandalone);
    };
  }, []);

  const promptInstall = useCallback(async (): Promise<boolean> => {
    if (!deferredPrompt) {
      console.log('[PWA] No install prompt available');
      return false;
    }

    try {
      await deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;

      console.log('[PWA] User choice:', outcome);

      if (outcome === 'accepted') {
        setDeferredPrompt(null);
        return true;
      }

      return false;
    } catch (error) {
      console.error('[PWA] Install prompt error:', error);
      return false;
    }
  }, [deferredPrompt]);

  const dismissPrompt = useCallback(() => {
    setDeferredPrompt(null);
  }, []);

  return {
    isInstallable: deferredPrompt !== null,
    isInstalled,
    isIOS,
    isStandalone,
    promptInstall,
    dismissPrompt,
    platform,
  };
}
