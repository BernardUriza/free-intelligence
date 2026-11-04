'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { CATALOG_SOURCES, catalogModelToCreate, isAlreadyRegisteredError, isFeaturedModel } from './format';
import {
  defaultModelCatalogConfirm,
  errorMessage,
  silentNotify,
  type CatalogModel,
  type CatalogSource,
  type ModelCatalogConfirm,
  type ModelCatalogNotify,
  type ModelCatalogStore,
} from './types';

export type CatalogFilter = CatalogSource | 'all' | 'installed';

export type CatalogSourceStatus = 'idle' | 'loading' | 'loaded' | 'error';

export interface CatalogSourceState {
  status: CatalogSourceStatus;
  models: CatalogModel[];
  error?: string;
}

export interface UseModelCatalogOptions {
  /** The catalog loads when this turns true and aborts in-flight listings when it turns false. */
  open: boolean;
  /** Called after an install, removal or sync changed what the registry holds. */
  onModelsChanged?: () => void;
  confirm?: ModelCatalogConfirm;
  notify?: ModelCatalogNotify;
  removeConfirmMessage?: (model: CatalogModel) => string;
}

export const defaultRemoveCatalogMessage = (model: CatalogModel) =>
  `¿Eliminar ${model.name}?\n\nSe borrará del disco. Podrás reinstalarlo después.`;

const SEARCH_DEBOUNCE_MS = 300;

const idleStates = (): Record<CatalogSource, CatalogSourceState> => ({
  ollama: { status: 'idle', models: [] },
  gpt4all: { status: 'idle', models: [] },
  huggingface: { status: 'idle', models: [] },
});

export function useModelCatalog(
  store: Pick<ModelCatalogStore, 'listCatalog' | 'installCatalogModel' | 'removeCatalogModel' | 'createModel'>,
  {
    open,
    onModelsChanged,
    confirm = defaultModelCatalogConfirm,
    notify = silentNotify,
    removeConfirmMessage = defaultRemoveCatalogMessage,
  }: UseModelCatalogOptions,
) {
  const storeRef = useRef(store);
  storeRef.current = store;
  const changedRef = useRef(onModelsChanged);
  changedRef.current = onModelsChanged;
  const [sourceStates, setSourceStates] = useState(idleStates);
  const [filter, setFilter] = useState<CatalogFilter>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [fetchQuery, setFetchQuery] = useState('');
  const [maxSizeGb, setMaxSizeGb] = useState<number | undefined>(undefined);
  const [installing, setInstalling] = useState<Record<string, number>>({});
  const [installErrors, setInstallErrors] = useState<Record<string, string>>({});
  const [syncing, setSyncing] = useState(false);
  const listAborts = useRef<Partial<Record<CatalogSource, AbortController>>>({});
  const installAborts = useRef<Record<string, AbortController>>({});

  const allModels = useMemo(() => CATALOG_SOURCES.flatMap((s) => sourceStates[s].models), [sourceStates]);
  const statuses = CATALOG_SOURCES.map((s) => sourceStates[s].status);
  const loading = statuses.includes('loading');
  const allLoaded = statuses.every((s) => s === 'loaded' || s === 'error');
  const allErrors = statuses.every((s) => s === 'error');

  const models = useMemo(() => {
    if (filter === 'installed') return allModels.filter((m) => m.is_installed);
    if (filter !== 'all') return sourceStates[filter].models;
    return allModels;
  }, [allModels, sourceStates, filter]);

  const installedCount = useMemo(() => allModels.filter((m) => m.is_installed).length, [allModels]);
  const showFeatured = filter === 'all' && !searchQuery;
  const featuredModels = useMemo(
    () => (showFeatured ? models.filter(isFeaturedModel).slice(0, 3) : []),
    [models, showFeatured],
  );
  const displayedModels = useMemo(
    () => (showFeatured ? models.filter((m) => !isFeaturedModel(m)) : models),
    [models, showFeatured],
  );

  const loadSource = useCallback(
    async (source: CatalogSource) => {
      listAborts.current[source]?.abort();
      const controller = new AbortController();
      listAborts.current[source] = controller;
      setSourceStates((prev) => ({ ...prev, [source]: { ...prev[source], status: 'loading', error: undefined } }));
      try {
        const list = await storeRef.current.listCatalog({
          source,
          query: fetchQuery || undefined,
          maxSizeGb,
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        setSourceStates((prev) => ({ ...prev, [source]: { status: 'loaded', models: list } }));
      } catch (err) {
        if (controller.signal.aborted || (err instanceof Error && err.name === 'AbortError')) return;
        setSourceStates((prev) => ({
          ...prev,
          [source]: { status: 'error', models: [], error: errorMessage(err, `Error al cargar ${source}`) },
        }));
      }
    },
    [fetchQuery, maxSizeGb],
  );

  const reload = useCallback(() => {
    CATALOG_SOURCES.forEach((source) => void loadSource(source));
  }, [loadSource]);

  useEffect(() => {
    const timer = setTimeout(() => setFetchQuery(searchQuery.trim()), SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  useEffect(() => {
    if (open) {
      reload();
      return;
    }
    for (const source of CATALOG_SOURCES) listAborts.current[source]?.abort();
  }, [open, reload]);

  useEffect(() => {
    const lists = listAborts.current;
    const installs = installAborts.current;
    return () => {
      Object.values(lists).forEach((c) => c?.abort());
      Object.values(installs).forEach((c) => c.abort());
    };
  }, []);

  const markInstalled = useCallback((modelId: string, isInstalled: boolean) => {
    setSourceStates((prev) => {
      const next = { ...prev };
      for (const source of CATALOG_SOURCES) {
        next[source] = {
          ...next[source],
          models: next[source].models.map((m) => (m.id === modelId ? { ...m, is_installed: isInstalled } : m)),
        };
      }
      return next;
    });
  }, []);

  const dropInstalling = (modelId: string) =>
    setInstalling((prev) => {
      const next = { ...prev };
      delete next[modelId];
      return next;
    });

  const install = useCallback(
    async (model: CatalogModel) => {
      if (model.id in installAborts.current) return;
      const controller = new AbortController();
      installAborts.current[model.id] = controller;
      setInstalling((prev) => ({ ...prev, [model.id]: 0 }));
      setInstallErrors((prev) => {
        const next = { ...prev };
        delete next[model.id];
        return next;
      });
      try {
        await storeRef.current.installCatalogModel(model.id, {
          signal: controller.signal,
          onProgress: (p) => setInstalling((prev) => ({ ...prev, [model.id]: p.progress_percent })),
        });
      } catch (err) {
        delete installAborts.current[model.id];
        if (controller.signal.aborted) return;
        dropInstalling(model.id);
        const message = errorMessage(err, 'Error al instalar el modelo');
        setInstallErrors((prev) => ({ ...prev, [model.id]: message }));
        notify('error', `${model.name}: ${message}`);
        return;
      }
      delete installAborts.current[model.id];
      dropInstalling(model.id);
      markInstalled(model.id, true);
      try {
        await storeRef.current.createModel(catalogModelToCreate(model));
        notify('success', `${model.name} instalado y registrado`);
      } catch (err) {
        notify(
          'success',
          isAlreadyRegisteredError(err)
            ? `${model.name} instalado (ya estaba registrado)`
            : `${model.name} instalado (registro manual requerido)`,
        );
      }
      changedRef.current?.();
    },
    [markInstalled, notify],
  );

  const remove = useCallback(
    async (model: CatalogModel) => {
      if (!(await confirm(removeConfirmMessage(model)))) return false;
      try {
        await storeRef.current.removeCatalogModel(model.id);
        markInstalled(model.id, false);
        notify('success', `${model.name} eliminado`);
        changedRef.current?.();
        return true;
      } catch (err) {
        const message = errorMessage(err, 'Error al eliminar');
        setInstallErrors((prev) => ({ ...prev, [model.id]: message }));
        notify('error', message);
        return false;
      }
    },
    [confirm, removeConfirmMessage, markInstalled, notify],
  );

  const syncInstalled = useCallback(async () => {
    const installed = allModels.filter((m) => m.is_installed);
    if (installed.length === 0) {
      notify('error', 'No hay modelos instalados para sincronizar');
      return;
    }
    setSyncing(true);
    let synced = 0;
    let skipped = 0;
    let failed = 0;
    for (const model of installed) {
      try {
        await storeRef.current.createModel(catalogModelToCreate(model));
        synced += 1;
      } catch (err) {
        if (isAlreadyRegisteredError(err)) skipped += 1;
        else failed += 1;
      }
    }
    setSyncing(false);
    if (synced > 0) {
      notify('success', `Sincronizados: ${synced} nuevos${skipped > 0 ? `, ${skipped} existentes` : ''}`);
      changedRef.current?.();
    } else if (skipped > 0) {
      notify('success', `Todos los ${skipped} modelos ya estaban registrados`);
    } else {
      notify('error', `Error al sincronizar (${failed} errores)`);
    }
  }, [allModels, notify]);

  return {
    sourceStates,
    filter,
    setFilter,
    searchQuery,
    setSearchQuery,
    maxSizeGb,
    setMaxSizeGb,
    installing,
    installErrors,
    syncing,
    allModels,
    models,
    featuredModels,
    displayedModels,
    installedCount,
    loading,
    allLoaded,
    allErrors,
    reload,
    install,
    remove,
    syncInstalled,
  };
}

export type ModelCatalogState = ReturnType<typeof useModelCatalog>;
