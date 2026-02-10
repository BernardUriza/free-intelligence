'use client';

import { useState, useEffect, useCallback } from 'react';
import { ROUTES } from '@/lib/api/routes';

type ServiceStatus = 'online' | 'offline' | 'checking';

interface SystemHealth {
  ollama: ServiceStatus;
  backend: ServiceStatus;
  isHealthy: boolean;
}

const POLL_INTERVAL = 30000; // 30 seconds

export function useSystemHealth() {
  const [health, setHealth] = useState<SystemHealth>({
    ollama: 'checking',
    backend: 'checking',
    isHealthy: false,
  });

  const checkHealth = useCallback(async () => {
    const results = await Promise.allSettled([
      fetch('http://localhost:11434/api/tags'),
      fetch(ROUTES.healthRoot),
    ]);

    const ollama: ServiceStatus = results[0].status === 'fulfilled' && results[0].value.ok ? 'online' : 'offline';
    const backend: ServiceStatus = results[1].status === 'fulfilled' && results[1].value.ok ? 'online' : 'offline';

    setHealth({
      ollama,
      backend,
      isHealthy: ollama === 'online' && backend === 'online',
    });
  }, []);

  useEffect(() => {
    checkHealth();
    const intervalId = setInterval(checkHealth, POLL_INTERVAL);
    return () => clearInterval(intervalId);
  }, [checkHealth]);

  return { ...health, refresh: checkHealth };
}

export default useSystemHealth;
