/**
 * Personas Admin Page
 *
 * Admin panel for managing AI personas (SOAP Editor, Clinical Advisor, etc.)
 * Route: /admin/personas
 * Requires: FI-superadmin role for create/delete operations
 */

'use client';

import { useState, useEffect } from 'react';
import { Loader2, AlertCircle, Brain, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuth } from '@aurity-standalone/hooks/useAuth';
import { createLogger } from '@/lib/internal/logger';

const log = createLogger('PersonasAdmin');
import type { Persona } from '@aurity-standalone/types/persona';
import { PersonaCreateModal } from '@/components/admin/persona';
import { personaService } from '@/services/persona';
import type { Persona as PersonaNew } from '@/components/admin/persona';
import { PersonaCard } from '@/components/admin/PersonaCard';
import { PersonaEditor } from '@/components/admin/PersonaEditor';
import { AppTemplate } from '@/components/layout/AppTemplate';
import { adminPersonasHeader } from '@/config/page-headers';

export default function PersonasAdminPage() {
  // Note: Auth token is now handled automatically by api client - no need for getAccessTokenSilently
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPersona, setSelectedPersona] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [_isDeleting, setIsDeleting] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // Load personas on mount
  useEffect(() => {
    loadPersonas();
  }, []);

  const loadPersonas = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await personaService.list();
      setPersonas(data);
    } catch (err) {
      log.error('Failed to load personas', { error: String(err) });
      setError(
        err instanceof Error ? err.message : 'Error al cargar las personas'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (personaId: string) => {
    setSelectedPersona(personaId);
    setIsEditing(true);
  };

  const handleSave = (updatedPersona: Persona) => {
    // Update persona in list
    setPersonas((prev) =>
      prev.map((p) => (p.id === updatedPersona.id ? updatedPersona : p))
    );
    setIsEditing(false);
    setSelectedPersona(null);
  };

  const handleClose = () => {
    setIsEditing(false);
    setSelectedPersona(null);
  };

  // Note: Auth token is now handled automatically by api client
  const handleOpenCreateModal = () => {
    setIsCreateModalOpen(true);
  };

  const handleCreateSuccess = (newPersona: PersonaNew) => {
    // Add new persona to list (types are compatible)
    setPersonas((prev) => [...prev, newPersona as unknown as Persona]);
    setIsCreateModalOpen(false);
  };

  const handleDelete = async (personaId: string) => {
    // Confirm deletion
    const persona = personas.find(p => p.id === personaId);
    if (!persona) return;

    const confirmed = window.confirm(
      `¿Estás seguro de eliminar la persona "${persona.name}"?\n\n` +
      `Esta acción eliminará:\n` +
      `• El template de la persona\n` +
      `• Todas las configuraciones de usuario asociadas\n\n` +
      `Esta acción no se puede deshacer.`
    );

    if (!confirmed) return;

    try {
      setIsDeleting(personaId);
      setDeleteError(null);

      // Note: Auth token is now handled automatically by api client
      await personaService.delete(personaId);

      // Remove from local state
      setPersonas(prev => prev.filter(p => p.id !== personaId));

      // Clear selection if deleted persona was selected
      if (selectedPersona === personaId) {
        setSelectedPersona(null);
        setIsEditing(false);
      }
    } catch (err) {
      log.error('Failed to delete persona', { error: String(err) });
      setDeleteError(
        err instanceof Error ? err.message : 'Error al eliminar la persona'
      );
    } finally {
      setIsDeleting(null);
    }
  };

  const headerConfig = adminPersonasHeader({ personasCount: personas.length });

  return (
    <AppTemplate headerConfig={headerConfig} backgroundGradient="purple" padding="8" showWatermark={true} showGeometricBg={true}>

        {/* Loading State */}
        {loading && (
          <div className="fi-empty-state-lg">
            <Loader2 className="w-12 h-12 fi-text-purple animate-spin mb-4" />
            <p className="text-slate-400">Cargando personas...</p>
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <div className="fi-empty-state-lg">
            <div className="p-6 bg-red-950/20 border border-red-800 rounded-lg max-w-md">
              <div className="flex items-center gap-3 mb-2">
                <AlertCircle className="w-6 h-6 fi-text-error" />
                <h3 className="text-lg font-semibold text-red-300">
                  Error al Cargar Personas
                </h3>
              </div>
              <p className="text-red-200 text-sm">{error}</p>
              <Button
                onClick={loadPersonas}
                variant="danger"
                fullWidth
                className="mt-4"
              >
                Reintentar
              </Button>
            </div>
          </div>
        )}

        {/* Delete Error Message */}
        {deleteError && (
          <div className="mb-6 p-4 bg-red-950/20 border border-red-800 rounded-lg">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-5 h-5 fi-text-error" />
              <span className="text-red-300">{deleteError}</span>
              <button
                onClick={() => setDeleteError(null)}
                className="ml-auto fi-text-error hover:text-red-300"
              >
                ✕
              </button>
            </div>
          </div>
        )}

        {/* Action Toolbar */}
        {!loading && !error && (
          <div className="flex justify-end mb-6">
            <Button
              onClick={handleOpenCreateModal}
              variant="primary"
              icon={Plus}
            >
              Crear Persona
            </Button>
          </div>
        )}

        {/* Personas Grid */}
        {!loading && !error && personas.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
            {personas.map((persona) => (
              <PersonaCard
                key={persona.id}
                persona={persona}
                isSelected={selectedPersona === persona.id}
                onClick={() => setSelectedPersona(persona.id)}
                onEdit={() => handleEdit(persona.id)}
                onDelete={() => handleDelete(persona.id)}
              />
            ))}
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && personas.length === 0 && (
          <div className="fi-empty-state-lg">
            <Brain className="w-16 h-16 text-slate-600 mb-4" />
            <h3 className="text-xl font-semibold text-slate-400 mb-2">
              No hay personas configuradas
            </h3>
            <p className="text-slate-500 text-center max-w-md">
              Las personas permiten configurar diferentes comportamientos del
              asistente médico.
            </p>
          </div>
        )}

        {/* Editor Panel (Slide-over) */}
        {selectedPersona && isEditing && (
          <PersonaEditor
            personaId={selectedPersona}
            isOpen={isEditing}
            onClose={handleClose}
            onSave={handleSave}
          />
        )}

        {/* Create Modal */}
        {isCreateModalOpen && (
          <PersonaCreateModal
            open={isCreateModalOpen}
            onOpenChange={setIsCreateModalOpen}
            onCreated={handleCreateSuccess}
          />
        )}
    </AppTemplate>
  );
}
