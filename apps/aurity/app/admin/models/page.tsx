/**
 * LLM Models Admin Page — renders fi-glass/model-catalog over aurity's API client.
 * Route: /admin/models. Requires the FI-superadmin role (enforced by the API).
 */

'use client';

import { useState } from 'react';
import { Download, Plus, X } from 'lucide-react';
import {
  LLMModelFilterBar,
  LLMModelFormSheet,
  LLMModelGrid,
  ModelCatalogDrawer,
  ModelTestSheet,
  SystemResourcesPanel,
  useLLMModels,
  useModelTest,
  useSystemResources,
  type LLMModel,
  type ModelCatalogConfirm,
  type ModelCatalogNotify,
} from 'fi-glass/model-catalog';
import { Button } from '@/components/ui/button';
import { AppTemplate } from '@/components/layout/AppTemplate';
import { adminLLMModelsHeader } from '@/config/page-headers';
import { confirmDanger, toastError, toastSuccess } from '@/lib/swal';
import { modelCatalogStore } from '@/services/model-catalog';

const confirm: ModelCatalogConfirm = (message) =>
  confirmDanger({ title: '¿Eliminar modelo?', text: message, confirmText: 'Eliminar' });

const notify: ModelCatalogNotify = (kind, message) => (kind === 'success' ? toastSuccess(message) : toastError(message));

export default function LLMModelsAdminPage() {
  const collection = useLLMModels(modelCatalogStore, { confirm, notify });
  const resources = useSystemResources(modelCatalogStore, { notify });
  const test = useModelTest(modelCatalogStore);
  const [editing, setEditing] = useState<LLMModel | 'new' | null>(null);
  const [catalogOpen, setCatalogOpen] = useState(false);

  return (
    <AppTemplate
      headerConfig={adminLLMModelsHeader({ modelsCount: collection.models.length })}
      headerActions={
        <div className="fi-flex-gap-md">
          <Button onClick={() => setCatalogOpen(true)} variant="purple" icon={Download}>
            Catálogo
          </Button>
          <Button onClick={() => setEditing('new')} icon={Plus}>
            Nuevo Modelo
          </Button>
        </div>
      }
      backgroundGradient="emerald"
      padding="8"
      showWatermark={true}
      showGeometricBg={true}
    >
      <SystemResourcesPanel {...resources} />

      <LLMModelFilterBar
        provider={collection.provider}
        onProviderChange={collection.setProvider}
        includeInactive={collection.includeInactive}
        onIncludeInactiveChange={collection.setIncludeInactive}
      />

      {collection.actionError && (
        <div className="admin-error-banner mb-6">
          <span className="flex-1">{collection.actionError}</span>
          <button onClick={collection.clearActionError} aria-label="Cerrar error">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      <LLMModelGrid
        models={collection.models}
        loading={collection.loading}
        error={collection.error}
        selectedId={collection.selectedId}
        onSelect={collection.setSelectedId}
        onEdit={setEditing}
        onDeactivate={(model) => void collection.deactivate(model)}
        onToggleActive={(model) => void collection.toggleActive(model)}
        onTest={(model) => void test.run(model)}
        onRetry={() => void collection.reload()}
        onCreateFirst={() => setEditing('new')}
      />

      {editing && (
        <LLMModelFormSheet
          model={editing === 'new' ? undefined : editing}
          store={modelCatalogStore}
          onClose={() => setEditing(null)}
          onSaved={(model) => {
            collection.upsert(model);
            notify('success', editing === 'new' ? 'Modelo creado correctamente' : 'Modelo actualizado correctamente');
          }}
        />
      )}

      <ModelTestSheet {...test} />

      <ModelCatalogDrawer
        open={catalogOpen}
        onClose={() => setCatalogOpen(false)}
        store={modelCatalogStore}
        onModelsChanged={() => void collection.reload()}
        confirm={confirm}
        notify={notify}
      />
    </AppTemplate>
  );
}
