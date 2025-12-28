// =============================================================================
// Online Status Hook
// =============================================================================
// Tracks network connectivity status for offline-first functionality
// =============================================================================

import { useState, useEffect, useCallback } from 'react';

interface UseOnlineStatusReturn {
  /** Whether the device is online */
  isOnline: boolean;
  /** Whether the device was recently offline (for sync indicators) */
  wasOffline: boolean;
  /** Timestamp of last online state */
  lastOnline: Date | null;
  /** Manually check connection by pinging a URL */
  checkConnection: () => Promise<boolean>;
}

export function useOnlineStatus(): UseOnlineStatusReturn {
  const [isOnline, setIsOnline] = useState(() => {
    if (typeof window === 'undefined') return true;
    return navigator.onLine;
  });
  const [wasOffline, setWasOffline] = useState(false);
  const [lastOnline, setLastOnline] = useState<Date | null>(null);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const handleOnline = () => {
      setIsOnline(true);
      setLastOnline(new Date());
      // Keep wasOffline true for a short time to show sync indicator
      setTimeout(() => setWasOffline(false), 5000);
    };

    const handleOffline = () => {
      setIsOnline(false);
      setWasOffline(true);
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Set initial lastOnline if online
    if (navigator.onLine) {
      setLastOnline(new Date());
    }

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  const checkConnection = useCallback(async (): Promise<boolean> => {
    try {
      // Try to fetch a small resource to verify actual connectivity
      const response = await fetch('/manifest.json', {
        method: 'HEAD',
        cache: 'no-store',
      });
      const online = response.ok;
      setIsOnline(online);
      if (online) setLastOnline(new Date());
      return online;
    } catch {
      setIsOnline(false);
      return false;
    }
  }, []);

  return {
    isOnline,
    wasOffline,
    lastOnline,
    checkConnection,
  };
}
