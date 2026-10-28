'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  defaultModelCatalogConfirm,
  errorMessage,
  silentNotify,
  type LLMModel,
  type LLMProvider,
  type ModelCatalogConfirm,
  type ModelCatalogNotify,
  type ModelCatalogStore,
} from './types';

export interface UseLLMModelsOptions {
  confirm?: ModelCatalogConfirm;
  notify?: ModelCatalogNotify;
  deactivateConfirmMessage?: (model: LLMModel) => string;
}

export interface LLMModelCollection {
  models: LLMModel[];
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
  selectedId: string | null;
  setSelectedId: (modelId: string | null) => void;
  includeInactive: boolean;
  setIncludeInactive: (value: boolean) => void;
  provider: LLMProvider | '';
  setProvider: (value: LLMProvider | '') => void;
  /** Insert or replace by id (after a create or an edit). */
  upsert: (model: LLMModel) => void;
  /** Confirms, then soft-deletes through `store.deactivateModel`. Resolves true only if it happened. */
  deactivate: (model: LLMModel) => Promise<boolean>;
  toggleActive: (model: LLMModel) => Promise<void>;
  actionError: string | null;
  clearActionError: () => void;
}

export const defaultDeactivateMessage = (model: LLMModel) =>
  `¿Eliminar el modelo "${model.id}"?\n\nEl modelo será desactivado y dejará de estar disponible para las personas.`;

export function useLLMModels(
  store: Pick<ModelCatalogStore, 'listModels' | 'updateModel' | 'deactivateModel'>,
  {
    confirm = defaultModelCatalogConfirm,
    notify = silentNotify,
    deactivateConfirmMessage = defaultDeactivateMessage,
  }: UseLLMModelsOptions = {},
): LLMModelCollection {
  const storeRef = useRef(store);
  storeRef.current = store;
  const [models, setModels] = useState<LLMModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [includeInactive, setIncludeInactive] = useState(false);
  const [provider, setProvider] = useState<LLMProvider | ''>('');

  const requestSeq = useRef(0);

  const reload = useCallback(async () => {
    const seq = ++requestSeq.current;
    setLoading(true);
    setError(null);
    try {
      const list = await storeRef.current.listModels({ includeInactive, provider: provider || undefined });
      if (seq === requestSeq.current) setModels(list);
    } catch (err) {
      if (seq === requestSeq.current) setError(errorMessage(err, 'Error al cargar los modelos'));
    } finally {
      if (seq === requestSeq.current) setLoading(false);
    }
  }, [includeInactive, provider]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const replace = useCallback((model: LLMModel) => {
    setModels((prev) =>
      prev.some((m) => m.id === model.id) ? prev.map((m) => (m.id === model.id ? model : m)) : [...prev, model],
    );
  }, []);

  const fail = useCallback(
    (err: unknown, fallback: string) => {
      const message = errorMessage(err, fallback);
      setActionError(message);
      notify('error', message);
    },
    [notify],
  );

  const deactivate = useCallback(
    async (model: LLMModel) => {
      if (!(await confirm(deactivateConfirmMessage(model)))) return false;
      setActionError(null);
      try {
        await storeRef.current.deactivateModel(model.id);
        setModels((prev) => prev.map((m) => (m.id === model.id ? { ...m, is_active: false } : m)));
        setSelectedId((current) => (current === model.id ? null : current));
        notify('success', 'Modelo desactivado correctamente');
        return true;
      } catch (err) {
        fail(err, 'Error al eliminar el modelo');
        return false;
      }
    },
    [confirm, deactivateConfirmMessage, notify, fail],
  );

  const toggleActive = useCallback(
    async (model: LLMModel) => {
      setActionError(null);
      try {
        const updated = await storeRef.current.updateModel(model.id, { is_active: !model.is_active });
        replace(updated);
        notify('success', updated.is_active ? 'Modelo activado' : 'Modelo desactivado');
      } catch (err) {
        fail(err, 'Error al cambiar el estado del modelo');
      }
    },
    [replace, notify, fail],
  );

  return {
    models,
    loading,
    error,
    reload,
    selectedId,
    setSelectedId,
    includeInactive,
    setIncludeInactive,
    provider,
    setProvider,
    upsert: replace,
    deactivate,
    toggleActive,
    actionError,
    clearActionError: useCallback(() => setActionError(null), []),
  };
}
