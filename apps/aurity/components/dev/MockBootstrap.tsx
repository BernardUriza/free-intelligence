"use client";

import { useEffect, useState } from 'react';
import { createLogger } from '@/lib/internal/logger';
import { shouldUseMocks, startMockWorker } from '@/mocks/startMockWorker';

const log = createLogger('MockBootstrap');

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
      log.error('Failed to start MSW', { error: String(err) });
    });
  }, []);

  if (!enabled) return null;
  return null;
}
