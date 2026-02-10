/**
 * LLM Models Admin Page
 *
 * Admin panel for managing LLM models available for persona assignment.
 * Route: /admin/models
 * Requires: FI-superadmin role
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  Loader2,
  AlertCircle,
  Brain,
  Plus,
  X,
  Filter,
  Download,
  Cpu,
  HardDrive,
  Activity,
  Zap,
  RefreshCw,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import type { LLMModel, LLMModelCreate, LLMModelUpdate, LLMProvider, CostTier } from '@aurity-standalone/types/llm';
import { PROVIDER_INFO, COST_TIER_INFO } from '@aurity-standalone/types/llm';
import {
  fetchLLMModels,
  createLLMModel,
  updateLLMModel,
  deleteLLMModel,
  testLLMModel,
} from '@aurity-standalone/api-client/llm-models';
import {
  fetchSystemResources,
  fetchRunningModels,
  unloadModel,
  formatTimeUntil,
  type SystemResources,
  type RunningModelsResponse,
} from '@/lib/api/system';
import { LLMModelCard } from '@/components/admin/LLMModelCard';
import { ModelCatalogDrawer } from '@/components/admin/model-catalog-drawer';
import { AppTemplate } from '@/components/layout/AppTemplate';
import { adminLLMModelsHeader } from '@/config/page-headers';
import { confirmDialog, toastSuccess, toastError, swal, showProgressiveLoading, closeDialog } from '@/lib/swal';

export default function LLMModelsAdminPage() {
  const [models, setModels] = useState<LLMModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showCatalogDrawer, setShowCatalogDrawer] = useState(false);
  const [editingModel, setEditingModel] = useState<LLMModel | null>(null);
  const [includeInactive, setIncludeInactive] = useState(false);
  const [providerFilter, setProviderFilter] = useState<LLMProvider | ''>('');

  // System Resources State
  const [systemResources, setSystemResources] = useState<SystemResources | null>(null);
  const [runningModels, setRunningModels] = useState<RunningModelsResponse | null>(null);
  const [resourcesLoading, setResourcesLoading] = useState(true);

  // Load models callback (declared before useEffect that uses it)
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
      console.error('Failed to load LLM models:', err);
      setError(err instanceof Error ? err.message : 'Error al cargar los modelos');
    } finally {
      setLoading(false);
    }
  }, [includeInactive, providerFilter]);

  useEffect(() => {
    loadModels();
  }, [includeInactive, providerFilter, loadModels]);

  // Load system resources on mount and periodically
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
    const interval = setInterval(loadResources, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, [loadResources]);

  const handleUnloadModel = async (modelName: string) => {
    try {
      await unloadModel(modelName);
      toastSuccess(`Modelo ${modelName} descargado de memoria`);
      await loadResources();
    } catch (err) {
      toastError(err instanceof Error ? err.message : 'Error al descargar modelo');
    }
  };

  const handleCreate = async (data: LLMModelCreate) => {
    try {
      const newModel = await createLLMModel(data);
      setModels((prev) => [...prev, newModel]);
      setShowCreateModal(false);
      toastSuccess('Modelo creado correctamente');
    } catch (err) {
      console.error('Failed to create model:', err);
      toastError(err instanceof Error ? err.message : 'Error al crear el modelo');
      throw err;
    }
  };

  const handleUpdate = async (modelId: string, data: LLMModelUpdate) => {
    try {
      const updated = await updateLLMModel(modelId, data);
      setModels((prev) => prev.map((m) => (m.id === modelId ? updated : m)));
      setEditingModel(null);
      toastSuccess('Modelo actualizado correctamente');
    } catch (err) {
      console.error('Failed to update model:', err);
      toastError(err instanceof Error ? err.message : 'Error al actualizar el modelo');
      throw err;
    }
  };

  const handleDelete = async (modelId: string) => {
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
      console.error('Failed to delete model:', err);
      toastError(err instanceof Error ? err.message : 'Error al eliminar el modelo');
    }
  };

  const handleToggleActive = async (model: LLMModel) => {
    try {
      const updated = await updateLLMModel(model.id, { is_active: !model.is_active });
      setModels((prev) => prev.map((m) => (m.id === model.id ? updated : m)));
      toastSuccess(updated.is_active ? 'Modelo activado' : 'Modelo desactivado');
    } catch (err) {
      console.error('Failed to toggle model:', err);
      toastError(err instanceof Error ? err.message : 'Error al cambiar estado del modelo');
    }
  };

  const handleTest = async (model: LLMModel) => {
    // Progressive loading stages - different for local vs cloud models
    const isLocalModel = model.provider === 'ollama';
    const stages = isLocalModel
      ? [
          { title: `Probando ${model.label}...`, text: 'Iniciando conexión con Ollama', delay: 0 },
          { title: 'Cargando modelo en memoria...', text: 'Los modelos locales requieren cargarse en RAM', delay: 3000 },
          { title: 'Generando respuesta...', text: 'Esto puede tardar varios minutos para modelos grandes', delay: 15000 },
          { title: 'Procesando...', text: 'El modelo está respondiendo a la consulta médica', delay: 60000 },
          { title: 'Casi listo...', text: 'Finalizando generación de respuesta', delay: 180000 },
        ]
      : [
          { title: `Probando ${model.label}...`, text: 'Conectando con API', delay: 0 },
          { title: 'Generando respuesta...', text: 'El modelo está procesando la consulta', delay: 3000 },
        ];

    const progressController = showProgressiveLoading(stages);

    try {
      const result = await testLLMModel(model.id);
      progressController.stop();
      closeDialog();

      if (result.success) {
        await swal.fire({
          icon: 'success',
          title: `Prueba de ${model.id}`,
          html: `
            <div class="mdl-swal-body">
              <div class="mdl-swal-prompt">
                <p class="mdl-swal-label">Prompt médico</p>
                <p class="mdl-swal-text">${result.prompt}</p>
              </div>
              <div class="mdl-swal-success-box">
                <p class="mdl-swal-success-label">Respuesta del modelo</p>
                <p class="mdl-swal-response-text">${result.response}</p>
              </div>
            </div>
          `,
          confirmButtonText: 'Cerrar',
          width: '600px',
        });
      } else {
        await swal.fire({
          icon: 'error',
          title: `Error al probar ${model.id}`,
          html: `
            <div class="mdl-swal-body">
              <div class="mdl-swal-prompt">
                <p class="mdl-swal-label">Prompt</p>
                <p class="mdl-swal-text">${result.prompt}</p>
              </div>
              <div class="mdl-swal-error-box">
                <p class="mdl-swal-error-label">Error</p>
                <p class="mdl-swal-error-text">${result.error || 'Error desconocido'}</p>
              </div>
            </div>
          `,
          confirmButtonText: 'Cerrar',
          width: '600px',
        });
      }
    } catch (err) {
      progressController.stop();
      closeDialog();
      console.error('Failed to test model:', err);
      toastError(err instanceof Error ? err.message : 'Error al probar el modelo');
    }
  };

  const headerConfig = adminLLMModelsHeader({ modelsCount: models.length });

  return (
    <AppTemplate
      headerConfig={headerConfig}
      headerActions={
        <div className="fi-flex-gap-md">
          <Button
            onClick={() => setShowCatalogDrawer(true)}
            variant="purple"
            icon={Download}
          >
            Catálogo
          </Button>
          <Button
            onClick={() => setShowCreateModal(true)}
            icon={Plus}
          >
            Nuevo Modelo
          </Button>
        </div>
      }
      backgroundGradient="emerald"
      padding="8"
      showWatermark={true}
      showGeometricBg={true}
    >
      {/* System Resources Dashboard */}
      <div className="mdl-resources-panel">
        <div className="mdl-resources-title-row">
          <div className="fi-flex-gap">
            <Activity className="mdl-icon-md fi-text-success" />
            <h3 className="fi-title">Recursos del Sistema</h3>
          </div>
          <Button
            onClick={loadResources}
            disabled={resourcesLoading}
            variant="ghost"
            size="sm"
            icon={RefreshCw}
            className={resourcesLoading ? 'mdl-spin-svg' : ''}
          >
            Actualizar
          </Button>
        </div>

        {resourcesLoading && !systemResources ? (
          <div className="mdl-resources-loading">
            <Loader2 className="mdl-resources-loading-icon" />
            <span className="mdl-resources-loading-text">Cargando recursos...</span>
          </div>
        ) : systemResources ? (
          <div className="mdl-resources-body">
            {/* RAM Usage Bar */}
            <div>
              <div className="mdl-ram-header">
                <div className="fi-flex-gap">
                  <HardDrive className="mdl-icon-sm" />
                  <span className="mdl-ram-label">Memoria RAM</span>
                </div>
                <span className="mdl-ram-value">
                  {systemResources.memory.used_gb.toFixed(1)}GB / {systemResources.memory.total_gb.toFixed(1)}GB
                </span>
              </div>
              <div className="mdl-progress-track">
                <div
                  className={`mdl-progress-bar ${
                    systemResources.memory.percent_used < 50 ? 'mdl-progress-ok' :
                    systemResources.memory.percent_used < 75 ? 'mdl-progress-warn' :
                    systemResources.memory.percent_used < 90 ? 'mdl-progress-danger' : 'mdl-progress-critical'
                  }`}
                  style={{ width: `${systemResources.memory.percent_used}%` }}
                />
              </div>
              <div className="mdl-progress-labels">
                <span>{systemResources.memory.available_gb.toFixed(1)}GB disponible</span>
                <span>{systemResources.memory.percent_used.toFixed(0)}% usado</span>
              </div>
            </div>

            {/* CPU & Platform Info */}
            <div className="mdl-cpu-row">
              <div className="fi-flex-gap">
                <Cpu className="mdl-icon-sm" />
                <span className="fi-text">CPU: {systemResources.cpu_percent.toFixed(0)}%</span>
                <span className="mdl-text-muted">({systemResources.cpu_count} cores)</span>
              </div>
              <span className="mdl-text-muted">{systemResources.platform}</span>
            </div>

            {/* Running Models */}
            {runningModels && (
              <div className="mdl-running-section">
                <div className="mdl-ollama-header">
                  <div className="fi-flex-gap">
                    <Zap className="mdl-icon-sm fi-text-warning" />
                    <span className="mdl-ollama-label">Modelos en Memoria (Ollama)</span>
                  </div>
                  {runningModels.ollama_available ? (
                    <span className="mdl-ollama-active">
                      <span className="mdl-status-dot" />
                      Ollama activo
                    </span>
                  ) : (
                    <span className="mdl-ollama-inactive">Ollama no disponible</span>
                  )}
                </div>

                {runningModels.models.length === 0 ? (
                  <p className="mdl-no-models">
                    Sin modelos cargados • RAM libre para cargar modelos
                  </p>
                ) : (
                  <div className="fi-stack-sm">
                    {runningModels.models.map((model) => (
                      <div
                        key={model.model_id}
                        className="mdl-running-card"
                      >
                        <div className="fi-flex-gap-md">
                          <span className={
                            model.processor === 'gpu' ? 'mdl-processor-gpu' :
                            model.processor === 'partial' ? 'mdl-processor-partial' :
                            'mdl-processor-cpu'
                          }>
                            {model.processor.toUpperCase()}
                          </span>
                          <span className="mdl-model-name">{model.name}</span>
                          <span className="fi-text-xs-muted">{model.size_gb}GB</span>
                        </div>
                        <div className="fi-flex-gap">
                          <span className="fi-text-xs-muted">
                            {formatTimeUntil(model.until)}
                          </span>
                          <Button
                            onClick={() => handleUnloadModel(model.name)}
                            variant="ghost"
                            size="xs"
                            icon={X}
                            title="Descargar de memoria"
                            className="mdl-unload-btn"
                          />
                        </div>
                      </div>
                    ))}
                    <div className="mdl-running-total">
                      Total en memoria: {runningModels.total_loaded_gb.toFixed(1)}GB
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ) : (
          <p className="mdl-no-resources">No se pudieron cargar los recursos del sistema</p>
        )}
      </div>

      {/* Filters */}
      <div className="mdl-filters-row">
        <div className="fi-flex-gap">
          <Filter className="mdl-icon-sm" />
          <Select value={providerFilter} onValueChange={(val) => setProviderFilter(val as LLMProvider | '')}>
            <SelectTrigger className="mdl-filter-select">
              <SelectValue placeholder="Todos los proveedores" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">Todos los proveedores</SelectItem>
              {Object.entries(PROVIDER_INFO).map(([key, info]) => (
                <SelectItem key={key} value={key}>
                  {info.icon} {info.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <label className="mdl-checkbox-label">
          <input
            type="checkbox"
            checked={includeInactive}
            onChange={(e) => setIncludeInactive(e.target.checked)}
            className="mdl-checkbox"
          />
          Mostrar inactivos
        </label>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="fi-empty-state-lg">
          <Loader2 className="mdl-loading-icon" />
          <p className="mdl-loading-text">Cargando modelos...</p>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="fi-empty-state-lg">
          <div className="mdl-error-panel">
            <div className="mdl-error-header">
              <AlertCircle className="mdl-error-icon" />
              <h3 className="mdl-error-title">
                Error al Cargar Modelos
              </h3>
            </div>
            <p className="mdl-error-text">{error}</p>
            <Button onClick={loadModels} variant="primary" fullWidth className="mdl-retry-gap">
              Reintentar
            </Button>
          </div>
        </div>
      )}

      {/* Models Grid */}
      {!loading && !error && models.length > 0 && (
        <div className="mdl-grid">
          {models.map((model) => (
            <LLMModelCard
              key={model.id}
              model={model}
              isSelected={selectedModel === model.id}
              onClick={() => setSelectedModel(model.id)}
              onEdit={() => setEditingModel(model)}
              onDelete={() => handleDelete(model.id)}
              onToggleActive={() => handleToggleActive(model)}
              onTest={() => handleTest(model)}
            />
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && models.length === 0 && (
        <div className="fi-empty-state-lg">
          <Brain className="mdl-empty-icon" />
          <h3 className="mdl-empty-title">
            No hay modelos configurados
          </h3>
          <p className="mdl-empty-desc">
            Los modelos LLM definen qué servicios de IA están disponibles para asignar a las personas.
          </p>
          <Button onClick={() => setShowCreateModal(true)} variant="primary">
            <Plus className="mdl-add-icon" />
            Crear Primer Modelo
          </Button>
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <LLMModelModal
          mode="create"
          onClose={() => setShowCreateModal(false)}
          onCreate={handleCreate}
        />
      )}

      {/* Edit Modal */}
      {editingModel && (
        <LLMModelModal
          mode="edit"
          model={editingModel}
          onClose={() => setEditingModel(null)}
          onUpdate={(data) => handleUpdate(editingModel.id, data)}
        />
      )}

      {/* Catalog Drawer */}
      <ModelCatalogDrawer
        isOpen={showCatalogDrawer}
        onClose={() => setShowCatalogDrawer(false)}
        onModelInstalled={loadModels}
      />
    </AppTemplate>
  );
}

// =============================================================================
// LLM MODEL MODAL (Create/Edit)
// =============================================================================

interface LLMModelModalProps {
  mode: 'create' | 'edit';
  model?: LLMModel;
  onClose: () => void;
  onCreate?: (data: LLMModelCreate) => Promise<void>;
  onUpdate?: (data: LLMModelUpdate) => Promise<void>;
}

function LLMModelModal({ mode, model, onClose, onCreate, onUpdate }: LLMModelModalProps) {
  const [formData, setFormData] = useState<LLMModelCreate>({
    id: model?.id || '',
    label: model?.label || '',
    provider: model?.provider || 'openai',
    cost_tier: model?.cost_tier || 'medium',
    max_tokens: model?.max_tokens || 4096,
    context_window: model?.context_window || 128000,
    is_active: model?.is_active ?? true,
    description: model?.description || '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (mode === 'create' && !formData.id.trim()) {
      setError('El ID del modelo es requerido');
      return;
    }
    if (!formData.label.trim()) {
      setError('El label es requerido');
      return;
    }

    setSaving(true);
    setError(null);
    try {
      if (mode === 'create' && onCreate) {
        await onCreate(formData);
      } else if (mode === 'edit' && onUpdate) {
        const { id: _id, ...updateData } = formData;
        await onUpdate(updateData);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al guardar');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mdl-modal-overlay">
      <div className="mdl-modal-panel">
        <div className="mdl-modal-title-row">
          <h2 className="fi-title-xl">
            {mode === 'create' ? 'Nuevo Modelo LLM' : 'Editar Modelo'}
          </h2>
          <button onClick={onClose} className="fi-btn-close">
            <X className="mdl-close-icon" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="mdl-form">
          {/* ID (only for create) */}
          {mode === 'create' && (
            <div>
              <label className="mdl-label">ID del Modelo *</label>
              <Input
                value={formData.id}
                onChange={(e) => setFormData({ ...formData, id: e.target.value.toLowerCase().replace(/\s/g, '-') })}
                placeholder="gpt-4o-mini"
                className="mdl-input-mono"
              />
              <p className="mdl-form-hint">
                Identificador único (sin espacios, minúsculas)
              </p>
            </div>
          )}

          {/* Label */}
          <div>
            <label className="mdl-label">Label (Nombre visible) *</label>
            <Input
              value={formData.label}
              onChange={(e) => setFormData({ ...formData, label: e.target.value })}
              placeholder="GPT-4o Mini (Balance, $$)"
            />
          </div>

          {/* Provider & Cost Tier */}
          <div className="mdl-form-grid">
            <div>
              <label className="mdl-label">Proveedor</label>
              <Select value={formData.provider} onValueChange={(val) => setFormData({ ...formData, provider: val as LLMProvider })}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Seleccionar proveedor" />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(PROVIDER_INFO).map(([key, info]) => (
                    <SelectItem key={key} value={key}>
                      {info.icon} {info.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="mdl-label">Nivel de Costo</label>
              <Select value={formData.cost_tier} onValueChange={(val) => setFormData({ ...formData, cost_tier: val as CostTier })}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Seleccionar nivel" />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(COST_TIER_INFO).map(([key, info]) => (
                    <SelectItem key={key} value={key}>
                      {info.icon} {info.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Max Tokens & Context Window */}
          <div className="mdl-form-grid">
            <div>
              <label className="mdl-label">Max Tokens (output)</label>
              <Input
                type="number"
                value={formData.max_tokens}
                onChange={(e) => setFormData({ ...formData, max_tokens: parseInt(e.target.value) || 0 })}
                min={1}
                max={1000000}
              />
            </div>
            <div>
              <label className="mdl-label">Ventana de Contexto</label>
              <Input
                type="number"
                value={formData.context_window}
                onChange={(e) => setFormData({ ...formData, context_window: parseInt(e.target.value) || 0 })}
                min={1024}
                max={2000000}
              />
            </div>
          </div>

          {/* Description */}
          <div>
            <label className="mdl-label">Descripción</label>
            <textarea
              value={formData.description || ''}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="mdl-textarea"
              rows={2}
              placeholder="Descripción del modelo y casos de uso..."
            />
          </div>

          {/* Active Status */}
          <div className="fi-flex-gap-md">
            <input
              type="checkbox"
              id="is_active"
              checked={formData.is_active}
              onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
              className="mdl-active-checkbox"
            />
            <label htmlFor="is_active" className="fi-subtitle">
              Modelo activo (disponible para selección)
            </label>
          </div>

          {error && (
            <div className="mdl-form-error">
              {error}
            </div>
          )}

          <div className="mdl-form-actions">
            <Button type="button" onClick={onClose} variant="secondary" fullWidth>
              Cancelar
            </Button>
            <Button
              type="submit"
              disabled={saving}
              variant="primary"
              fullWidth
              loading={saving}
            >
              {mode === 'create' ? 'Crear Modelo' : 'Guardar Cambios'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
