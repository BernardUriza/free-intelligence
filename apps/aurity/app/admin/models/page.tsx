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
            <div class="text-left space-y-4">
              <div class="p-3 bg-slate-700/50 rounded-lg">
                <p class="fi-text-xs mb-1 uppercase tracking-wide">Prompt médico</p>
                <p class="text-sm text-slate-200">${result.prompt}</p>
              </div>
              <div class="p-3 bg-emerald-900/30 border border-emerald-800 rounded-lg">
                <p class="text-xs fi-text-success mb-1 uppercase tracking-wide">Respuesta del modelo</p>
                <p class="text-sm text-slate-200 whitespace-pre-wrap">${result.response}</p>
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
            <div class="text-left space-y-4">
              <div class="p-3 bg-slate-700/50 rounded-lg">
                <p class="fi-text-xs mb-1 uppercase tracking-wide">Prompt</p>
                <p class="text-sm text-slate-200">${result.prompt}</p>
              </div>
              <div class="p-3 bg-red-900/30 border border-red-800 rounded-lg">
                <p class="text-xs fi-text-error mb-1 uppercase tracking-wide">Error</p>
                <p class="text-sm text-red-200">${result.error || 'Error desconocido'}</p>
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
      <div className="mb-6 p-4 bg-slate-800/50 border border-slate-700 rounded-xl">
        <div className="fi-flex-between mb-4">
          <div className="fi-flex-gap">
            <Activity className="w-5 h-5 fi-text-success" />
            <h3 className="fi-title">Recursos del Sistema</h3>
          </div>
          <Button
            onClick={loadResources}
            disabled={resourcesLoading}
            variant="ghost"
            size="sm"
            icon={RefreshCw}
            className={resourcesLoading ? '[&>svg]:animate-spin' : ''}
          >
            Actualizar
          </Button>
        </div>

        {resourcesLoading && !systemResources ? (
          <div className="flex items-center gap-2 text-slate-400">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-sm">Cargando recursos...</span>
          </div>
        ) : systemResources ? (
          <div className="space-y-4">
            {/* RAM Usage Bar */}
            <div>
              <div className="fi-flex-between mb-2">
                <div className="fi-flex-gap">
                  <HardDrive className="w-4 h-4 text-slate-400" />
                  <span className="text-sm fi-text">Memoria RAM</span>
                </div>
                <span className="text-sm font-mono text-slate-400">
                  {systemResources.memory.used_gb.toFixed(1)}GB / {systemResources.memory.total_gb.toFixed(1)}GB
                </span>
              </div>
              <div className="h-3 bg-slate-700 rounded-full overflow-hidden">
                <div
                  className={`h-full transition-all duration-500 ${
                    systemResources.memory.percent_used < 50 ? 'bg-emerald-500' :
                    systemResources.memory.percent_used < 75 ? 'bg-yellow-500' :
                    systemResources.memory.percent_used < 90 ? 'bg-orange-500' : 'bg-red-500'
                  }`}
                  style={{ width: `${systemResources.memory.percent_used}%` }}
                />
              </div>
              <div className="flex justify-between mt-1 fi-text-xs-muted">
                <span>{systemResources.memory.available_gb.toFixed(1)}GB disponible</span>
                <span>{systemResources.memory.percent_used.toFixed(0)}% usado</span>
              </div>
            </div>

            {/* CPU & Platform Info */}
            <div className="flex items-center gap-6 text-sm">
              <div className="fi-flex-gap">
                <Cpu className="w-4 h-4 text-slate-400" />
                <span className="fi-text">CPU: {systemResources.cpu_percent.toFixed(0)}%</span>
                <span className="text-slate-500">({systemResources.cpu_count} cores)</span>
              </div>
              <span className="text-slate-500">{systemResources.platform}</span>
            </div>

            {/* Running Models */}
            {runningModels && (
              <div className="pt-3 fi-border-top">
                <div className="fi-flex-between mb-2">
                  <div className="fi-flex-gap">
                    <Zap className="w-4 h-4 fi-text-warning" />
                    <span className="text-sm fi-text">Modelos en Memoria (Ollama)</span>
                  </div>
                  {runningModels.ollama_available ? (
                    <span className="text-xs fi-text-success flex items-center gap-1">
                      <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
                      Ollama activo
                    </span>
                  ) : (
                    <span className="text-xs fi-text-error">Ollama no disponible</span>
                  )}
                </div>

                {runningModels.models.length === 0 ? (
                  <p className="text-sm text-slate-500 italic">
                    Sin modelos cargados • RAM libre para cargar modelos
                  </p>
                ) : (
                  <div className="fi-stack-sm">
                    {runningModels.models.map((model) => (
                      <div
                        key={model.model_id}
                        className="flex items-center justify-between p-2 bg-slate-900/50 rounded-lg"
                      >
                        <div className="fi-flex-gap-md">
                          <span className={`px-2 py-0.5 text-xs rounded ${
                            model.processor === 'gpu' ? 'bg-purple-900/50 text-purple-300' :
                            model.processor === 'partial' ? 'bg-amber-900/50 text-amber-300' :
                            'bg-slate-700 fi-text'
                          }`}>
                            {model.processor.toUpperCase()}
                          </span>
                          <span className="text-sm text-white font-medium">{model.name}</span>
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
                            className="text-slate-500 hover:fi-text-error"
                          />
                        </div>
                      </div>
                    ))}
                    <div className="fi-text-xs-muted text-right">
                      Total en memoria: {runningModels.total_loaded_gb.toFixed(1)}GB
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ) : (
          <p className="text-sm text-slate-500">No se pudieron cargar los recursos del sistema</p>
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4 mb-6">
        <div className="fi-flex-gap">
          <Filter className="w-4 h-4 text-slate-400" />
          <Select value={providerFilter} onValueChange={(val) => setProviderFilter(val as LLMProvider | '')}>
            <SelectTrigger className="w-48">
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
        <label className="flex items-center gap-2 fi-subtitle cursor-pointer">
          <input
            type="checkbox"
            checked={includeInactive}
            onChange={(e) => setIncludeInactive(e.target.checked)}
            className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-emerald-500 focus:ring-emerald-500"
          />
          Mostrar inactivos
        </label>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="fi-empty-state-lg">
          <Loader2 className="w-12 h-12 fi-text-success animate-spin mb-4" />
          <p className="text-slate-400">Cargando modelos...</p>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="fi-empty-state-lg">
          <div className="p-6 bg-red-950/20 border border-red-800 rounded-lg max-w-md">
            <div className="flex items-center gap-3 mb-2">
              <AlertCircle className="w-6 h-6 fi-text-error" />
              <h3 className="text-lg font-semibold text-red-300">
                Error al Cargar Modelos
              </h3>
            </div>
            <p className="text-red-200 text-sm">{error}</p>
            <Button onClick={loadModels} variant="primary" fullWidth className="mt-4">
              Reintentar
            </Button>
          </div>
        </div>
      )}

      {/* Models Grid */}
      {!loading && !error && models.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
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
          <Brain className="w-16 h-16 text-slate-600 mb-4" />
          <h3 className="text-xl font-semibold text-slate-400 mb-2">
            No hay modelos configurados
          </h3>
          <p className="text-slate-500 text-center max-w-md mb-6">
            Los modelos LLM definen qué servicios de IA están disponibles para asignar a las personas.
          </p>
          <Button onClick={() => setShowCreateModal(true)} variant="primary">
            <Plus className="w-4 h-4 mr-2" />
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
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-slate-900 rounded-lg border border-slate-700 p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="fi-flex-between mb-6">
          <h2 className="fi-title-xl">
            {mode === 'create' ? 'Nuevo Modelo LLM' : 'Editar Modelo'}
          </h2>
          <button onClick={onClose} className="fi-btn-close">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* ID (only for create) */}
          {mode === 'create' && (
            <div>
              <label className="block fi-subtitle mb-1">ID del Modelo *</label>
              <Input
                value={formData.id}
                onChange={(e) => setFormData({ ...formData, id: e.target.value.toLowerCase().replace(/\s/g, '-') })}
                placeholder="gpt-4o-mini"
                className="font-mono"
              />
              <p className="fi-text-xs-muted mt-1">
                Identificador único (sin espacios, minúsculas)
              </p>
            </div>
          )}

          {/* Label */}
          <div>
            <label className="block fi-subtitle mb-1">Label (Nombre visible) *</label>
            <Input
              value={formData.label}
              onChange={(e) => setFormData({ ...formData, label: e.target.value })}
              placeholder="GPT-4o Mini (Balance, $$)"
            />
          </div>

          {/* Provider & Cost Tier */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block fi-subtitle mb-1">Proveedor</label>
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
              <label className="block fi-subtitle mb-1">Nivel de Costo</label>
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
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block fi-subtitle mb-1">Max Tokens (output)</label>
              <Input
                type="number"
                value={formData.max_tokens}
                onChange={(e) => setFormData({ ...formData, max_tokens: parseInt(e.target.value) || 0 })}
                min={1}
                max={1000000}
              />
            </div>
            <div>
              <label className="block fi-subtitle mb-1">Ventana de Contexto</label>
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
            <label className="block fi-subtitle mb-1">Descripción</label>
            <textarea
              value={formData.description || ''}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white focus:border-emerald-500 focus:outline-none"
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
              className="w-4 h-4 text-emerald-500"
            />
            <label htmlFor="is_active" className="fi-subtitle">
              Modelo activo (disponible para selección)
            </label>
          </div>

          {error && (
            <div className="p-3 bg-red-950/20 border border-red-800 rounded-lg text-red-300 text-sm">
              {error}
            </div>
          )}

          <div className="flex gap-3 pt-4">
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
