/**
 * useLLMModels Hook
 *
 * Single Responsibility: LLM model list CRUD — load, create, update, delete,
 * toggle active status. Owns filter state (provider, includeInactive).
 *
 * Route: /admin/models
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import type { LLMModel, LLMModelCreate, LLMModelUpdate, LLMProvider } from '@aurity-standalone/types/llm';
import {
  fetchLLMModels,
  createLLMModel,
  updateLLMModel,
  deleteLLMModel,
} from '@aurity-standalone/api-client/llm-models';
import { confirmDialog, toastSuccess, toastError } from '@/lib/swal';
import { createLogger } from '@/lib/internal/logger';

const log = createLogger('LLMModels');

export function useLLMModels() {
  const [models, setModels] = useState<LLMModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState<string | null>(null);

  // Filters
  const [includeInactive, setIncludeInactive] = useState(false);
  const [providerFilter, setProviderFilter] = useState<LLMProvider | ''>('');

  const loadModels = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchLLMModels({
        includeInactive,
        provider: providerFilter || undefined,
      });
      setModels(data);
    } catch (err) {
      log.error('Failed to load models', { error: String(err) });
      setError(err instanceof Error ? err.message : 'Error al cargar los modelos');
    } finally {
      setLoading(false);
    }
  }, [includeInactive, providerFilter]);

  useEffect(() => {
    loadModels();
  }, [loadModels]);

  const handleCreate = useCallback(async (data: LLMModelCreate) => {
    try {
      const newModel = await createLLMModel(data);
      setModels((prev) => [...prev, newModel]);
      toastSuccess('Modelo creado correctamente');
    } catch (err) {
      log.error('Failed to create model', { error: String(err) });
      toastError(err instanceof Error ? err.message : 'Error al crear el modelo');
      throw err;
    }
  }, []);

  const handleUpdate = useCallback(async (modelId: string, data: LLMModelUpdate) => {
    try {
      const updated = await updateLLMModel(modelId, data);
      setModels((prev) => prev.map((m) => (m.id === modelId ? updated : m)));
      toastSuccess('Modelo actualizado correctamente');
    } catch (err) {
      log.error('Failed to update model', { error: String(err) });
      toastError(err instanceof Error ? err.message : 'Error al actualizar el modelo');
      throw err;
    }
  }, []);

  const handleDelete = useCallback(async (modelId: string) => {
    const confirmed = await confirmDialog({
      title: '¿Eliminar modelo?',
      text: 'El modelo será desactivado. Usa eliminación permanente para removerlo completamente.',
      confirmText: 'Desactivar',
      icon: 'warning',
    });
    if (!confirmed) return;

    try {
      await deleteLLMModel(modelId, false);
      setModels((prev) => prev.map((m) => (m.id === modelId ? { ...m, is_active: false } : m)));
      if (selectedModel === modelId) {
        setSelectedModel(null);
      }
      toastSuccess('Modelo desactivado correctamente');
    } catch (err) {
      log.error('Failed to delete model', { error: String(err) });
      toastError(err instanceof Error ? err.message : 'Error al eliminar el modelo');
    }
  }, [selectedModel]);

  const handleToggleActive = useCallback(async (model: LLMModel) => {
    try {
      const updated = await updateLLMModel(model.id, { is_active: !model.is_active });
      setModels((prev) => prev.map((m) => (m.id === model.id ? updated : m)));
      toastSuccess(updated.is_active ? 'Modelo activado' : 'Modelo desactivado');
    } catch (err) {
      log.error('Failed to toggle model', { error: String(err) });
      toastError(err instanceof Error ? err.message : 'Error al cambiar estado del modelo');
    }
  }, []);

  return {
    models,
    loading,
    error,
    selectedModel,
    setSelectedModel,
    loadModels,
    handleCreate,
    handleUpdate,
    handleDelete,
    handleToggleActive,
    includeInactive,
    setIncludeInactive,
    providerFilter,
    setProviderFilter,
  } as const;
}
