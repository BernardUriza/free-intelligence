/**
 * useSystemResources Hook
 *
 * Single Responsibility: System resource monitoring — RAM, CPU, running Ollama
 * models, and model unloading. Polls every 10 seconds.
 *
 * Route: /admin/models
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  fetchSystemResources,
  fetchRunningModels,
  unloadModel,
  type SystemResources,
  type RunningModelsResponse,
} from '@/lib/api/system';
import { toastSuccess, toastError } from '@/lib/swal';

const POLL_INTERVAL_MS = 10_000;

export function useSystemResources() {
  const [systemResources, setSystemResources] = useState<SystemResources | null>(null);
  const [runningModels, setRunningModels] = useState<RunningModelsResponse | null>(null);
  const [resourcesLoading, setResourcesLoading] = useState(true);

  const loadResources = useCallback(async () => {
    try {
      setResourcesLoading(true);
      const [resources, running] = await Promise.all([
        fetchSystemResources(),
        fetchRunningModels(),
      ]);
      setSystemResources(resources);
      setRunningModels(running);
    } catch (err) {
      console.error('Failed to load system resources:', err);
    } finally {
      setResourcesLoading(false);
    }
  }, []);

  useEffect(() => {
    loadResources();
    const interval = setInterval(loadResources, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [loadResources]);

  const handleUnloadModel = useCallback(async (modelName: string) => {
    try {
      await unloadModel(modelName);
      toastSuccess(`Modelo ${modelName} descargado de memoria`);
      await loadResources();
    } catch (err) {
      toastError(err instanceof Error ? err.message : 'Error al descargar modelo');
    }
  }, [loadResources]);

  return {
    systemResources,
    runningModels,
    resourcesLoading,
    loadResources,
    handleUnloadModel,
  } as const;
}
