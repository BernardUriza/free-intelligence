/**
 * ModelsGrid
 *
 * Single Responsibility: Renders the LLM model cards grid with loading,
 * error, and empty states.
 *
 * Route: /admin/models
 */

'use client';

import { Loader2, AlertCircle, Brain, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { LLMModelCard } from '@/components/admin/LLMModelCard';
import type { LLMModel } from '@aurity-standalone/types/llm';

interface ModelsGridProps {
  models: LLMModel[];
  loading: boolean;
  error: string | null;
  selectedModel: string | null;
  onSelectModel: (id: string) => void;
  onEditModel: (model: LLMModel) => void;
  onDeleteModel: (id: string) => void;
  onToggleActive: (model: LLMModel) => void;
  onTestModel: (model: LLMModel) => void;
  onRetry: () => void;
  onCreateFirst: () => void;
}

export function ModelsGrid({
  models,
  loading,
  error,
  selectedModel,
  onSelectModel,
  onEditModel,
  onDeleteModel,
  onToggleActive,
  onTestModel,
  onRetry,
  onCreateFirst,
}: ModelsGridProps) {
  if (loading) {
    return (
      <div className="fi-empty-state-lg">
        <Loader2 className="mdl-loading-icon" />
        <p className="mdl-loading-text">Cargando modelos...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="fi-empty-state-lg">
        <div className="mdl-error-panel">
          <div className="mdl-error-header">
            <AlertCircle className="mdl-error-icon" />
            <h3 className="mdl-error-title">Error al Cargar Modelos</h3>
          </div>
          <p className="mdl-error-text">{error}</p>
          <Button onClick={onRetry} variant="primary" fullWidth className="mdl-retry-gap">
            Reintentar
          </Button>
        </div>
      </div>
    );
  }

  if (models.length === 0) {
    return (
      <div className="fi-empty-state-lg">
        <Brain className="mdl-empty-icon" />
        <h3 className="mdl-empty-title">No hay modelos configurados</h3>
        <p className="mdl-empty-desc">
          Los modelos LLM definen qué servicios de IA están disponibles para asignar a las personas.
        </p>
        <Button onClick={onCreateFirst} variant="primary">
          <Plus className="mdl-add-icon" />
          Crear Primer Modelo
        </Button>
      </div>
    );
  }

  return (
    <div className="mdl-grid">
      {models.map((model) => (
        <LLMModelCard
          key={model.id}
          model={model}
          isSelected={selectedModel === model.id}
          onClick={() => onSelectModel(model.id)}
          onEdit={() => onEditModel(model)}
          onDelete={() => onDeleteModel(model.id)}
          onToggleActive={() => onToggleActive(model)}
          onTest={() => onTestModel(model)}
        />
      ))}
    </div>
  );
}
