'use client';

import { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import {
  fetchCatalogModels,
  fetchSourcesStatus,
  installModelWithProgress,
  deleteInstalledModel,
  type CatalogModel,
  type CatalogSource,
  type SourcesStatus,
  type InstallProgress,
} from '@/lib/api/catalog';
import { createLLMModel } from '@aurity-standalone/api-client/llm-models';
import type { LLMModelCreate } from '@aurity-standalone/types/llm';
import { toastSuccess, toastError, confirmDialog } from '@/lib/swal';
import type { SourceState, SourceFilter } from '../types';
import { SOURCES, INITIAL_SOURCE_STATES, FEATURED_MODEL_IDS } from '../constants';
import { createLogger } from '@/lib/internal/logger';

const log = createLogger('ModelCatalog');

interface UseModelCatalogOptions {
  isOpen: boolean;
  onModelInstalled?: () => void;
}

export function useModelCatalog({ isOpen, onModelInstalled }: UseModelCatalogOptions) {
  // Progressive loading: per-source state
  const [sourceStates, setSourceStates] = useState<Record<CatalogSource, SourceState>>(
    INITIAL_SOURCE_STATES as Record<CatalogSource, SourceState>
  );
  const [, setSourcesStatus] = useState<SourcesStatus | null>(null);

  // Filters
  const [sourceFilter, setSourceFilter] = useState<SourceFilter>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [maxSizeGb, setMaxSizeGb] = useState<number | undefined>(undefined);

  // Installation tracking
  const [installingModels, setInstallingModels] = useState<Record<string, number>>({});
  const [isSyncing, setIsSyncing] = useState(false);

  // AbortControllers for race condition prevention
  const abortControllersRef = useRef<Record<CatalogSource, AbortController | null>>({
    ollama: null,
    gpt4all: null,
    huggingface: null,
  });

  // Derived State
  const allModels = useMemo(
    () => Object.values(sourceStates).flatMap((s) => s.models),
    [sourceStates]
  );

  const loading = Object.values(sourceStates).some((s) => s.status === 'loading');
  const allLoaded = Object.values(sourceStates).every(
    (s) => s.status === 'loaded' || s.status === 'error'
  );
  const allErrors = Object.values(sourceStates).every((s) => s.status === 'error');

  const models = useMemo(() => {
    if (sourceFilter === 'installed') {
      return allModels.filter((m) => m.is_installed);
    }
    if (sourceFilter !== 'all' && SOURCES.includes(sourceFilter as CatalogSource)) {
      return sourceStates[sourceFilter as CatalogSource].models;
    }
    return allModels;
  }, [allModels, sourceStates, sourceFilter]);

  const installedCount = useMemo(
    () => allModels.filter((m) => m.is_installed).length,
    [allModels]
  );

  const featuredModels = useMemo(
    () => models.filter((m) =>
      FEATURED_MODEL_IDS.some((id) => m.id.toLowerCase().includes(id.toLowerCase()))
    ).slice(0, 3),
    [models]
  );

  const regularModels = useMemo(
    () => models.filter((m) =>
      !FEATURED_MODEL_IDS.some((id) => m.id.toLowerCase().includes(id.toLowerCase()))
    ),
    [models]
  );

  const displayedModels = useMemo(() => {
    if (sourceFilter === 'installed' || searchQuery) {
      return models;
    }
    return regularModels;
  }, [models, regularModels, sourceFilter, searchQuery]);

  // Load a single source
  const loadSource = useCallback(async (source: CatalogSource) => {
    abortControllersRef.current[source]?.abort();
    const controller = new AbortController();
    abortControllersRef.current[source] = controller;

    setSourceStates((prev) => ({
      ...prev,
      [source]: { ...prev[source], status: 'loading', error: undefined },
    }));

    try {
      const response = await fetchCatalogModels({
        source,
        query: searchQuery || undefined,
        max_size_gb: maxSizeGb,
        signal: controller.signal,
      });

      setSourceStates((prev) => ({
        ...prev,
        [source]: { status: 'loaded', models: response.models },
      }));
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') return;
      log.error(`Failed to load source`, { source, error: String(err) });
      setSourceStates((prev) => ({
        ...prev,
        [source]: {
          status: 'error',
          models: [],
          error: err instanceof Error ? err.message : `Error al cargar ${source}`,
        },
      }));
    }
  }, [searchQuery, maxSizeGb]);

  // Load catalog progressively
  const loadCatalog = useCallback(async () => {
    setSourceStates(INITIAL_SOURCE_STATES as Record<CatalogSource, SourceState>);
    fetchSourcesStatus().then(setSourcesStatus).catch((err) => log.error('Failed to fetch sources status', { error: String(err) }));

    if (sourceFilter !== 'all' && sourceFilter !== 'installed') {
      const source = sourceFilter as CatalogSource;
      if (SOURCES.includes(source)) {
        loadSource(source);
        return;
      }
    }

    SOURCES.forEach((source) => loadSource(source));
  }, [sourceFilter, loadSource]);

  // Effect: Load on open
  useEffect(() => {
    if (isOpen) {
      loadCatalog();
    } else {
      SOURCES.forEach((source) => {
        abortControllersRef.current[source]?.abort();
        abortControllersRef.current[source] = null;
      });
    }
  }, [isOpen, loadCatalog]);

  // Cleanup on unmount
  useEffect(() => {
    const currentControllers = abortControllersRef.current;
    return () => {
      SOURCES.forEach((source) => currentControllers[source]?.abort());
    };
  }, []);

  // Update installed status helper
  const updateModelInstalledStatus = useCallback((modelId: string, isInstalled: boolean) => {
    setSourceStates((prev) => {
      const newStates = { ...prev };
      for (const source of SOURCES) {
        newStates[source] = {
          ...newStates[source],
          models: newStates[source].models.map((m) =>
            m.id === modelId ? { ...m, is_installed: isInstalled } : m
          ),
        };
      }
      return newStates;
    });
  }, []);

  // Install handler
  const handleInstall = useCallback((model: CatalogModel) => {
    setInstallingModels((prev) => ({ ...prev, [model.id]: 0 }));

    const handleProgress = (progress: InstallProgress) => {
      setInstallingModels((prev) => ({ ...prev, [model.id]: progress.progress_percent }));
    };

    const handleComplete = async () => {
      setInstallingModels((prev) => {
        const updated = { ...prev };
        delete updated[model.id];
        return updated;
      });
      updateModelInstalledStatus(model.id, true);

      try {
        const llmModelData: LLMModelCreate = {
          id: model.id,
          label: model.name,
          provider: 'ollama',
          cost_tier: 'low',
          max_tokens: 4096,
          context_window: model.context_length || 4096,
          is_active: true,
          description: model.description || `${model.name} (${model.quantization})`,
          size_bytes: model.size_bytes,
          ram_required_gb: model.ram_required_gb || null,
        };
        await createLLMModel(llmModelData);
        toastSuccess(`${model.name} instalado y registrado`);
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : '';
        if (errorMsg.includes('already exists') || errorMsg.includes('duplicate')) {
          toastSuccess(`${model.name} instalado (ya estaba registrado)`);
        } else {
          toastSuccess(`${model.name} instalado (registro manual requerido)`);
        }
      }

      onModelInstalled?.();
    };

    const handleError = (errorMsg: string) => {
      setInstallingModels((prev) => {
        const updated = { ...prev };
        delete updated[model.id];
        return updated;
      });
      toastError(`Error: ${errorMsg}`);
    };

    installModelWithProgress(model.id, handleProgress, handleComplete, handleError);
  }, [onModelInstalled, updateModelInstalledStatus]);

  // Delete handler
  const handleDelete = useCallback(async (model: CatalogModel) => {
    const confirmed = await confirmDialog({
      title: '¿Eliminar modelo?',
      text: `${model.name} será eliminado. Podrás reinstalarlo después.`,
      confirmText: 'Eliminar',
      icon: 'warning',
    });

    if (!confirmed) return;

    try {
      await deleteInstalledModel(model.id);
      updateModelInstalledStatus(model.id, false);
      toastSuccess(`${model.name} eliminado`);
      onModelInstalled?.();
    } catch (err) {
      toastError(err instanceof Error ? err.message : 'Error al eliminar');
    }
  }, [onModelInstalled, updateModelInstalledStatus]);

  // Sync installed models
  const syncInstalledModels = useCallback(async () => {
    const installedModels = allModels.filter((m) => m.is_installed);
    if (installedModels.length === 0) {
      toastError('No hay modelos instalados para sincronizar');
      return;
    }

    setIsSyncing(true);
    let synced = 0, skipped = 0, errors = 0;

    for (const model of installedModels) {
      try {
        const llmModelData: LLMModelCreate = {
          id: model.id,
          label: model.name,
          provider: 'ollama',
          cost_tier: 'low',
          max_tokens: 4096,
          context_window: model.context_length || 4096,
          is_active: true,
          description: model.description || `${model.name} (${model.quantization})`,
          size_bytes: model.size_bytes,
          ram_required_gb: model.ram_required_gb || null,
        };
        await createLLMModel(llmModelData);
        synced++;
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : '';
        if (errorMsg.includes('already exists') || errorMsg.includes('duplicate')) {
          skipped++;
        } else {
          errors++;
        }
      }
    }

    setIsSyncing(false);

    if (synced > 0) {
      toastSuccess(`Sincronizados: ${synced} nuevos${skipped > 0 ? `, ${skipped} existentes` : ''}`);
      onModelInstalled?.();
    } else if (skipped > 0) {
      toastSuccess(`Todos los ${skipped} modelos ya estaban registrados`);
    } else {
      toastError(`Error al sincronizar (${errors} errores)`);
    }
  }, [allModels, onModelInstalled]);

  return {
    // State
    sourceStates,
    sourceFilter,
    searchQuery,
    maxSizeGb,
    installingModels,
    isSyncing,
    // Derived
    allModels,
    models,
    displayedModels,
    featuredModels,
    installedCount,
    loading,
    allLoaded,
    allErrors,
    // Actions
    setSourceFilter,
    setSearchQuery,
    setMaxSizeGb,
    loadCatalog,
    handleInstall,
    handleDelete,
    syncInstalledModels,
  };
}
