/**
 * PersonaCreateModal Component
 *
 * Modal for creating new AI personas (FI-superadmin only).
 * Composes PersonaForm with create-specific persistence.
 * Open/Closed Principle: Modal shell + form composition.
 *
 * @module components/admin/persona/PersonaCreateModal
 */

'use client';

import { useState, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { X, Sparkles, AlertCircle } from 'lucide-react';
import { createLogger } from '@/lib/internal/logger';
import { PersonaForm } from './PersonaForm';

const log = createLogger('PersonaCreate');
import {
  DEFAULT_PERSONA_VALUES,
  validatePersonaCreate,
  type PersonaCreateFormValues,
} from './schema';
import { mapFormToCreateRequest, type Persona, type PersonaFormValues } from './types';
import { personaService, PersonaServiceError } from '@/services/persona';

export interface PersonaCreateModalProps {
  /** Whether the modal is open */
  open: boolean;
  /** Handler for open state changes */
  onOpenChange: (open: boolean) => void;
  /** Callback when persona is created successfully */
  onCreated: (persona: Persona) => void;
  // Note: authToken removed - now handled automatically by api client
}

/**
 * PersonaCreateModal - Modal wrapper for persona creation
 *
 * Follows Dependency Inversion: Uses PersonaForm for UI,
 * delegates persistence to personaService.
 */
export function PersonaCreateModal({
  open,
  onOpenChange,
  onCreated,
}: PersonaCreateModalProps) {
  // Form state
  const [formValues, setFormValues] = useState<PersonaCreateFormValues>(DEFAULT_PERSONA_VALUES);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [creating, setCreating] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  // Reset form state
  const resetForm = useCallback(() => {
    setFormValues(DEFAULT_PERSONA_VALUES);
    setErrors({});
    setApiError(null);
  }, []);

  // Handle close
  const handleClose = useCallback(() => {
    if (creating) return; // Prevent close during save
    resetForm();
    onOpenChange(false);
  }, [creating, resetForm, onOpenChange]);

  // Handle form submission
  const handleSubmit = useCallback(async () => {
    // Validate form
    const validation = validatePersonaCreate(formValues);
    if (!validation.success) {
      setErrors(validation.errors || {});
      return;
    }

    setErrors({});
    setApiError(null);
    setCreating(true);

    try {
      const request = mapFormToCreateRequest(validation.data!);
      // Note: Auth token is now handled automatically by api client
      const persona = await personaService.create(request);

      onCreated(persona);
      resetForm();
      onOpenChange(false);
    } catch (err) {
      log.error('Failed to create persona', { error: String(err) });

      if (err instanceof PersonaServiceError) {
        setApiError(err.message);
      } else {
        setApiError('Error inesperado al crear la persona');
      }
    } finally {
      setCreating(false);
    }
  }, [formValues, onCreated, resetForm, onOpenChange]);

  // Handle form value changes
  const handleChange = useCallback((values: PersonaFormValues) => {
    setFormValues(values as PersonaCreateFormValues);
    // Clear field error when user modifies it
    if (Object.keys(errors).length > 0) {
      setErrors({});
    }
  }, [errors]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto" role="dialog" aria-modal="true">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm"
        onClick={handleClose}
        aria-hidden="true"
      />

      {/* Modal */}
      <div className="relative flex min-h-full items-center justify-center p-4">
        <div className="admin-modal-persona">
          {/* Header */}
          <div className="flex items-center justify-between p-6 fi-border-bottom flex-shrink-0">
            <div className="fi-flex-gap-md">
              <div className="p-2 rounded-lg bg-purple-900 border border-purple-700">
                <Sparkles className="w-5 h-5 fi-text-purple" />
              </div>
              <div>
                <h2 className="fi-title-xl">Crear Nueva Persona</h2>
                <p className="fi-subtitle">Define una nueva personalidad de IA</p>
              </div>
            </div>
            <Button
              onClick={handleClose}
              disabled={creating}
              className="fi-icon-btn-ghost"
              aria-label="Cerrar modal"
              variant="ghost"
              size="sm"
              type="button"
            >
              <X className="w-5 h-5 text-slate-400" />
            </Button>
          </div>

          {/* Content - Scrollable */}
          <div className="p-6 overflow-y-auto flex-1">
            <PersonaForm
              value={formValues}
              onChange={handleChange}
              onSubmit={handleSubmit}
              disabled={creating}
              errors={errors}
              mode="create"
            />

            {/* API Error */}
            {apiError && (
              <div className="mt-4 flex items-center gap-2 p-3 bg-red-900/20 border border-red-800 rounded-lg">
                <AlertCircle className="w-5 h-5 fi-text-error flex-shrink-0" />
                <p className="text-sm text-red-300">{apiError}</p>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between p-6 fi-border-top flex-shrink-0">
            <p className="fi-text-xs-muted">
              <span className="fi-text-error">*</span> Campos requeridos
            </p>
            <div className="fi-flex-gap-md">
              <Button onClick={handleClose} disabled={creating} variant="secondary">
                Cancelar
              </Button>
              <Button
                onClick={handleSubmit}
                disabled={creating}
                variant="primary"
                icon={creating ? undefined : Sparkles}
                loading={creating}
              >
                {creating ? 'Creando...' : 'Crear Persona'}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default PersonaCreateModal;
