'use client';

import { Brain, Loader2, Plus } from 'lucide-react';
import { AdminAlert, AdminButton } from '../admin-kit';
import { LLMModelCard } from './LLMModelCard';
import { FI_MODEL_CATALOG_ROOT_CLASS, useModelCatalogStyle } from './modelCatalogStyle';
import type { LLMModel } from './types';

export interface LLMModelGridProps {
  models: readonly LLMModel[];
  loading: boolean;
  error: string | null;
  selectedId?: string | null;
  onSelect?: (modelId: string) => void;
  onEdit: (model: LLMModel) => void;
  onDeactivate: (model: LLMModel) => void;
  onToggleActive: (model: LLMModel) => void;
  onTest?: (model: LLMModel) => void;
  onRetry: () => void;
  onCreateFirst?: () => void;
  locale?: string;
}

export function LLMModelGrid({
  models,
  loading,
  error,
  selectedId,
  onSelect,
  onEdit,
  onDeactivate,
  onToggleActive,
  onTest,
  onRetry,
  onCreateFirst,
  locale,
}: LLMModelGridProps) {
  useModelCatalogStyle();

  if (loading) {
    return (
      <div className={`${FI_MODEL_CATALOG_ROOT_CLASS} fi-mc-empty`} role="status">
        <Loader2 size={40} className="fi-admin-spin" aria-hidden="true" />
        <p>Cargando modelos...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`${FI_MODEL_CATALOG_ROOT_CLASS} fi-mc-empty`}>
        <AdminAlert
          action={
            <AdminButton variant="danger" onClick={onRetry}>
              Reintentar
            </AdminButton>
          }
        >
          {error}
        </AdminAlert>
      </div>
    );
  }

  if (models.length === 0) {
    return (
      <div className={`${FI_MODEL_CATALOG_ROOT_CLASS} fi-mc-empty`}>
        <Brain size={56} aria-hidden="true" />
        <h3>No hay modelos configurados</h3>
        <p>Los modelos LLM definen qué servicios de IA están disponibles para asignar a las personas.</p>
        {onCreateFirst ? (
          <AdminButton variant="primary" icon={Plus} onClick={onCreateFirst}>
            Crear primer modelo
          </AdminButton>
        ) : null}
      </div>
    );
  }

  return (
    <div className={`${FI_MODEL_CATALOG_ROOT_CLASS} fi-mc-grid`}>
      {models.map((model) => (
        <LLMModelCard
          key={model.id}
          model={model}
          locale={locale}
          selected={selectedId === model.id}
          onSelect={onSelect ? () => onSelect(model.id) : undefined}
          onEdit={() => onEdit(model)}
          onDeactivate={() => onDeactivate(model)}
          onToggleActive={() => onToggleActive(model)}
          onTest={onTest ? () => onTest(model) : undefined}
        />
      ))}
    </div>
  );
}
