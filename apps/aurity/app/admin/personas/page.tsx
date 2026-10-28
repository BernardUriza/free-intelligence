/**
 * Personas Admin Page — renders fi-glass/persona-admin over aurity's personaService.
 * Route: /admin/personas. Create/delete require the FI-superadmin role (enforced by the API).
 */

'use client';

import { useEffect, useState } from 'react';
import { Loader2, AlertCircle, Brain, Plus, X } from 'lucide-react';
import {
  PersonaCard,
  PersonaCreateModal,
  PersonaEditor,
  usePersonaCollection,
  type PersonaConfirm,
  type PersonaOption,
} from 'fi-glass/persona-admin';
import { Button } from '@/components/ui/button';
import { confirmDanger } from '@/lib/swal';
import { personaService } from '@/services/persona';
import { fetchLLMModels } from '@aurity-standalone/api-client/llm-models';
import { AppTemplate } from '@/components/layout/AppTemplate';
import { adminPersonasHeader } from '@/config/page-headers';
import {
  PERSONA_ACCENTS,
  PERSONA_MODEL_FALLBACK,
  PERSONA_VOICE_OPTIONS,
  PROTECTED_PERSONAS,
  modelOptionsFrom,
  personaDeleteMessage,
} from '@/config/persona-admin';

const confirmDelete: PersonaConfirm = (message) =>
  confirmDanger({ title: 'Eliminar persona', text: message, confirmText: 'Eliminar' });

const deleteMessage = (persona: { name: string }) => personaDeleteMessage(persona.name);

export default function PersonasAdminPage() {
  const collection = usePersonaCollection(personaService, {
    confirm: confirmDelete,
    deleteConfirmMessage: deleteMessage,
  });
  const { personas, loading, error } = collection;
  const [modelOptions, setModelOptions] = useState<PersonaOption[]>(PERSONA_MODEL_FALLBACK);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  useEffect(() => {
    fetchLLMModels({ includeInactive: false })
      .then((models) => setModelOptions(modelOptionsFrom(models)))
      .catch(() => setModelOptions(PERSONA_MODEL_FALLBACK));
  }, []);

  const headerConfig = adminPersonasHeader({ personasCount: personas.length });

  return (
    <AppTemplate headerConfig={headerConfig} backgroundGradient="purple" padding="8" showWatermark={true} showGeometricBg={true}>
      {loading && (
        <div className="fi-empty-state-lg">
          <Loader2 className="w-12 h-12 fi-text-purple animate-spin mb-4" />
          <p className="text-slate-400">Cargando personas...</p>
        </div>
      )}

      {error && !loading && (
        <div className="fi-empty-state-lg">
          <div className="p-6 bg-red-950/20 border border-red-800 rounded-lg max-w-md">
            <div className="flex items-center gap-3 mb-2">
              <AlertCircle className="w-6 h-6 fi-text-error" />
              <h3 className="text-lg font-semibold text-red-300">Error al Cargar Personas</h3>
            </div>
            <p className="text-red-200 text-sm">{error}</p>
            <Button onClick={() => void collection.reload()} variant="danger" fullWidth className="mt-4">
              Reintentar
            </Button>
          </div>
        </div>
      )}

      {collection.removeError && (
        <div className="mb-6 p-4 bg-red-950/20 border border-red-800 rounded-lg">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-5 h-5 fi-text-error" />
            <span className="text-red-300">{collection.removeError}</span>
            <button
              onClick={collection.clearRemoveError}
              className="ml-auto fi-text-error hover:text-red-300"
              aria-label="Cerrar error"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {!loading && !error && (
        <div className="flex justify-end mb-6">
          <Button onClick={() => setIsCreateOpen(true)} variant="primary" icon={Plus}>
            Crear Persona
          </Button>
        </div>
      )}

      {!loading && !error && personas.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          {personas.map((persona) => (
            <PersonaCard
              key={persona.id}
              persona={persona}
              accentColor={PERSONA_ACCENTS[persona.id]}
              selected={selectedId === persona.id}
              onSelect={() => setSelectedId(persona.id)}
              onEdit={() => setEditingId(persona.id)}
              onDelete={
                PROTECTED_PERSONAS.has(persona.id)
                  ? undefined
                  : () =>
                      void collection.remove(persona).then((removed) => {
                        if (removed && selectedId === persona.id) setSelectedId(null);
                      })
              }
            />
          ))}
        </div>
      )}

      {!loading && !error && personas.length === 0 && (
        <div className="fi-empty-state-lg">
          <Brain className="w-16 h-16 text-slate-600 mb-4" />
          <h3 className="text-xl font-semibold text-slate-400 mb-2">No hay personas configuradas</h3>
          <p className="text-slate-500 text-center max-w-md">
            Las personas permiten configurar diferentes comportamientos del asistente médico.
          </p>
        </div>
      )}

      {editingId && (
        <PersonaEditor
          personaId={editingId}
          open
          onClose={() => setEditingId(null)}
          onSaved={collection.upsert}
          store={personaService}
          modelOptions={modelOptions}
          voiceOptions={PERSONA_VOICE_OPTIONS}
        />
      )}

      <PersonaCreateModal
        open={isCreateOpen}
        onOpenChange={setIsCreateOpen}
        store={personaService}
        onCreated={collection.upsert}
        modelOptions={modelOptions}
        voiceOptions={PERSONA_VOICE_OPTIONS}
        initialValues={{ model: 'qwen3:1.7b', voice: 'nova' }}
      />
    </AppTemplate>
  );
}
