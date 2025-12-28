/**
 * useBackendHealth Hook
 *
 * React hook to track backend availability.
 * Initializes health check on first use and provides reactive state.
 *
 * Usage:
 *   const { isAvailable, check } = useBackendHealth();
 *
 *   if (!isAvailable) {
 *     return <OfflineMessage />;
 *   }
 *
 * File: apps/aurity/hooks/useBackendHealth.ts
 * Created: 2025-11-26
 */

import { useState, useEffect, useCallback } from 'react';
import { backendHealth } from '@aurity-standalone/api-client/backend-health';

interface UseBackendHealthReturn {
  /** Whether backend is currently available */
  isAvailable: boolean;
  /** Force a health check */
  check: () => Promise<boolean>;
}

export function useBackendHealth(): UseBackendHealthReturn {
  const [isAvailable, setIsAvailable] = useState(false);

  useEffect(() => {
    // Initialize and subscribe
    backendHealth.initialize();

    const unsubscribe = backendHealth.subscribe((available) => {
      setIsAvailable(available);
    });

    return unsubscribe;
  }, []);

  const check = useCallback(async () => {
    return backendHealth.check();
  }, []);

  return {
    isAvailable,
    check,
  };
}
