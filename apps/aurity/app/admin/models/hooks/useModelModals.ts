/**
 * useModelModals Hook
 *
 * Single Responsibility: Modal/drawer visibility state and compound handlers
 * for the LLM Models Admin page.
 *
 * Route: /admin/models
 */

'use client';

import { useState, useCallback } from 'react';
import type { LLMModel, LLMModelCreate, LLMModelUpdate } from '@aurity-standalone/types/llm';

interface UseModelModalsOptions {
  onCreate: (data: LLMModelCreate) => Promise<void>;
  onUpdate: (modelId: string, data: LLMModelUpdate) => Promise<void>;
}

export function useModelModals({ onCreate, onUpdate }: UseModelModalsOptions) {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showCatalogDrawer, setShowCatalogDrawer] = useState(false);
  const [editingModel, setEditingModel] = useState<LLMModel | null>(null);

  // ── Open / Close ──────────────────────────────────────────────────

  const openCreate = useCallback(() => setShowCreateModal(true), []);
  const closeCreate = useCallback(() => setShowCreateModal(false), []);

  const openCatalog = useCallback(() => setShowCatalogDrawer(true), []);
  const closeCatalog = useCallback(() => setShowCatalogDrawer(false), []);

  const openEdit = useCallback((model: LLMModel) => setEditingModel(model), []);
  const closeEdit = useCallback(() => setEditingModel(null), []);

  // ── Compound handlers (action + close) ────────────────────────────

  const handleCreateAndClose = useCallback(async (data: LLMModelCreate) => {
    await onCreate(data);
    closeCreate();
  }, [onCreate, closeCreate]);

  const handleUpdateAndClose = useCallback(async (data: LLMModelUpdate) => {
    if (!editingModel) return;
    await onUpdate(editingModel.id, data);
    closeEdit();
  }, [editingModel, onUpdate, closeEdit]);

  return {
    showCreateModal,
    showCatalogDrawer,
    editingModel,
    openCreate,
    closeCreate,
    openCatalog,
    closeCatalog,
    openEdit,
    closeEdit,
    handleCreateAndClose,
    handleUpdateAndClose,
  } as const;
}
