/**
 * LLM Models Admin Page
 *
 * Admin panel for managing LLM models available for persona assignment.
 * Route: /admin/models
 * Requires: FI-superadmin role
 *
 * Architecture: Thin orchestrator page that composes modular hooks and components.
 * - useLLMModels: Model list CRUD + filter state
 * - useSystemResources: RAM, CPU, running models polling
 * - useModelTest: Test flow with progressive loading
 * - useModelModals: Modal/drawer visibility
 * - SystemResourcesPanel: Resource dashboard rendering
 * - ModelsFilterBar: Provider filter + inactive toggle
 * - ModelsGrid: Model cards with loading/error/empty states
 * - LLMModelModal: Create/Edit form (extracted)
 */

'use client';

import { Plus, Download } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { AppTemplate } from '@/components/layout/AppTemplate';
import { ModelCatalogDrawer } from '@/components/admin/model-catalog-drawer';
import { adminLLMModelsHeader } from '@/config/page-headers';
import { useLLMModels } from './hooks/useLLMModels';
import { useSystemResources } from './hooks/useSystemResources';
import { useModelTest } from './hooks/useModelTest';
import { useModelModals } from './hooks/useModelModals';
import { SystemResourcesPanel } from './components/SystemResourcesPanel';
import { ModelsFilterBar } from './components/ModelsFilterBar';
import { ModelsGrid } from './components/ModelsGrid';
import { LLMModelModal } from './components/LLMModelModal';

export default function LLMModelsAdminPage() {
  const {
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
  } = useLLMModels();

  const {
    systemResources,
    runningModels,
    resourcesLoading,
    loadResources,
    handleUnloadModel,
  } = useSystemResources();

  const { handleTest } = useModelTest();

  const modals = useModelModals({
    onCreate: handleCreate,
    onUpdate: handleUpdate,
  });

  const headerConfig = adminLLMModelsHeader({ modelsCount: models.length });

  return (
    <AppTemplate
      headerConfig={headerConfig}
      headerActions={
        <div className="fi-flex-gap-md">
          <Button onClick={modals.openCatalog} variant="purple" icon={Download}>
            Catálogo
          </Button>
          <Button onClick={modals.openCreate} icon={Plus}>
            Nuevo Modelo
          </Button>
        </div>
      }
      backgroundGradient="emerald"
      padding="8"
      showWatermark={true}
      showGeometricBg={true}
    >
      <SystemResourcesPanel
        systemResources={systemResources}
        runningModels={runningModels}
        resourcesLoading={resourcesLoading}
        onRefresh={loadResources}
        onUnloadModel={handleUnloadModel}
      />

      <ModelsFilterBar
        providerFilter={providerFilter}
        onProviderChange={setProviderFilter}
        includeInactive={includeInactive}
        onIncludeInactiveChange={setIncludeInactive}
      />

      <ModelsGrid
        models={models}
        loading={loading}
        error={error}
        selectedModel={selectedModel}
        onSelectModel={setSelectedModel}
        onEditModel={modals.openEdit}
        onDeleteModel={handleDelete}
        onToggleActive={handleToggleActive}
        onTestModel={handleTest}
        onRetry={loadModels}
        onCreateFirst={modals.openCreate}
      />

      {modals.showCreateModal && (
        <LLMModelModal
          mode="create"
          onClose={modals.closeCreate}
          onCreate={modals.handleCreateAndClose}
        />
      )}

      {modals.editingModel && (
        <LLMModelModal
          mode="edit"
          model={modals.editingModel}
          onClose={modals.closeEdit}
          onUpdate={modals.handleUpdateAndClose}
        />
      )}

      <ModelCatalogDrawer
        isOpen={modals.showCatalogDrawer}
        onClose={modals.closeCatalog}
        onModelInstalled={loadModels}
      />
    </AppTemplate>
  );
}
