'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  errorMessage,
  silentNotify,
  type ModelCatalogNotify,
  type ModelCatalogStore,
  type RunningModelsResponse,
  type SystemResources,
} from './types';

export interface UseSystemResourcesOptions {
  /** 0 disables polling. */
  pollIntervalMs?: number;
  notify?: ModelCatalogNotify;
}

export interface SystemResourcesState {
  resources: SystemResources | null;
  running: RunningModelsResponse | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  unload: (modelName: string) => Promise<void>;
  unloading: string | null;
}

export function useSystemResources(
  store: Pick<ModelCatalogStore, 'getSystemResources' | 'listRunningModels' | 'unloadRunningModel'>,
  { pollIntervalMs = 10_000, notify = silentNotify }: UseSystemResourcesOptions = {},
): SystemResourcesState {
  const storeRef = useRef(store);
  storeRef.current = store;
  const [resources, setResources] = useState<SystemResources | null>(null);
  const [running, setRunning] = useState<RunningModelsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [unloading, setUnloading] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [nextResources, nextRunning] = await Promise.all([
        storeRef.current.getSystemResources(),
        storeRef.current.listRunningModels(),
      ]);
      setResources(nextResources);
      setRunning(nextRunning);
      setError(null);
    } catch (err) {
      setError(errorMessage(err, 'No se pudieron cargar los recursos del sistema'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    if (!pollIntervalMs) return;
    const timer = setInterval(() => void refresh(), pollIntervalMs);
    return () => clearInterval(timer);
  }, [refresh, pollIntervalMs]);

  const unload = useCallback(
    async (modelName: string) => {
      setUnloading(modelName);
      try {
        await storeRef.current.unloadRunningModel(modelName);
        notify('success', `Modelo ${modelName} descargado de memoria`);
        await refresh();
      } catch (err) {
        const message = errorMessage(err, 'Error al descargar el modelo de memoria');
        setError(message);
        notify('error', message);
      } finally {
        setUnloading(null);
      }
    },
    [notify, refresh],
  );

  return { resources, running, loading, error, refresh, unload, unloading };
}
