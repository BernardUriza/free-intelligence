"use client";

import { useEffect, useState } from 'react';
import { shouldUseMocks, startMockWorker } from '@/mocks/startMockWorker';

/**
 * Starts MSW in the browser when mock flags are enabled.
 * Flags: NEXT_PUBLIC_USE_MOCKS, NEXT_PUBLIC_MOCK_BACKEND, or localStorage.USE_MOCKS === 'true'
 */
export function MockBootstrap() {
  const [enabled, setEnabled] = useState(false);

  useEffect(() => {
    const active = shouldUseMocks();
    setEnabled(active);
    if (!active) return;

    startMockWorker().catch((err) => {
      console.error('[MockBootstrap] Failed to start MSW', err);
    });
  }, []);

  if (!enabled) return null;
  return null;
}
